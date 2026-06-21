import asyncio
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.admin import process_overdue_payments
from app.repositories.subasta_repo import SubastaRepository
from app.services.auth_service import AuthService
from app.services.subasta_service import SubastaService
from app.services.usuario_service import UsuarioService


def pago_vencido(**overrides):
    data = {
        "id": 10,
        "subastaId": 5,
        "usuarioId": 20,
        "totalPujado": 1000.0,
        "comision": 100.0,
        "totalFinal": 1100.0,
        "moneda": "USD",
        "estado": "pendiente",
        "fechaLimitePago": "2026-06-20T12:00:00Z",
    }
    data.update(overrides)
    return data


def multa_pendiente(**overrides):
    data = {
        "id": 90,
        "cliente_id": 20,
        "importe": 100.0,
        "estado": "pendiente",
        "fechaLimite": "2026-06-24T12:00:00Z",
        "motivo": "Incumplimiento de pago #10 subasta #5",
    }
    data.update(overrides)
    return data


def medio_pago(**overrides):
    data = {
        "id": 99,
        "cliente_id": 20,
        "estado_verificacion": "validado",
        "moneda": "USD",
        "limite_reservado": 0.0,
    }
    data.update(overrides)
    return data


def make_db(fetchone_value=None):
    db = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_value
    db.cursor.return_value.__enter__.return_value = cursor
    return db, cursor


class TestProcesarVencimientosService(unittest.TestCase):
    def test_pago_pendiente_vencido_genera_multa_del_10_y_marca_vencido(self):
        db = MagicMock()
        pago = pago_vencido()
        multa = multa_pendiente(id=91, importe=100.0)

        with patch(
            "app.services.subasta_service.SubastaRepository.get_pagos_pendientes_vencidos",
            return_value=[pago],
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_multas_pendientes_vencidas",
            return_value=[],
        ), patch(
            "app.services.subasta_service.SubastaRepository.marcar_pago_vencido",
            return_value=True,
        ) as marcar_pago, patch(
            "app.services.subasta_service.SubastaRepository.generar_multa",
            return_value=(multa, True),
        ) as generar_multa, patch(
            "app.services.subasta_service.SubastaRepository.crear_notificacion",
        ) as notificar:
            result = SubastaService.procesar_vencimientos(db)

        self.assertEqual(result["pagosVencidosProcesados"], 1)
        self.assertEqual(result["multasCreadas"], 1)
        self.assertEqual(result["usuariosMarcadosMultaActiva"], [20])
        marcar_pago.assert_called_once_with(db, 10)
        generar_multa.assert_called_once_with(
            db,
            20,
            1000.0,
            "Incumplimiento de pago #10 subasta #5",
        )
        self.assertEqual(notificar.call_count, 2)
        db.commit.assert_called_once()

    def test_multa_pendiente_vencida_bloquea_usuario(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.get_pagos_pendientes_vencidos",
            return_value=[],
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_multas_pendientes_vencidas",
            return_value=[multa_pendiente()],
        ), patch(
            "app.services.subasta_service.SubastaRepository.bloquear_usuario",
            return_value=True,
        ) as bloquear, patch(
            "app.services.subasta_service.SubastaRepository.crear_notificacion",
        ) as notificar:
            result = SubastaService.procesar_vencimientos(db)

        self.assertEqual(result["usuariosBloqueados"], [20])
        self.assertEqual(result["multasVencidasBloqueantes"], 1)
        bloquear.assert_called_once_with(db, 20)
        notificar.assert_called_once()
        db.commit.assert_called_once()

    def test_join_rechaza_usuario_con_multa_o_bloqueo(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaService.procesar_vencimientos",
            return_value={},
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value={"identificador": 5, "estado": "abierta", "categoria": "comun"},
        ), patch(
            "app.services.subasta_service.SubastaRepository.puede_participar",
            return_value=False,
        ), patch(
            "app.services.subasta_service.SubastaRepository.tiene_medio_pago_validado",
            return_value=True,
        ):
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.join_subasta(db, 5, 20, "comun")

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("multas", ctx.exception.detail)

    def test_admin_endpoint_protegido_y_devuelve_resumen(self):
        normal_user = {"usuarioId": 2}
        admin_user = {"usuarioId": 12}
        resumen = {
            "pagosVencidosProcesados": 1,
            "multasCreadas": 1,
            "usuariosMarcadosMultaActiva": [20],
            "usuariosBloqueados": [],
            "multasVencidasBloqueantes": 0,
        }

        with patch("app.api.admin.SubastaService.procesar_vencimientos") as procesar:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(process_overdue_payments(MagicMock(), normal_user))

        self.assertEqual(ctx.exception.status_code, 403)
        procesar.assert_not_called()

        with patch(
            "app.api.admin.SubastaService.procesar_vencimientos",
            return_value=resumen,
        ) as procesar:
            result = asyncio.run(process_overdue_payments(MagicMock(), admin_user))

        self.assertEqual(result, resumen)
        procesar.assert_called_once()


