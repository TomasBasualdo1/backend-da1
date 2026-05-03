from fastapi import APIRouter, Depends
from psycopg import Connection

from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/usuarios")


@router.get("/me")
async def get_profile(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.patch("/me")
async def update_profile(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.get("/me/medios-pago")
async def list_payment_methods(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/me/medios-pago", status_code=201)
async def add_payment_method(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.patch("/me/medios-pago/{id}")
async def update_payment_method(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.delete("/me/medios-pago/{id}", status_code=204)
async def delete_payment_method(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.get("/me/metricas")
async def get_metrics(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.get("/me/multas")
async def list_fines(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/me/multas/pagar")
async def pay_fine(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass
