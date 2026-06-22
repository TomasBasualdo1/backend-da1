from fastapi import HTTPException, status
from psycopg import Connection

from app.repositories.notificacion_repo import NotificacionRepository


class NotificacionService:
    @staticmethod
    def list_notifications(db: Connection, usuario_id: int) -> list[dict]:
        return NotificacionRepository.list_for_user(db, usuario_id)

    @staticmethod
    def mark_read(db: Connection, usuario_id: int, notificacion_id: int) -> dict:
        if not NotificacionRepository.exists_for_user(db, notificacion_id, usuario_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notificación no encontrada",
            )

        NotificacionRepository.mark_read(db, notificacion_id)
        db.commit()
        return {"message": "Notificación marcada como leída"}