class TestSubastaMultaRepository(unittest.TestCase):
    def test_generar_multa_crea_10_por_ciento_y_setea_multa_activa(self):
        db, cursor = make_db()
        cursor.fetchone.side_effect = [
            None,
            {
                "id": 91,
                "importe": 100.0,
                "estado": "pendiente",
                "fechaLimite": "2026-06-24T12:00:00Z",
                "motivo": "Incumplimiento de pago #10 subasta #5",
            },
            {"identificador": 20},
        ]

        multa, created = SubastaRepository.generar_multa(
            db,
            20,
            1000.0,
            "Incumplimiento de pago #10 subasta #5",
        )

        self.assertTrue(created)
        self.assertEqual(multa["importe"], 100.0)
        executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertIn("INSERT INTO multas", executed_sql)
        self.assertIn("multa_activa = true", executed_sql)

    def test_generar_multa_no_duplica_mismo_motivo(self):
        db, cursor = make_db(
            {
                "id": 91,
                "importe": 100.0,
                "estado": "pendiente",
                "fechaLimite": "2026-06-24T12:00:00Z",
                "motivo": "Incumplimiento de pago #10 subasta #5",
            }
        )

        multa, created = SubastaRepository.generar_multa(
            db,
            20,
            1000.0,
            "Incumplimiento de pago #10 subasta #5",
        )

        self.assertFalse(created)
        self.assertEqual(multa["id"], 91)
        executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertNotIn("INSERT INTO multas", executed_sql)

    def test_marcar_pago_vencido_actualiza_estado(self):
        db, cursor = make_db({"identificador": 10})

        result = SubastaRepository.marcar_pago_vencido(db, 10)

        self.assertTrue(result)
        executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertIn("estado = 'vencido'", executed_sql)

    def test_puede_participar_rechaza_multa_activa_o_bloqueado(self):
        db, cursor = make_db({"bloqueado": False, "multa_activa": True})
        self.assertFalse(SubastaRepository.puede_participar(db, 20))

        cursor.fetchone.return_value = {"bloqueado": True, "multa_activa": False}
        self.assertFalse(SubastaRepository.puede_participar(db, 20))


