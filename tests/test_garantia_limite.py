import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.repositories.subasta_repo import SubastaRepository
from app.services.subasta_service import SubastaService


def medio_pago(**overrides):
    data = {
        "id": 99,
        "cliente_id": 20,
        "estado_verificacion": "validado",
        "moneda": "USD",
        "limite_reservado": 2000.0,
    }
    data.update(overrides)
    return data


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


def make_db(fetchone_value=None, fetchall_value=None):
    db = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_value
    cursor.fetchall.return_value = fetchall_value if fetchall_value is not None else []
    db.cursor.return_value.__enter__.return_value = cursor
    return db, cursor


@contextmanager
def puja_context(
    *,
    garantia_total=2000.0,
    pagos_pendientes=0.0,
    pujas_ganadoras=None,
    puede_participar=True,
    asistente_id=44,
    precio_base=1000.0,
    mejor_oferta=0.0,
    categoria_subasta="comun",
    puja_id=77,
    idempotency_record=None,
):
    db = MagicMock()
    if pujas_ganadoras is None:
        pujas_ganadoras = []

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaService.procesar_vencimientos",
                return_value={},
            )
        )
        stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaRepository.puede_participar",
                return_value=puede_participar,
            )
        )
        lock_or_create = stack.enter_context(
            patch(
                "app.services.subasta_service.PujaRepository.lock_or_create_idempotency_record",
                return_value=idempotency_record,
            )
        )
        stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaRepository.get_asistente_id",
                return_value=asistente_id,
            )
        )
        stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaRepository.get_item_for_update",
                return_value={
                    "id": 9,
                    "preciobase": precio_base,
                    "subastado": "no",
                },
            )
        )
        stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaRepository.get_mejor_oferta",
                return_value=mejor_oferta,
            )
        )
        stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaRepository.get_subasta_basica",
                return_value={"identificador": 5, "estado": "abierta", "categoria": categoria_subasta, "moneda": "USD"},
            )
        )
        get_garantia = stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaRepository.get_garantia_validada_for_update",
                return_value={"total": garantia_total, "medios": 1, "moneda": "USD"},
            )
        )
        stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaRepository.get_exposicion_pagos_pendientes",
                return_value=pagos_pendientes,
            )
        )
        stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaRepository.get_pujas_ganadoras_parciales_activas",
                return_value=pujas_ganadoras,
            )
        )
        registrar = stack.enter_context(
            patch(
                "app.services.subasta_service.SubastaRepository.registrar_puja",
                return_value=puja_id,
            )
        )
        mark_completed = stack.enter_context(
            patch(
                "app.services.subasta_service.PujaRepository.mark_idempotency_completed",
            )
        )

        yield {
            "db": db,
            "registrar": registrar,
            "mark_completed": mark_completed,
            "get_garantia": get_garantia,
            "lock_or_create": lock_or_create,
        }


