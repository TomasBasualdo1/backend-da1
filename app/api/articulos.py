from fastapi import APIRouter, Depends
from psycopg import Connection

from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/articulos")


@router.post("", status_code=201)
async def create_article(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.get("/mis-publicaciones")
async def list_my_articles(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.get("/{id}")
async def get_article_detail(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/{id}/aceptar-tasacion")
async def accept_valuation(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/{id}/seguro/aumentar")
async def request_insurance_increase(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass
