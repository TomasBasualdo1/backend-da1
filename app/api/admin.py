from fastapi import APIRouter, Depends
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.repositories.usuario_repo import UsuarioRepository
from app.services.email_service import EmailService

router = APIRouter(prefix="/admin")


@router.post("/usuarios/{id}/verificar")
async def verify_user(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = UsuarioRepository.aprobar_registro(db, id)
    EmailService.send_verification_email(result["email"], result["token"])
    return {"message": "Usuario aprobado. Se envió el email de verificación."}


@router.post("/medios-pago/{id}/verificar")
async def verify_payment_method(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/articulos/{id}/evaluar")
async def evaluate_article(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/subastas", status_code=201)
async def create_auction(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/subastas/{id}/catalogo/items", status_code=201)
async def add_catalog_item(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass
