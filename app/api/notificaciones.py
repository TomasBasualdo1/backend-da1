from fastapi import APIRouter, Depends
from psycopg import Connection

from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/usuarios")


@router.get("/me/notificaciones")
async def list_notifications(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/me/notificaciones/{id}/leer")
async def mark_notification_read(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass
