from fastapi import APIRouter, Depends
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.schemas.schemas import ArticuloInput, Articulo, SeguroAumentoRequest
from app.services.articulo_service import ArticuloService

router = APIRouter(prefix="/articulos")


@router.post("", status_code=201)
async def create_article(
    body: ArticuloInput,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return ArticuloService.crear_articulo(db, user["usuarioId"], body)


@router.get("/mis-publicaciones", response_model=list[Articulo])
async def list_my_articles(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return ArticuloService.get_mis_articulos(db, user["usuarioId"])


@router.get("/{id}", response_model=Articulo)
async def get_article_detail(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return ArticuloService.get_articulo_detalle(db, id, user["usuarioId"])


@router.post("/{id}/aceptar-tasacion")
async def accept_valuation(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return ArticuloService.aceptar_tasacion(db, id, user["usuarioId"])


@router.post("/{id}/seguro/aumentar")
async def request_insurance_increase(
    id: int,
    body: SeguroAumentoRequest,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return ArticuloService.solicitar_aumento_seguro(db, id, user["usuarioId"], body.montoNuevo)
