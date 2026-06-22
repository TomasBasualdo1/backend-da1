import asyncio
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.subastas import close_auction
from app.repositories.subasta_repo import SubastaRepository
from app.services.subasta_service import SubastaService


def pago_pendiente(**overrides):
    data = {
        "id": 10,
        "subastaId": 5,
        "usuarioId": 20,
        "totalPujado": 1000.0,
        "comision": 100.0,
        "costoEnvio": 0.0,
        "totalFinal": 1100.0,
        "moneda": "USD",
        "modoEntrega": None,
        "estado": "pendiente",
        "fechaLimitePago": "2026-06-24T12:00:00Z",
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


DEFAULT = object()


def make_repo_patches(pago=DEFAULT, medio=DEFAULT):
    return (
        patch(
            "app.services.subasta_service.SubastaRepository.get_pago_usuario",
            return_value=pago if pago is not DEFAULT else pago_pendiente(),
        ),
        patch(
            "app.services.subasta_service.SubastaRepository.get_medio_pago_para_cliente",
            return_value=medio if medio is not DEFAULT else medio_pago(),
        ),
        patch("app.services.subasta_service.SubastaRepository.confirmar_pago"),
        patch("app.services.subasta_service.SubastaRepository.crear_notificacion"),
    )


class TestSubastaPagoApi(unittest.TestCase):
    def test_usuario_comun_no_puede_cerrar_subasta(self):
        user = {"usuarioId": 2, "categoria": "comun"}

        with patch("app.api.subastas.SubastaService.cerrar_subasta") as cerrar:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(close_auction(5, MagicMock(), user))

        self.assertEqual(ctx.exception.status_code, 403)
        cerrar.assert_not_called()

    def test_admin_puede_cerrar_y_se_generan_pagos_esperados(self):
        db = MagicMock()
        items = [
            {
                "item_id": 1,
                "preciobase": 1000.0,
                "comision": 100.0,
                "producto": 11,
                "duenio": 30,
                "puja_id": 101,
                "puja_importe": 1200.0,
                "cliente_ganador": 20,
            },
            {
                "item_id": 2,
                "preciobase": 800.0,
                "comision": 80.0,
                "producto": 12,
                "duenio": 31,
                "puja_id": 102,
                "puja_importe": 900.0,
                "cliente_ganador": 20,
            },
            {
                "item_id": 3,
                "preciobase": 500.0,
                "comision": 50.0,
                "producto": 13,
                "duenio": 32,
                "puja_id": None,
                "puja_importe": None,
                "cliente_ganador": None,
            },
        ]

        with patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value={"identificador": 5, "estado": "abierta", "categoria": "comun", "moneda": "USD"},
        ), patch(
            "app.services.subasta_service.SubastaRepository.obtener_items_con_pujas",
            return_value=items,
        ), patch(
            "app.services.subasta_service.SubastaRepository.cerrar_item",
        ) as cerrar_item, patch(
            "app.services.subasta_service.SubastaRepository.registrar_venta",
        ) as registrar_venta, patch(
            "app.services.subasta_service.SubastaRepository.generar_pago",
            return_value=77,
        ) as generar_pago, patch(
            "app.services.subasta_service.SubastaRepository.crear_notificacion",
        ), patch(
            "app.services.subasta_service.SubastaRepository.marcar_subasta_cerrada",
        ) as marcar_cerrada, patch(
            "app.services.subasta_service.SubastaRepository.finalizar_sesiones",
        ) as finalizar_sesiones:
            result = SubastaService.cerrar_subasta(db, 5)

        self.assertEqual(result["itemsCerrados"], 3)
        self.assertEqual(result["pagosGenerados"], 1)
        self.assertEqual(cerrar_item.call_count, 3)
        self.assertEqual(registrar_venta.call_count, 2)
        generar_pago.assert_called_once_with(db, 5, 20, 2100.0, 180.0, "USD")
        marcar_cerrada.assert_called_once_with(db, 5)
        finalizar_sesiones.assert_called_once_with(db, 5)
        db.commit.assert_called_once()


