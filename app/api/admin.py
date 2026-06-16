from fastapi import APIRouter, Depends
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.repositories.usuario_repo import UsuarioRepository
from app.services.email_service import EmailService
from app.schemas.schemas import UsuarioVerificacion

router = APIRouter(prefix="/admin")


@router.post("/usuarios/{id}/verificar")
async def verify_user(
    id: int,
    body: UsuarioVerificacion,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if body.admitido:
        # If category is provided, extract its string value
        categoria_str = body.categoria.value if body.categoria else None
        result = UsuarioRepository.aprobar_registro(db, id, categoria_str)
        try:
            EmailService.send_verification_email(result["email"], result["token"])
        except Exception as e:
            print(f"Error sending verification email: {e}")
        return {"message": "Usuario aprobado. Se envió el email de verificación."}
    else:
        result = UsuarioRepository.rechazar_registro(db, id, body.motivoRechazo)
        try:
            EmailService.send_rejection_email(result["email"], body.motivoRechazo or "No especificado")
        except Exception as e:
            print(f"Error sending rejection email: {e}")
        return {"message": "Usuario rechazado. Se envió la notificación de rechazo."}



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
