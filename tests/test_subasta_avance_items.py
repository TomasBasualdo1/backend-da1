import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, call, patch

from fastapi import HTTPException

from app.api.subastas import close_auction
from app.repositories.subasta_repo import SubastaRepository
from app.services.subasta_service import SubastaService


def subasta_basica(**overrides):
    data = {
        "identificador": 5,
        "estado": "abierta",
        "categoria": "comun",
        "moneda": "USD",
    }
    data.update(overrides)
    return data


def item_cierre(**overrides):
    data = {
        "item_id": 1,
        "preciobase": 1000.0,
        "comision": 100.0,
        "producto": 11,
        "duenio": 30,
        "puja_id": 101,
        "puja_importe": 1200.0,
        "cliente_ganador": 20,
    }
    data.update(overrides)
    return data


def item_detalle(**overrides):
    data = {
        "id": 2,
        "descripcion": "Siguiente item",
        "precioBase": 800.0,
        "mejorOfertaActual": None,
        "limiteMinimo": 800.0,
        "limiteMaximo": 960.0,
        "subastado": "no",
        "fotos": [],
    }
    data.update(overrides)
    return data


class TestSubastaAvanceItemsService(unittest.TestCase):
    def test_no_se_puede_pujar_por_item_no_activo(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaService.procesar_vencimientos",
            return_value={},
        ), patch(
            "app.services.subasta_service.SubastaRepository.puede_participar",
            return_value=True,
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_asistente_id",
            return_value=44,
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_item_for_update",
            return_value={"id": 2, "preciobase": 500.0, "subastado": "no"},
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_item_activo_id",
            return_value=1,
        ), patch(
            "app.services.subasta_service.SubastaRepository.registrar_puja",
        ) as registrar:
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.procesar_puja(
                    db,
                    subasta_id=5,
                    item_id=2,
                    usuario_id=20,
                    categoria_usuario="comun",
                    importe=500.0,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("ítem activo", ctx.exception.detail)
        registrar.assert_not_called()
        db.rollback.assert_called_once()

    def test_cierre_de_primer_item_avanza_al_segundo_sin_cerrar_subasta(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value=subasta_basica(),
        ), patch(
            "app.services.subasta_service.SubastaRepository.obtener_item_activo_con_puja",
            return_value=item_cierre(),
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
            "app.services.subasta_service.SubastaRepository.get_item_activo_detalle",
            return_value=item_detalle(id=2),
        ), patch(
            "app.services.subasta_service.SubastaRepository.contar_items_pendientes",
            return_value=1,
        ), patch(
            "app.services.subasta_service.SubastaRepository.marcar_subasta_cerrada",
        ) as marcar_subasta, patch(
            "app.services.subasta_service.SubastaRepository.finalizar_sesiones",
        ) as finalizar_sesiones:
            result = SubastaService.cerrar_subasta(db, 5)

        self.assertEqual(result["itemsCerrados"], 1)
        self.assertFalse(result["subastaCerrada"])
        self.assertEqual(result["itemCerrado"]["id"], 1)
        self.assertEqual(result["itemActivo"]["id"], 2)
        cerrar_item.assert_called_once_with(db, 1, 101)
        registrar_venta.assert_called_once_with(db, 5, 30, 11, 20, 1200.0, 100.0)
        generar_pago.assert_called_once_with(db, 5, 20, 1200.0, 100.0, "USD")
        marcar_subasta.assert_not_called()
        finalizar_sesiones.assert_not_called()

    def test_cierre_final_con_ganadores_distintos_por_item(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value=subasta_basica(),
        ), patch(
            "app.services.subasta_service.SubastaRepository.obtener_item_activo_con_puja",
            side_effect=[
                item_cierre(
                    item_id=1,
                    producto=11,
                    duenio=30,
                    puja_id=101,
                    puja_importe=1200.0,
                    cliente_ganador=20,
                ),
                item_cierre(
                    item_id=2,
                    producto=12,
                    duenio=31,
                    puja_id=102,
                    puja_importe=900.0,
                    cliente_ganador=21,
                    preciobase=800.0,
                    comision=80.0,
                ),
            ],
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
            "app.services.subasta_service.SubastaRepository.get_item_activo_detalle",
            side_effect=[item_detalle(id=2), None],
        ), patch(
            "app.services.subasta_service.SubastaRepository.contar_items_pendientes",
            side_effect=[1, 0],
        ), patch(
            "app.services.subasta_service.SubastaRepository.marcar_subasta_cerrada",
        ) as marcar_subasta, patch(
            "app.services.subasta_service.SubastaRepository.finalizar_sesiones",
        ) as finalizar_sesiones:
            first = SubastaService.cerrar_subasta(db, 5)
            second = SubastaService.cerrar_subasta(db, 5)

        self.assertFalse(first["subastaCerrada"])
        self.assertTrue(second["subastaCerrada"])
        self.assertEqual(cerrar_item.call_args_list, [call(db, 1, 101), call(db, 2, 102)])
        self.assertEqual(registrar_venta.call_count, 2)
        self.assertEqual(registrar_venta.call_args_list[0].args[4], 20)
        self.assertEqual(registrar_venta.call_args_list[1].args[4], 21)
        self.assertEqual(
            generar_pago.call_args_list,
            [
                call(db, 5, 20, 1200.0, 100.0, "USD"),
                call(db, 5, 21, 900.0, 80.0, "USD"),
            ],
        )
        marcar_subasta.assert_called_once_with(db, 5)
        finalizar_sesiones.assert_called_once_with(db, 5)

    def test_item_sin_pujas_se_marca_y_notifica_compra_empresa(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value=subasta_basica(),
        ), patch(
            "app.services.subasta_service.SubastaRepository.obtener_item_activo_con_puja",
            return_value=item_cierre(
                puja_id=None,
                puja_importe=None,
                cliente_ganador=None,
            ),
        ), patch(
            "app.services.subasta_service.SubastaRepository.cerrar_item",
        ) as cerrar_item, patch(
            "app.services.subasta_service.SubastaRepository.registrar_venta",
        ) as registrar_venta, patch(
            "app.services.subasta_service.SubastaRepository.generar_pago",
        ) as generar_pago, patch(
            "app.services.subasta_service.SubastaRepository.crear_notificacion",
        ) as notificar, patch(
            "app.services.subasta_service.SubastaRepository.get_item_activo_detalle",
            return_value=None,
        ), patch(
            "app.services.subasta_service.SubastaRepository.contar_items_pendientes",
            return_value=0,
        ), patch(
            "app.services.subasta_service.SubastaRepository.marcar_subasta_cerrada",
        ), patch(
            "app.services.subasta_service.SubastaRepository.finalizar_sesiones",
        ):
            result = SubastaService.cerrar_subasta(db, 5)

        self.assertTrue(result["subastaCerrada"])
        self.assertEqual(result["pagosGenerados"], 0)
        cerrar_item.assert_called_once_with(db, 1, None)
        registrar_venta.assert_not_called()
        generar_pago.assert_not_called()
        self.assertIn("adquirido por la empresa", notificar.call_args.args[3])

    def test_cierre_sin_items_pendientes_no_duplica_ventas_pagos_notificaciones(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value=subasta_basica(),
        ), patch(
            "app.services.subasta_service.SubastaRepository.obtener_item_activo_con_puja",
            return_value=None,
        ), patch(
            "app.services.subasta_service.SubastaRepository.registrar_venta",
        ) as registrar_venta, patch(
            "app.services.subasta_service.SubastaRepository.generar_pago",
        ) as generar_pago, patch(
            "app.services.subasta_service.SubastaRepository.crear_notificacion",
        ) as notificar, patch(
            "app.services.subasta_service.SubastaRepository.marcar_subasta_cerrada",
        ) as marcar_subasta, patch(
            "app.services.subasta_service.SubastaRepository.finalizar_sesiones",
        ) as finalizar_sesiones:
            result = SubastaService.cerrar_subasta(db, 5)

        self.assertEqual(result["itemsCerrados"], 0)
        self.assertTrue(result["subastaCerrada"])
        registrar_venta.assert_not_called()
        generar_pago.assert_not_called()
        notificar.assert_not_called()
        marcar_subasta.assert_called_once_with(db, 5)
        finalizar_sesiones.assert_called_once_with(db, 5)


class TestSubastaAvanceItemsRepository(unittest.TestCase):
    def test_cerrar_item_limpia_ganadores_previos_y_marca_solo_una_puja(self):
        db = MagicMock()
        cursor = MagicMock()
        db.cursor.return_value.__enter__.return_value = cursor

        SubastaRepository.cerrar_item(db, item_id=9, puja_id=77)

        self.assertEqual(cursor.execute.call_count, 3)
        self.assertIn("UPDATE itemscatalogo SET subastado", cursor.execute.call_args_list[0].args[0])
        self.assertIn("UPDATE pujos SET ganador = 'no'", cursor.execute.call_args_list[1].args[0])
        self.assertEqual(cursor.execute.call_args_list[1].args[1], (9,))
        self.assertIn("UPDATE pujos SET ganador = 'si'", cursor.execute.call_args_list[2].args[0])
        self.assertEqual(cursor.execute.call_args_list[2].args[1], (77,))

    def test_generar_pago_existente_pendiente_acumula_sin_insertar_duplicado(self):
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            "identificador": 44,
            "estado": "pendiente",
            "total_pujado": 1000.0,
            "comision": 100.0,
            "costo_envio": 0.0,
        }
        db.cursor.return_value.__enter__.return_value = cursor

        result = SubastaRepository.generar_pago(
            db,
            subasta_id=5,
            cliente_id=20,
            total_pujado=900.0,
            comision=80.0,
            moneda="USD",
        )

        self.assertEqual(result, 44)
        self.assertEqual(cursor.execute.call_count, 2)
        self.assertIn("UPDATE pagos", cursor.execute.call_args_list[1].args[0])
        self.assertEqual(
            cursor.execute.call_args_list[1].args[1],
            (1900.0, 180.0, 2080.0, "USD", 44),
        )


