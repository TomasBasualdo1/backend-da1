from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.repositories.articulo_repo import ArticuloRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.services.email_service import EmailService
from app.services.subasta_service import SubastaService
from app.schemas.schemas import (
    Articulo,
    ArticuloEvaluacion,
    CatalogoItemInput,
    SubastaCreate,
)

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


@router.post("/articulos/{id}/evaluar", response_model=Articulo)
async def evaluate_article(
    id: int,
    evaluacion: ArticuloEvaluacion,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if user.get("usuarioId") != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado (solo administradores).",
        )

    return ArticuloRepository.evaluar_articulo(db, id, evaluacion)


@router.post("/subastas", status_code=201)
async def create_auction(
    subasta: SubastaCreate,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return SubastaService.create_subasta(db, subasta, user.get("usuarioId"))


@router.post("/subastas/{id}/catalogo/items", status_code=201)
async def add_catalog_item(
    id: int,
    item: CatalogoItemInput,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return SubastaService.add_catalog_item(db, id, item, user.get("usuarioId"))
