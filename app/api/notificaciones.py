from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.schemas.schemas import Notificacion

router = APIRouter(prefix="/usuarios")


@router.get("/me/notificaciones", response_model=list[Notificacion])
async def list_notifications(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                identificador as id,
                tipo,
                mensaje,
                fecha_hora as "fechaHora",
                leida
            FROM notificaciones
            WHERE persona_id = %s
            ORDER BY fecha_hora DESC
            """,
            (user["usuarioId"],),
        )
        rows = cursor.fetchall()
        return [
            Notificacion(
                id=row["id"],
                tipo=row["tipo"],
                mensaje=row["mensaje"],
                fechaHora=row["fechaHora"],
                leida=row["leida"],
            )
            for row in rows
        ]


@router.post("/me/notificaciones/{id}/leer")
async def mark_notification_read(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM notificaciones WHERE identificador = %s AND persona_id = %s",
            (id, user["usuarioId"]),
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Notificación no encontrada")

        cursor.execute(
            "UPDATE notificaciones SET leida = true WHERE identificador = %s",
            (id,),
        )
    db.commit()
    return {"message": "Notificación marcada como leída"}

