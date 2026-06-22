import asyncio
import inspect
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

import app.api.notificaciones as notificaciones_router
from app.api.notificaciones import list_notifications, mark_notification_read
from app.services.notificacion_service import NotificacionService


def make_db(fetchone_value=None, fetchall_value=None):
    db = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_value
    cursor.fetchall.return_value = fetchall_value if fetchall_value is not None else []
    db.cursor.return_value.__enter__.return_value = cursor
    return db, cursor


class TestNotificacionesApi(unittest.TestCase):
    def setUp(self):
        self.user = {"usuarioId": 123}

    def test_list_notifications_returns_same_response_shape(self):
        fecha = datetime(2026, 6, 22, 12, 30, tzinfo=timezone.utc)
        db, cursor = make_db(
            fetchall_value=[
                {
                    "id": 7,
                    "tipo": "sistema",
                    "mensaje": "Tu registro fue aprobado",
                    "fechaHora": fecha,
                    "leida": False,
                }
            ]
        )

        response = asyncio.run(list_notifications(db=db, user=self.user))

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].id, 7)
        self.assertEqual(response[0].tipo.value, "sistema")
        self.assertEqual(response[0].mensaje, "Tu registro fue aprobado")
        self.assertEqual(response[0].fechaHora, fecha)
        self.assertFalse(response[0].leida)

        executed_sql = cursor.execute.call_args.args[0]
        self.assertIn('fecha_hora as "fechaHora"', executed_sql)
        self.assertIn("ORDER BY fecha_hora DESC", executed_sql)
        self.assertEqual(cursor.execute.call_args.args[1], (123,))

    def test_mark_notification_read_updates_and_commits(self):
        db, cursor = make_db(fetchone_value={"exists": 1})

        response = asyncio.run(mark_notification_read(7, db=db, user=self.user))

        self.assertEqual(response, {"message": "Notificación marcada como leída"})
        self.assertEqual(cursor.execute.call_count, 2)
        self.assertIn(
            "SELECT 1 FROM notificaciones",
            cursor.execute.call_args_list[0].args[0],
        )
        self.assertEqual(cursor.execute.call_args_list[0].args[1], (7, 123))
        self.assertEqual(
            cursor.execute.call_args_list[1].args[0],
            "UPDATE notificaciones SET leida = true WHERE identificador = %s",
        )
        self.assertEqual(cursor.execute.call_args_list[1].args[1], (7,))
        db.commit.assert_called_once()

    def test_mark_notification_read_not_found_keeps_404_message(self):
        db, _ = make_db(fetchone_value=None)

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(mark_notification_read(7, db=db, user=self.user))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Notificación no encontrada")
        db.commit.assert_not_called()

    def test_router_delegates_to_service_without_sql_inline(self):
        source = inspect.getsource(notificaciones_router)
        self.assertNotIn("cursor.execute", source)
        self.assertNotIn("db.cursor", source)

        with patch(
            "app.api.notificaciones.NotificacionService.list_notifications",
            return_value=[
                {
                    "id": 1,
                    "tipo": "pago",
                    "mensaje": "Pago registrado",
                    "fechaHora": datetime(2026, 6, 22, tzinfo=timezone.utc),
                    "leida": True,
                }
            ],
        ) as list_service:
            response = asyncio.run(
                notificaciones_router.list_notifications(db=MagicMock(), user=self.user)
            )

        self.assertEqual(response[0].id, 1)
        list_service.assert_called_once()


class TestNotificacionService(unittest.TestCase):
    def test_service_decides_404_before_update(self):
        db = MagicMock()
        with patch(
            "app.services.notificacion_service.NotificacionRepository.exists_for_user",
            return_value=False,
        ) as exists_for_user, patch(
            "app.services.notificacion_service.NotificacionRepository.mark_read"
        ) as mark_read:
            with self.assertRaises(HTTPException) as ctx:
                NotificacionService.mark_read(db, 123, 7)

        self.assertEqual(ctx.exception.status_code, 404)
        exists_for_user.assert_called_once_with(db, 7, 123)
        mark_read.assert_not_called()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