class TestGarantiaLimiteService(unittest.TestCase):
    def test_usuario_con_garantia_suficiente_puede_pujar(self):
        with puja_context(
            garantia_total=2000.0,
            pagos_pendientes=300.0,
            pujas_ganadoras=[{"itemId": 22, "importe": 400.0}],
        ) as ctx:
            result = SubastaService.procesar_puja(
                ctx["db"], 5, 9, 20, "comun", 1000.0
            )

        self.assertEqual(result["pujaId"], 77)
        ctx["registrar"].assert_called_once_with(ctx["db"], 44, 9, 1000.0)
        ctx["db"].commit.assert_called_once()

    def test_usuario_con_garantia_insuficiente_no_puede_pujar(self):
        with puja_context(garantia_total=1000.0, pagos_pendientes=200.0) as ctx:
            with self.assertRaises(HTTPException) as raised:
                SubastaService.procesar_puja(
                    ctx["db"], 5, 9, 20, "comun", 1000.0
                )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail["codigo"], "GARANTIA_INSUFICIENTE")
        self.assertEqual(raised.exception.detail["garantiaDisponible"], 800.0)
        self.assertEqual(raised.exception.detail["importeRequerido"], 1000.0)
        ctx["registrar"].assert_not_called()
        ctx["db"].rollback.assert_called_once()

    def test_exposicion_suma_pagos_pendientes(self):
        with puja_context(
            garantia_total=1000.0,
            pagos_pendientes=500.0,
            precio_base=500.0,
        ) as ctx:
            with self.assertRaises(HTTPException):
                SubastaService.procesar_puja(
                    ctx["db"], 5, 9, 20, "comun", 600.0
                )

        ctx["registrar"].assert_not_called()

    def test_exposicion_suma_pujas_ganadoras_parciales_activas(self):
        with puja_context(
            garantia_total=1000.0,
            pujas_ganadoras=[{"itemId": 30, "importe": 500.0}],
            precio_base=500.0,
        ) as ctx:
            with self.assertRaises(HTTPException):
                SubastaService.procesar_puja(
                    ctx["db"], 5, 9, 20, "comun", 600.0
                )

        ctx["registrar"].assert_not_called()

    def test_exposicion_no_suma_pujas_superadas(self):
        with puja_context(
            garantia_total=700.0,
            pujas_ganadoras=[],
            precio_base=500.0,
        ) as ctx:
            result = SubastaService.procesar_puja(
                ctx["db"], 5, 9, 20, "comun", 600.0
            )

        self.assertEqual(result["pujaId"], 77)
        ctx["registrar"].assert_called_once()

    def test_nueva_puja_candidata_se_incluye_en_exposicion(self):
        with puja_context(
            garantia_total=500.0,
            pagos_pendientes=0.0,
            pujas_ganadoras=[],
            precio_base=500.0,
        ) as ctx:
            with self.assertRaises(HTTPException):
                SubastaService.procesar_puja(
                    ctx["db"], 5, 9, 20, "comun", 600.0
                )

        ctx["registrar"].assert_not_called()

    def test_si_usuario_ya_gana_mismo_item_reemplaza_puja_anterior(self):
        with puja_context(
            garantia_total=1000.0,
            pujas_ganadoras=[{"itemId": 9, "importe": 600.0}],
            precio_base=2000.0,
            mejor_oferta=600.0,
        ) as ctx:
            result = SubastaService.procesar_puja(
                ctx["db"], 5, 9, 20, "comun", 900.0
            )

        self.assertEqual(result["pujaId"], 77)
        ctx["registrar"].assert_called_once()

    def test_puja_rechazada_por_garantia_no_completa_idempotencia(self):
        with puja_context(
            garantia_total=1000.0,
            pagos_pendientes=200.0,
            idempotency_record={"identificador": 55, "_created": True},
        ) as ctx:
            with self.assertRaises(HTTPException):
                SubastaService.procesar_puja(
                    ctx["db"],
                    5,
                    9,
                    20,
                    "comun",
                    1000.0,
                    idempotency_key="bid-123",
                )

        ctx["registrar"].assert_not_called()
        ctx["mark_completed"].assert_not_called()
        ctx["db"].rollback.assert_called_once()

    def test_replay_idempotente_completed_no_recalcula_exposicion(self):
        db = MagicMock()
        record = {
            "identificador": 10,
            "subasta_id": 5,
            "item_id": 9,
            "importe": 1000.0,
            "estado": "completed",
            "puja_id": 77,
            "mejor_oferta_actual": 1000.0,
            "limite_minimo": 1010.0,
            "limite_maximo": 1200.0,
            "moneda": "USD",
            "es_ganadora_parcial": True,
        }

        with patch(
            "app.services.subasta_service.SubastaService.procesar_vencimientos",
            return_value={},
        ), patch(
            "app.services.subasta_service.SubastaRepository.puede_participar",
            return_value=True,
        ), patch(
            "app.services.subasta_service.PujaRepository.lock_or_create_idempotency_record",
            return_value=record,
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_garantia_validada_for_update",
        ) as get_garantia, patch(
            "app.services.subasta_service.SubastaRepository.registrar_puja",
        ) as registrar:
            result = SubastaService.procesar_puja(
                db,
                5,
                9,
                20,
                "comun",
                1000.0,
                idempotency_key="bid-123",
            )

        self.assertTrue(result["_idempotentReplay"])
        get_garantia.assert_not_called()
        registrar.assert_not_called()
        db.commit.assert_called_once()

    def test_usuario_con_multa_o_bloqueo_se_rechaza_antes_de_garantia(self):
        with puja_context(puede_participar=False) as ctx:
            with self.assertRaises(HTTPException) as raised:
                SubastaService.procesar_puja(
                    ctx["db"], 5, 9, 20, "comun", 1000.0
                )

        self.assertEqual(raised.exception.status_code, 403)
        ctx["get_garantia"].assert_not_called()
        ctx["registrar"].assert_not_called()

    def test_confirmar_pago_con_limite_suficiente_sigue_funcionando(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.get_pago_usuario",
            return_value=pago_pendiente(totalPujado=1000.0, comision=100.0),
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_medio_pago_para_cliente",
            return_value=medio_pago(limite_reservado=2000.0),
        ), patch(
            "app.services.subasta_service.SubastaRepository.confirmar_pago",
        ) as confirmar, patch(
            "app.services.subasta_service.SubastaRepository.crear_notificacion",
        ):
            result = SubastaService.confirmar_pago(
                db,
                5,
                20,
                99,
                "envio",
                "Calle 123",
                False,
            )

        self.assertEqual(result, {"message": "Pago confirmado exitosamente"})
        confirmar.assert_called_once()
        db.commit.assert_called_once()