class TestSubastaAvanceItemsApi(unittest.TestCase):
    def test_cierre_parcial_emite_evento_item_sin_cierre_final(self):
        result = {
            "itemsCerrados": 1,
            "pagosGenerados": 1,
            "itemCerrado": {"id": 1},
            "itemActivo": {"id": 2},
            "itemsPendientes": 1,
            "subastaCerrada": False,
        }

        with patch(
            "app.api.subastas.SubastaService.cerrar_subasta",
            return_value=result,
        ), patch(
            "app.api.subastas.SubastaStreamer.broadcast",
            new_callable=AsyncMock,
        ) as broadcast:
            response = asyncio.run(close_auction(5, MagicMock(), {"usuarioId": 12}))

        self.assertEqual(response, result)
        broadcast.assert_called_once()
        self.assertEqual(broadcast.call_args.args[1], "item")

    def test_cierre_final_emite_item_y_cierre_final(self):
        result = {
            "itemsCerrados": 1,
            "pagosGenerados": 1,
            "itemCerrado": {"id": 2},
            "itemActivo": None,
            "itemsPendientes": 0,
            "subastaCerrada": True,
        }

        with patch(
            "app.api.subastas.SubastaService.cerrar_subasta",
            return_value=result,
        ), patch(
            "app.api.subastas.SubastaStreamer.broadcast",
            new_callable=AsyncMock,
        ) as broadcast:
            response = asyncio.run(close_auction(5, MagicMock(), {"usuarioId": 12}))

        self.assertEqual(response, result)
        self.assertEqual(broadcast.call_count, 2)
        self.assertEqual(broadcast.call_args_list[0].args[1], "item")
        self.assertEqual(broadcast.call_args_list[1].args[1], "cierre")


if __name__ == "__main__":
    unittest.main()
