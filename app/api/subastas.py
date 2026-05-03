from fastapi import APIRouter, Depends
from psycopg import Connection

from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/subastas")


@router.get("/publicas")
async def list_public_auctions(db: Connection = Depends(get_db)):
    pass


@router.get("/publicas/{id}")
async def get_public_auction_detail(
    id: int,
    db: Connection = Depends(get_db),
):
    pass


@router.get("")
async def list_auctions(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.get("/{id}")
async def get_auction_detail(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/{id}/join", status_code=201)
async def join_auction(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.delete("/{id}/join", status_code=204)
async def leave_auction(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.get("/{id}/stream")
async def stream_auction(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.get("/{id}/historial")
async def get_auction_history(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.get("/{id}/pagos")
async def get_auction_payment(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/{id}/pagos")
async def confirm_auction_payment(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/{id}/cerrar")
async def close_auction(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass


@router.post("/{id}/items/{item_id}/pujar", status_code=201)
async def place_bid(
    id: int,
    item_id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    pass