class TestPagarMultaService(unittest.TestCase):
    def test_pagar_multa_con_medio_ajeno_falla(self):
        db = MagicMock()

        with patch(
            "app.services.usuario_service.SubastaService.procesar_vencimientos",
            return_value={},
        ), patch(
            "app.services.usuario_service.UsuarioRepository.get_multa_para_cliente",
            return_value=multa_pendiente(),
        ), patch(
            "app.services.usuario_service.UsuarioRepository.get_medio_pago_para_cliente",
            return_value=None,
        ), patch(
            "app.services.usuario_service.UsuarioRepository.pagar_multa",
        ) as pagar:
            with self.assertRaises(HTTPException) as ctx:
                UsuarioService.pagar_multa(db, 20, 90, 99)

        self.assertEqual(ctx.exception.status_code, 403)
        pagar.assert_not_called()
        db.rollback.assert_called_once()

    def test_pagar_multa_con_medio_no_validado_falla(self):
        db = MagicMock()

        with patch(
            "app.services.usuario_service.SubastaService.procesar_vencimientos",
            return_value={},
        ), patch(
            "app.services.usuario_service.UsuarioRepository.get_multa_para_cliente",
            return_value=multa_pendiente(),
        ), patch(
            "app.services.usuario_service.UsuarioRepository.get_medio_pago_para_cliente",
            return_value=medio_pago(estado_verificacion="pendiente"),
        ), patch(
            "app.services.usuario_service.UsuarioRepository.pagar_multa",
        ) as pagar:
            with self.assertRaises(HTTPException) as ctx:
                UsuarioService.pagar_multa(db, 20, 90, 99)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "Medio de pago no validado")
        pagar.assert_not_called()
        db.rollback.assert_called_once()

    def test_pagar_multa_pendiente_marca_pagada_y_limpia_ultima(self):
        db = MagicMock()

        with patch(
            "app.services.usuario_service.SubastaService.procesar_vencimientos",
            return_value={},
        ), patch(
            "app.services.usuario_service.UsuarioRepository.get_multa_para_cliente",
            return_value=multa_pendiente(),
        ), patch(
            "app.services.usuario_service.UsuarioRepository.get_medio_pago_para_cliente",
            return_value=medio_pago(),
        ), patch(
            "app.services.usuario_service.UsuarioRepository.pagar_multa",
        ) as pagar, patch(
            "app.services.usuario_service.UsuarioRepository.tiene_multas_pendientes",
            return_value=False,
        ), patch(
            "app.services.usuario_service.UsuarioRepository.set_multa_activa",
        ) as set_multa_activa, patch(
            "app.services.usuario_service.UsuarioRepository.crear_notificacion",
        ):
            result = UsuarioService.pagar_multa(db, 20, 90, 99)

        self.assertEqual(result, {"message": "Multa pagada correctamente"})
        pagar.assert_called_once_with(db, 90, 99)
        set_multa_activa.assert_called_once_with(db, 20, False)
        db.commit.assert_called_once()

    def test_pagar_multa_no_limpia_si_quedan_pendientes(self):
        db = MagicMock()

        with patch(
            "app.services.usuario_service.SubastaService.procesar_vencimientos",
            return_value={},
        ), patch(
            "app.services.usuario_service.UsuarioRepository.get_multa_para_cliente",
            return_value=multa_pendiente(),
        ), patch(
            "app.services.usuario_service.UsuarioRepository.get_medio_pago_para_cliente",
            return_value=medio_pago(),
        ), patch(
            "app.services.usuario_service.UsuarioRepository.pagar_multa",
        ), patch(
            "app.services.usuario_service.UsuarioRepository.tiene_multas_pendientes",
            return_value=True,
        ), patch(
            "app.services.usuario_service.UsuarioRepository.set_multa_activa",
        ) as set_multa_activa, patch(
            "app.services.usuario_service.UsuarioRepository.crear_notificacion",
        ):
            UsuarioService.pagar_multa(db, 20, 90, 99)

        set_multa_activa.assert_not_called()
        db.commit.assert_called_once()


class TestBloqueoLogin(unittest.TestCase):
    @patch("app.services.auth_service.verify_password", return_value=True)
    def test_bloqueado_no_puede_loguear(self, verify_password):
        db, _ = make_db(
            {
                "usuario_id": 20,
                "documento": "35123456",
                "nombre": "Juan Perez",
                "password_hash": "hash",
                "admitido": "si",
                "categoria": "comun",
                "estadoRegistro": "aprobado",
                "bloqueado": True,
                "multaActiva": True,
            }
        )

        with self.assertRaises(HTTPException) as ctx:
            AuthService.login(db, "35123456", "secret")

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "User is blocked")


if __name__ == "__main__":
    unittest.main()
