from fastapi import APIRouter, Depends, Request, HTTPException
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.services.subasta_service import SubastaService
from app.schemas.schemas import SubastaListado, SubastaListadoPublico, SubastaDetalle, SubastaDetallePublica

router = APIRouter(prefix="/subastas")


@router.get("/publicas", response_model=list[SubastaListadoPublico])
async def list_public_auctions(db: Connection = Depends(get_db)):
    return SubastaService.get_publicas(db)


@router.get("/publicas/{id}", response_model=SubastaDetallePublica)
async def get_public_auction_detail(
    id: int,
    request: Request,
    db: Connection = Depends(get_db),
):
    base_url = str(request.base_url).rstrip("/")
    subasta = SubastaService.get_publica_detalle(db, id, base_url)
    if not subasta:
        raise HTTPException(status_code=404, detail="Subasta no encontrada")
    return subasta


@router.get("", response_model=list[SubastaListado])
async def list_auctions(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return SubastaService.get_todas(db)


@router.get("/{id}", response_model=SubastaDetalle)
async def get_auction_detail(
    id: int,
    request: Request,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    base_url = str(request.base_url).rstrip("/")
    subasta = SubastaService.get_detalle(db, id, base_url)
    if not subasta:
        raise HTTPException(status_code=404, detail="Subasta no encontrada")
    return subasta



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
