import asyncio
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.subastas import stream_auction
from app.services.subasta_service import SubastaService


@contextmanager
def fake_db_context(db):
    yield db


class TestSubastaStreamAccess(unittest.TestCase):
    def test_valida_acceso_stream_con_sesion_activa(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value={"estado": "abierta", "categoria": "oro", "moneda": "USD"},
        ), patch(
            "app.services.subasta_service.SubastaRepository.puede_participar",
            return_value=True,
        ), patch(
            "app.services.subasta_service.SubastaRepository.tiene_medio_pago_validado",
            return_value=True,
        ), patch(
            "app.services.subasta_service.SubastaRepository.tiene_sesion_activa",
            return_value=True,
        ) as tiene_sesion:
            SubastaService.validar_acceso_stream(
                db,
                subasta_id=5,
                usuario_id=12,
                categoria_usuario="oro",
            )

        tiene_sesion.assert_called_once_with(db, 5, 12)

    def test_valida_acceso_stream_rechaza_usuario_sin_join(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value={"estado": "abierta", "categoria": "comun", "moneda": "USD"},
        ), patch(
            "app.services.subasta_service.SubastaRepository.puede_participar",
            return_value=True,
        ), patch(
            "app.services.subasta_service.SubastaRepository.tiene_medio_pago_validado",
            return_value=True,
        ), patch(
            "app.services.subasta_service.SubastaRepository.tiene_sesion_activa",
            return_value=False,
        ):
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.validar_acceso_stream(
                    db,
                    subasta_id=5,
                    usuario_id=12,
                    categoria_usuario="comun",
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("unirte", ctx.exception.detail)

    def test_endpoint_stream_valida_antes_de_suscribir(self):
        db = MagicMock()
        queue = asyncio.Queue()
        user = {"usuarioId": 12, "categoria": "platino"}

        with patch(
            "app.api.subastas.get_db_connection",
            return_value=fake_db_context(db),
        ), patch(
            "app.api.subastas.SubastaService.validar_acceso_stream",
        ) as validar, patch(
            "app.api.subastas.SubastaStreamer.subscribe",
            return_value=queue,
        ) as subscribe:
            response = asyncio.run(stream_auction(5, user=user))

        validar.assert_called_once_with(
            db,
            subasta_id=5,
            usuario_id=12,
            categoria_usuario="platino",
        )
        subscribe.assert_called_once_with(5)
        self.assertEqual(response.media_type, "text/event-stream")
