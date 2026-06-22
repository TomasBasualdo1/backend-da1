import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.subastas import place_bid
from app.repositories.puja_repo import PujaRepository
from app.schemas.schemas import PujaRequest
from app.services.subasta_service import SubastaService


def puja_response(**overrides):
    response = {
        "pujaId": 77,
        "mejorOfertaActual": 1200.0,
        "limiteMinimo": 1210.0,
        "limiteMaximo": 1400.0,
        "moneda": "USD",
        "esGanadoraParcial": True,
    }
    response.update(overrides)
    return response


class TestPujaIdempotencyService(unittest.TestCase):
    def test_replay_misma_key_devuelve_respuesta_cacheada(self):
        db = MagicMock()
        record = {
            "identificador": 10,
            "subasta_id": 5,
            "item_id": 9,
            "importe": 1200.0,
            "estado": "completed",
            "puja_id": 77,
            "mejor_oferta_actual": 1200.0,
            "limite_minimo": 1210.0,
            "limite_maximo": 1400.0,
            "moneda": "USD",
            "es_ganadora_parcial": True,
        }

        with patch(
            "app.services.subasta_service.SubastaRepository.puede_participar",
            return_value=True,
        ), patch(
            "app.services.subasta_service.PujaRepository.lock_or_create_idempotency_record",
            return_value=record,
        ), patch(
            "app.services.subasta_service.SubastaRepository.registrar_puja"
        ) as registrar:
            result = SubastaService.procesar_puja(
                db,
                subasta_id=5,
                item_id=9,
                usuario_id=12,
                categoria_usuario="comun",
                importe=1200.0,
                idempotency_key="abc-123",
            )

        self.assertEqual(result["pujaId"], 77)
        self.assertTrue(result["_idempotentReplay"])
        registrar.assert_not_called()
        db.commit.assert_called_once()

    def test_misma_key_con_payload_distinto_devuelve_409(self):
        db = MagicMock()
        record = {
            "identificador": 10,
            "subasta_id": 5,
            "item_id": 9,
            "importe": 1200.0,
            "estado": "completed",
        }

        with patch(
            "app.services.subasta_service.SubastaRepository.puede_participar",
            return_value=True,
        ), patch(
            "app.services.subasta_service.PujaRepository.lock_or_create_idempotency_record",
            return_value=record,
        ):
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.procesar_puja(
                    db,
                    subasta_id=5,
                    item_id=9,
                    usuario_id=12,
                    categoria_usuario="comun",
                    importe=1300.0,
                    idempotency_key="abc-123",
                )

        self.assertEqual(ctx.exception.status_code, 409)
        db.rollback.assert_called_once()

    def test_key_nueva_registra_puja_y_guarda_respuesta(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.puede_participar",
            return_value=True,
        ), patch(
            "app.services.subasta_service.PujaRepository.lock_or_create_idempotency_record",
            return_value={"identificador": 10, "_created": True},
        ) as lock_or_create, patch(
            "app.services.subasta_service.SubastaRepository.get_asistente_id",
            return_value=44,
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_item_for_update",
            return_value={"id": 9, "preciobase": 1000.0, "subastado": "no"},
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_mejor_oferta",
            return_value=0.0,
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value={"categoria": "comun", "moneda": "USD"},
        ), patch(
            "app.services.subasta_service.SubastaRepository.registrar_puja",
            return_value=77,
        ) as registrar, patch(
            "app.services.subasta_service.PujaRepository.mark_idempotency_completed",
        ) as mark_completed:
            result = SubastaService.procesar_puja(
                db,
                subasta_id=5,
                item_id=9,
                usuario_id=12,
                categoria_usuario="comun",
                importe=1200.0,
                idempotency_key="abc-123",
            )

        lock_or_create.assert_called_once_with(db, 12, 5, 9, 1200.0, "abc-123")
        registrar.assert_called_once_with(db, 44, 9, 1200.0)
        mark_completed.assert_called_once_with(db, 10, result)
        db.commit.assert_called_once()

    def test_key_vacia_se_trata_como_ausente(self):
        self.assertIsNone(PujaRepository.normalize_idempotency_key("  "))


class TestPujaIdempotencyApi(unittest.TestCase):
    def test_endpoint_pasa_header_al_service(self):
        user = {"usuarioId": 12, "categoria": "comun"}

        with patch(
            "app.api.subastas.SubastaService.procesar_puja",
            return_value=puja_response(),
        ) as procesar, patch(
            "app.api.subastas.SubastaStreamer.broadcast",
            new_callable=AsyncMock,
        ) as broadcast:
            result = asyncio.run(
                place_bid(
                    5,
                    9,
                    PujaRequest(importe=1200.0),
                    idempotency_key="abc-123",
                    db=MagicMock(),
                    user=user,
                )
            )

        self.assertEqual(result.pujaId, 77)
        self.assertEqual(procesar.call_args.kwargs["idempotency_key"], "abc-123")
        broadcast.assert_called_once()
        _, event_type, event_data = broadcast.call_args.args
        self.assertEqual(event_type, "puja")
        self.assertEqual(event_data["usuarioId"], 12)
        self.assertEqual(event_data["importe"], 1200.0)
        self.assertEqual(event_data["moneda"], "USD")
        self.assertTrue(event_data["esGanadoraParcial"])

    def test_endpoint_no_reemite_sse_en_replay(self):
        user = {"usuarioId": 12, "categoria": "comun"}

        with patch(
            "app.api.subastas.SubastaService.procesar_puja",
            return_value=puja_response(_idempotentReplay=True),
        ), patch(
            "app.api.subastas.SubastaStreamer.broadcast",
            new_callable=AsyncMock,
        ) as broadcast:
            result = asyncio.run(
                place_bid(
                    5,
                    9,
                    PujaRequest(importe=1200.0),
                    idempotency_key="abc-123",
                    db=MagicMock(),
                    user=user,
                )
            )

        self.assertEqual(result.pujaId, 77)
        broadcast.assert_not_called()
