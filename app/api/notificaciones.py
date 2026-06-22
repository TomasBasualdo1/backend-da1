from fastapi import APIRouter, Depends
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.schemas.schemas import Notificacion
from app.services.notificacion_service import NotificacionService

router = APIRouter(prefix="/usuarios")


@router.get("/me/notificaciones", response_model=list[Notificacion])
async def list_notifications(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return [
        Notificacion(**row)
        for row in NotificacionService.list_notifications(db, user["usuarioId"])
    ]


@router.post("/me/notificaciones/{id}/leer")
async def mark_notification_read(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return NotificacionService.mark_read(db, user["usuarioId"], id)