class TestGarantiaLimiteRepository(unittest.TestCase):
    def test_multiples_medios_validados_con_limite_se_suman(self):
        db, cursor = make_db(
            fetchall_value=[
                {"identificador": 1, "limite_reservado": 500.0},
                {"identificador": 2, "limite_reservado": 750.0},
            ]
        )

        result = SubastaRepository.get_garantia_validada_for_update(db, 20, "USD")

        self.assertEqual(result["total"], 1250.0)
        self.assertEqual(result["medios"], 2)

        executed_sql = cursor.execute.call_args.args[0]
        self.assertIn("estado_verificacion = 'validado'", executed_sql)
        self.assertIn("tipo IN ('cheque_certificado', 'cuenta_bancaria')", executed_sql)
        self.assertIn("FOR UPDATE", executed_sql)

    def test_medio_no_validado_no_aporta_limite_por_filtro_sql(self):
        db, cursor = make_db(fetchall_value=[])

        result = SubastaRepository.get_garantia_validada_for_update(db, 20, "USD")

        self.assertEqual(result["total"], 0.0)
        executed_sql = cursor.execute.call_args.args[0]
        self.assertIn("estado_verificacion = 'validado'", executed_sql)

    def test_medio_con_limite_cero_no_aporta_por_filtro_sql(self):
        db, cursor = make_db(fetchall_value=[])

        result = SubastaRepository.get_garantia_validada_for_update(db, 20, "USD")

        self.assertEqual(result["total"], 0.0)
        executed_sql = cursor.execute.call_args.args[0]
        self.assertIn("limite_reservado > 0", executed_sql)

    def test_query_de_pujas_activas_solo_devuelve_mejor_puja_por_item(self):
        db, cursor = make_db(
            fetchall_value=[
                {"itemId": 9, "importe": 600.0},
                {"itemId": 30, "importe": 500.0},
            ]
        )

        rows = SubastaRepository.get_pujas_ganadoras_parciales_activas(db, 20)

        self.assertEqual(rows[0]["importe"], 600.0)
        executed_sql = cursor.execute.call_args.args[0]
        self.assertIn("SELECT DISTINCT ON (pu.item)", executed_sql)
        self.assertIn("s.estado = 'abierta'", executed_sql)
        self.assertIn("WHERE mejores.cliente = %s", executed_sql)


if __name__ == "__main__":
    unittest.main()