class TestSubastaPagoService(unittest.TestCase):
    def test_confirmar_pago_con_medio_ajeno_falla(self):
        db = MagicMock()
        get_pago, get_medio, confirmar, notificar = make_repo_patches(medio=None)

        with get_pago, get_medio as get_medio_mock, confirmar as confirmar_mock, notificar:
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.confirmar_pago(
                    db, 5, 20, 99, "envio", "Calle 123", False
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Medio de pago", ctx.exception.detail)
        get_medio_mock.assert_called_once_with(db, 20, 99)
        confirmar_mock.assert_not_called()
        db.rollback.assert_called_once()

    def test_confirmar_pago_con_medio_no_validado_falla(self):
        db = MagicMock()
        patches = make_repo_patches(
            medio=medio_pago(estado_verificacion="pendiente")
        )

        with patches[0], patches[1], patches[2] as confirmar, patches[3]:
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.confirmar_pago(
                    db, 5, 20, 99, "envio", "Calle 123", False
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "Medio de pago no validado")
        confirmar.assert_not_called()
        db.rollback.assert_called_once()

    def test_confirmar_pago_con_moneda_incompatible_falla(self):
        db = MagicMock()
        patches = make_repo_patches(medio=medio_pago(moneda="ARS"))

        with patches[0], patches[1], patches[2] as confirmar, patches[3]:
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.confirmar_pago(
                    db, 5, 20, 99, "envio", "Calle 123", False
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Moneda invalida para este pago")
        confirmar.assert_not_called()
        db.rollback.assert_called_once()

    def test_confirmar_pago_con_limite_insuficiente_falla(self):
        db = MagicMock()
        patches = make_repo_patches(medio=medio_pago(limite_reservado=1200.0))

        with patches[0], patches[1], patches[2] as confirmar, patches[3]:
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.confirmar_pago(
                    db, 5, 20, 99, "envio", "Calle 123", False
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Fondos insuficientes")
        confirmar.assert_not_called()
        db.rollback.assert_called_once()

    def test_envio_sin_direccion_falla(self):
        db = MagicMock()
        get_pago, get_medio, confirmar, notificar = make_repo_patches()

        with get_pago, get_medio as get_medio_mock, confirmar as confirmar_mock, notificar:
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.confirmar_pago(db, 5, 20, 99, "envio", "   ", False)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "La direccion de envio es obligatoria")
        get_medio_mock.assert_not_called()
        confirmar_mock.assert_not_called()
        db.rollback.assert_called_once()

    def test_envio_suma_costo_de_envio(self):
        db = MagicMock()
        get_pago, get_medio, confirmar, notificar = make_repo_patches(
            medio=medio_pago(limite_reservado=2000.0)
        )

        with get_pago, get_medio, confirmar as confirmar_mock, notificar:
            result = SubastaService.confirmar_pago(
                db, 5, 20, 99, "envio", " Calle 123 ", False
            )

        self.assertEqual(result, {"message": "Pago confirmado exitosamente"})
        confirmar_mock.assert_called_once_with(
            db,
            10,
            99,
            "envio",
            "Calle 123",
            False,
            500.0,
            1600.0,
        )
        db.commit.assert_called_once()

    def test_retiro_exige_perdida_de_seguro(self):
        db = MagicMock()
        get_pago, get_medio, confirmar, notificar = make_repo_patches()

        with get_pago, get_medio as get_medio_mock, confirmar as confirmar_mock, notificar:
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.confirmar_pago(db, 5, 20, 99, "retiro", None, False)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("perdida de seguro", ctx.exception.detail)
        get_medio_mock.assert_not_called()
        confirmar_mock.assert_not_called()
        db.rollback.assert_called_once()

    def test_retiro_persiste_perdida_de_seguro(self):
        db = MagicMock()
        get_pago, get_medio, confirmar, notificar = make_repo_patches()

        with get_pago, get_medio, confirmar as confirmar_mock, notificar:
            result = SubastaService.confirmar_pago(
                db, 5, 20, 99, "retiro", "No usar", True
            )

        self.assertEqual(result, {"message": "Pago confirmado exitosamente"})
        confirmar_mock.assert_called_once_with(
            db,
            10,
            99,
            "retiro",
            None,
            True,
            0.0,
            1100.0,
        )
        db.commit.assert_called_once()

    def test_pago_valido_marca_pagado_y_guarda_medio_pago(self):
        db = MagicMock()
        get_pago, get_medio, confirmar, notificar = make_repo_patches()

        with get_pago, get_medio, confirmar as confirmar_mock, notificar as notificar_mock:
            SubastaService.confirmar_pago(db, 5, 20, 99, "envio", "Calle 123", False)

        confirmar_mock.assert_called_once()
        args = confirmar_mock.call_args.args
        self.assertEqual(args[1], 10)
        self.assertEqual(args[2], 99)
        self.assertEqual(args[3], "envio")
        notificar_mock.assert_called_once()
        db.commit.assert_called_once()


class TestSubastaPagoRepository(unittest.TestCase):
    def test_generar_pago_reusa_pago_existente_para_evitar_duplicados(self):
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {"identificador": 44}
        db.cursor.return_value.__enter__.return_value = cursor

        result = SubastaRepository.generar_pago(
            db,
            subasta_id=5,
            cliente_id=20,
            total_pujado=1000.0,
            comision=100.0,
            moneda="USD",
        )

        self.assertEqual(result, 44)
        self.assertEqual(cursor.execute.call_count, 1)


if __name__ == "__main__":
    unittest.main()
