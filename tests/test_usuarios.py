import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.usuarios import (
    add_payment_method,
    delete_payment_method,
    delete_profile_picture,
    get_metrics,
    get_profile,
    list_pending_auction_payments,
    list_payment_methods,
    update_payment_method,
    update_profile,
)
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.schemas import MedioPagoInput, MedioPagoUpdate
from app.services.usuario_service import UsuarioService


class FakeUpload:
    content_type = "image/png"

    def __init__(self, content: bytes):
        self.content = content

    async def read(self):
        return self.content


class TestUsuariosApi(unittest.TestCase):
    def setUp(self):
        self.mock_user = {"usuarioId": 123, "documento": "12345678"}
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.cursor.return_value.__enter__.return_value = self.mock_cursor

    def test_delete_profile_picture(self):
        response = asyncio.run(
            delete_profile_picture(db=self.mock_db, user=self.mock_user)
        )

        self.assertEqual(response, {"message": "Foto de perfil eliminada correctamente"})

        # Verify the database update query was executed with correct arguments
        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE personas_adicionales SET foto_url = NULL WHERE identificador = %s",
            (123,)
        )
        self.mock_db.commit.assert_called_once()

    def test_get_profile_success(self):
        self.mock_cursor.fetchone.return_value = {
            "id": 123,
            "documento": "12345678",
            "nombre": "Juan Carlos Perez",
            "email": "juan@example.com",
            "direccion": "Av. Corrientes 1234",
            "telefono": "+54 11 5555-5555",
            "foto": "http://example.com/avatar.jpg",
            "numeroPais": 1,
            "admitido": "si",
            "estadoRegistro": "aprobado",
            "categoria": "comun",
            "multaActiva": False,
            "bloqueado": False
        }

        response = asyncio.run(get_profile(db=self.mock_db, user=self.mock_user))

        self.assertEqual(response.id, 123)
        self.assertEqual(response.nombre, "Juan")
        self.assertEqual(response.apellido, "Carlos Perez")
        self.assertEqual(response.admitido.value, "si")
        self.assertEqual(response.telefono, "+54 11 5555-5555")

        executed_sql = self.mock_cursor.execute.call_args.args[0]
        self.assertIn("WHERE p.identificador = %s", executed_sql)
        self.assertEqual(self.mock_cursor.execute.call_args.args[1], (123,))

    def test_get_profile_not_found(self):
        self.mock_cursor.fetchone.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_profile(db=self.mock_db, user=self.mock_user))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Usuario no encontrado")

    @patch(
        "app.services.usuario_service.StorageService.upload_file",
        return_value="https://storage.example.com/profile/123/photo.jpg",
    )
    def test_update_profile_split_name_uploads_photo_and_commits(self, upload_file):
        self.mock_cursor.fetchone.return_value = {
            "nombre": "Juan Perez",
            "documento": "12345678",
        }

        response = asyncio.run(
            update_profile(
                nombre="Ana",
                apellido="Gomez",
                direccion="Nueva direccion",
                telefono="5555",
                foto=FakeUpload(b"avatar"),
                db=self.mock_db,
                user=self.mock_user,
            )
        )

        self.assertEqual(response, {"message": "Perfil actualizado correctamente"})
        upload_file.assert_called_once_with(
            b"avatar",
            "profile/123/photo.jpg",
            "image/png",
        )

        executed_sql = "\n".join(
            call.args[0] for call in self.mock_cursor.execute.call_args_list
        )
        self.assertIn("SELECT nombre, documento FROM personas", executed_sql)
        self.assertIn("UPDATE personas SET nombre = %s", executed_sql)
        self.assertIn("UPDATE personas SET direccion = %s", executed_sql)
        self.assertIn("UPDATE personas_adicionales SET telefono = %s", executed_sql)
        self.assertIn("UPDATE personas_adicionales SET foto_url = %s", executed_sql)
        self.assertIn(
            ("Ana Gomez", 123),
            [call.args[1] for call in self.mock_cursor.execute.call_args_list],
        )
        self.mock_db.commit.assert_called_once()

    def test_update_profile_not_found(self):
        self.mock_cursor.fetchone.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(update_profile(db=self.mock_db, user=self.mock_user))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Usuario no encontrado")
        self.mock_db.commit.assert_not_called()

    def test_list_payment_methods_maps_fields_and_float_values(self):
        self.mock_cursor.fetchall.return_value = [
            {
                "id": 8,
                "tipo": "cuenta_bancaria",
                "ultimos_digitos": "7788",
                "estadoVerificacion": "validado",
                "moneda": "USD",
                "limiteReservado": 1200,
                "paisBanco": "AR",
                "esCuentaReceptora": 0,
            }
        ]

        response = asyncio.run(
            list_payment_methods(db=self.mock_db, user=self.mock_user)
        )

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].id, 8)
        self.assertEqual(response[0].tipo.value, "cuenta_bancaria")
        self.assertEqual(response[0].ultimos_digitos, "7788")
        self.assertEqual(response[0].estadoVerificacion.value, "validado")
        self.assertEqual(response[0].moneda.value, "USD")
        self.assertEqual(response[0].limiteReservado, 1200.0)
        self.assertEqual(response[0].paisBanco, "AR")
        self.assertFalse(response[0].esCuentaReceptora)

        executed_sql = self.mock_cursor.execute.call_args.args[0]
        self.assertIn("estado_verificacion as \"estadoVerificacion\"", executed_sql)
        self.assertEqual(self.mock_cursor.execute.call_args.args[1], (123,))

    def test_add_payment_method_extracts_last_digits_and_commits(self):
        body = MedioPagoInput(
            tipo="tarjeta_credito",
            datos_encriptados="tok_1234567890123456",
            moneda="USD",
            limiteReservado=500.0,
            paisBanco="AR",
            esCuentaReceptora=True,
        )

        response = asyncio.run(
            add_payment_method(body=body, db=self.mock_db, user=self.mock_user)
        )

        self.assertEqual(response, {"message": "Medio de pago agregado correctamente"})
        params = self.mock_cursor.execute.call_args.args[1]
        self.assertEqual(
            params,
            (
                123,
                "tarjeta_credito",
                "tok_1234567890123456",
                "3456",
                "USD",
                500.0,
                "AR",
                True,
            ),
        )
        self.mock_db.commit.assert_called_once()

    def test_add_payment_method_preserves_default_last_digits(self):
        body = MedioPagoInput(
            tipo="cheque_certificado",
            datos_encriptados="",
            moneda="ARS",
        )

        asyncio.run(add_payment_method(body=body, db=self.mock_db, user=self.mock_user))

        params = self.mock_cursor.execute.call_args.args[1]
        self.assertEqual(params[3], "4321")
        self.assertEqual(params[5], 0.0)
        self.assertIsNone(params[6])
        self.assertFalse(params[7])

    def test_update_payment_method_updates_allowlisted_fields(self):
        self.mock_cursor.fetchone.return_value = {"exists": 1}
        body = MedioPagoUpdate(limiteReservado=900.0, esCuentaReceptora=True)

        response = asyncio.run(
            update_payment_method(8, body, db=self.mock_db, user=self.mock_user)
        )

        self.assertEqual(response, {"message": "Medio de pago actualizado"})
        update_call = self.mock_cursor.execute.call_args_list[-1]
        self.assertEqual(
            update_call.args[0],
            "UPDATE medios_pago SET limite_reservado = %s, es_cuenta_receptora = %s WHERE identificador = %s",
        )
        self.assertEqual(update_call.args[1], (900.0, True, 8))
        self.mock_db.commit.assert_called_once()

    def test_update_payment_method_without_changes_returns_noop_without_commit(self):
        self.mock_cursor.fetchone.return_value = {"exists": 1}

        response = asyncio.run(
            update_payment_method(
                8,
                MedioPagoUpdate(),
                db=self.mock_db,
                user=self.mock_user,
            )
        )

        self.assertEqual(response, {"message": "No se realizaron cambios"})
        self.assertEqual(self.mock_cursor.execute.call_count, 1)
        self.mock_db.commit.assert_not_called()

    def test_update_payment_method_not_found(self):
        self.mock_cursor.fetchone.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                update_payment_method(
                    8,
                    MedioPagoUpdate(limiteReservado=100.0),
                    db=self.mock_db,
                    user=self.mock_user,
                )
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Medio de pago no encontrado")
        self.mock_db.commit.assert_not_called()

    def test_delete_payment_method_deletes_owned_method_and_commits(self):
        self.mock_cursor.fetchone.return_value = {"exists": 1}

        response = asyncio.run(
            delete_payment_method(8, db=self.mock_db, user=self.mock_user)
        )

        self.assertIsNone(response)
        executed_sql = "\n".join(
            call.args[0] for call in self.mock_cursor.execute.call_args_list
        )
        self.assertIn(
            "SELECT 1 FROM medios_pago WHERE identificador = %s AND cliente_id = %s",
            executed_sql,
        )
        self.assertIn("DELETE FROM medios_pago WHERE identificador = %s", executed_sql)
        self.mock_db.commit.assert_called_once()

    def test_delete_payment_method_not_found(self):
        self.mock_cursor.fetchone.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(delete_payment_method(8, db=self.mock_db, user=self.mock_user))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Medio de pago no encontrado")
        self.mock_db.commit.assert_not_called()

    def test_get_metrics_maps_counts_sums_categories_and_dates(self):
        last_seen = datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
        self.mock_cursor.fetchone.side_effect = [
            {"total": 5},
            {"total": 2},
            {"total_pujas": 10, "total_importe": 1500},
            {"total": 700},
            {"max_fecha": last_seen},
        ]
        self.mock_cursor.fetchall.return_value = [
            {"categoria": "comun"},
            {"categoria": "oro"},
            {"categoria": None},
        ]

        response = asyncio.run(get_metrics(db=self.mock_db, user=self.mock_user))

        self.assertEqual(response.totalSubastasParticipadas, 5)
        self.assertEqual(response.totalSubastasGanadas, 2)
        self.assertEqual(response.porcentajeExito, 40.0)
        self.assertEqual(response.totalPujasRealizadas, 10)
        self.assertEqual(response.montoTotalOfertado, 1500.0)
        self.assertEqual(response.montoTotalPagado, 700.0)
        self.assertEqual([cat.value for cat in response.categoriasParticipadas], ["comun", "oro"])
        self.assertEqual(response.ultimaParticipacion, last_seen)

    def test_list_pending_auction_payments_endpoint_maps_items(self):
        with patch(
            "app.api.usuarios.UsuarioService.list_pagos_pendientes",
            return_value=[
                {
                    "id": 77,
                    "subastaId": 5,
                    "usuarioId": 123,
                    "subastaFecha": "2026-06-28",
                    "subastaHora": "19:00:00",
                    "subastaUbicacion": "Sala Central",
                    "totalPujado": 1200.0,
                    "comision": 120.0,
                    "costoEnvio": 0.0,
                    "totalFinal": 1320.0,
                    "moneda": "USD",
                    "modoEntrega": None,
                    "estado": "pendiente",
                    "fechaLimitePago": "2099-06-24T12:00:00Z",
                    "items": [
                        {
                            "itemId": 9,
                            "productoId": 11,
                            "descripcion": "Reloj antiguo",
                            "importe": 1200.0,
                            "comision": 120.0,
                        }
                    ],
                }
            ],
        ) as service:
            response = asyncio.run(
                list_pending_auction_payments(db=self.mock_db, user=self.mock_user)
            )

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].id, 77)
        self.assertEqual(response[0].subastaId, 5)
        self.assertEqual(response[0].items[0].descripcion, "Reloj antiguo")
        service.assert_called_once_with(self.mock_db, 123)

    def test_service_pagos_pendientes_procesa_vencimientos_antes_de_listar(self):
        with patch(
            "app.services.usuario_service.SubastaService.procesar_vencimientos",
            return_value={},
        ) as vencimientos, patch(
            "app.services.usuario_service.UsuarioRepository.get_pagos_pendientes",
            return_value=[],
        ) as repo:
            result = UsuarioService.list_pagos_pendientes(self.mock_db, 123)

        self.assertEqual(result, [])
        vencimientos.assert_called_once_with(self.mock_db, 123)
        repo.assert_called_once_with(self.mock_db, 123)

    def test_repo_pagos_pendientes_filtra_usuario_pendiente_y_subasta_cerrada(self):
        self.mock_cursor.fetchall.side_effect = [
            [
                {
                    "id": 77,
                    "subastaId": 5,
                    "usuarioId": 123,
                    "subastaFecha": "2026-06-28",
                    "subastaHora": "19:00:00",
                    "subastaUbicacion": "Sala Central",
                    "totalPujado": 1200,
                    "comision": 120,
                    "costoEnvio": 0,
                    "totalFinal": 1320,
                    "moneda": "USD",
                    "modoEntrega": None,
                    "estado": "pendiente",
                    "fechaLimitePago": "2099-06-24T12:00:00Z",
                }
            ],
            [
                {
                    "subastaId": 5,
                    "itemId": 9,
                    "productoId": 11,
                    "descripcion": "Reloj antiguo",
                    "importe": 1200,
                    "comision": 120,
                }
            ],
        ]

        result = UsuarioRepository.get_pagos_pendientes(self.mock_db, 123)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["totalPujado"], 1200.0)
        self.assertEqual(result[0]["items"][0]["descripcion"], "Reloj antiguo")
        self.assertEqual(result[0]["items"][0]["importe"], 1200.0)

        pagos_sql = self.mock_cursor.execute.call_args_list[0].args[0]
        self.assertIn("p.cliente_id = %s", pagos_sql)
        self.assertIn("p.estado = 'pendiente'", pagos_sql)
        self.assertIn("s.estado = 'cerrada'", pagos_sql)
        self.assertEqual(self.mock_cursor.execute.call_args_list[0].args[1], (123,))

        ventas_sql = self.mock_cursor.execute.call_args_list[1].args[0]
        self.assertIn("FROM registrodesubasta r", ventas_sql)
        self.assertIn("r.cliente = %s", ventas_sql)
        self.assertEqual(self.mock_cursor.execute.call_args_list[1].args[1], (123, [5]))

if __name__ == "__main__":
    unittest.main()
