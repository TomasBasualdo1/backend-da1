import asyncio
import json

from fastapi import APIRouter, Depends, Header, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from psycopg import Connection

from app.core.database import get_db_connection
from app.core.security import decode_access_token
from app.dependencies import get_current_user, get_db, require_admin, security
from app.services.auth_service import AuthService
from app.services.subasta_service import SubastaService
from app.services.streamer import SubastaStreamer
from app.schemas.schemas import (
    SubastaListado, SubastaListadoPublico,
    SubastaDetalle, SubastaDetallePublica,
    PujaRequest, PujaResponse, Puja, Pago, PagoRequest,
)

router = APIRouter(prefix="/subastas")


def get_stream_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    with get_db_connection() as db:
        if AuthService.is_token_blacklisted(db, payload.get("jti")):
            raise HTTPException(status_code=401, detail="Token revoked")

    return payload


# ─────────────────── LISTADOS PÚBLICOS ───────────────────

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


# ─────────────────── LISTADOS AUTENTICADOS ───────────────────

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


# ─────────────────── JOIN / LEAVE ───────────────────

@router.post("/{id}/join", status_code=201)
async def join_auction(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    categoria = user["categoria"].value if hasattr(user["categoria"], "value") else str(user["categoria"])
    return SubastaService.join_subasta(db, id, user["usuarioId"], categoria)


@router.delete("/{id}/join", status_code=204)
async def leave_auction(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    SubastaService.leave_subasta(db, id, user["usuarioId"])
    return None


# ─────────────────── STREAMING (SSE) ───────────────────

@router.get("/{id}/stream")
async def stream_auction(
    id: int,
    user: dict = Depends(get_stream_user),
):
    """
    Endpoint SSE: el frontend se conecta aquí y recibe en tiempo real
    cada nueva puja o cambio de ítem mientras la subasta esté abierta.
    """
    categoria = user["categoria"].value if hasattr(user["categoria"], "value") else str(user["categoria"])
    # Validar con una conexion corta para no sostener Postgres durante todo el stream.
    with get_db_connection() as db:
        SubastaService.validar_acceso_stream(
            db,
            subasta_id=id,
            usuario_id=user["usuarioId"],
            categoria_usuario=categoria,
        )

    queue = SubastaStreamer.subscribe(id)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive para no cortar la conexion
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            SubastaStreamer.unsubscribe(id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ─────────────────── PUJAR ───────────────────

@router.post("/{id}/items/{item_id}/pujar", status_code=201, response_model=PujaResponse)
async def place_bid(
    id: int,
    item_id: int,
    body: PujaRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    categoria = user["categoria"].value if hasattr(user["categoria"], "value") else str(user["categoria"])
    resultado = SubastaService.procesar_puja(
        db=db,
        subasta_id=id,
        item_id=item_id,
        usuario_id=user["usuarioId"],
        categoria_usuario=categoria,
        importe=body.importe,
        idempotency_key=idempotency_key,
    )

    is_replay = bool(resultado.pop("_idempotentReplay", False))
    if not is_replay:
        # Notificar a todos los usuarios conectados via SSE
        await SubastaStreamer.broadcast(id, "puja", {
            "itemId": item_id,
            "usuarioId": user["usuarioId"],
            "importe": resultado["mejorOfertaActual"],
            "mejorOfertaActual": resultado["mejorOfertaActual"],
            "limiteMinimo": resultado["limiteMinimo"],
            "limiteMaximo": resultado["limiteMaximo"],
            "pujaId": resultado["pujaId"],
            "moneda": resultado["moneda"],
            "esGanadoraParcial": resultado["esGanadoraParcial"],
        })

    return PujaResponse(**resultado)


# ─────────────────── HISTORIAL ───────────────────

@router.get("/{id}/historial", response_model=list[Puja])
async def get_auction_history(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return SubastaService.get_historial(db, id, user["usuarioId"])


# ─────────────────── PAGOS ───────────────────

@router.get("/{id}/pagos", response_model=Pago)
async def get_auction_payment(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return SubastaService.get_pago(db, id, user["usuarioId"])


@router.post("/{id}/pagos")
async def confirm_auction_payment(
    id: int,
    body: PagoRequest,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return SubastaService.confirmar_pago(
        db=db,
        subasta_id=id,
        usuario_id=user["usuarioId"],
        medio_pago_id=body.medioPagoId,
        modo_entrega=body.modoEntrega.value,
        direccion_envio=body.direccionEnvio,
        acepta_perder_seguro=body.aceptaPerderSeguro or False,
    )


# ─────────────────── CIERRE ───────────────────

@router.post("/{id}/cerrar")
async def close_auction(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    require_admin(user)
    resultado = SubastaService.cerrar_subasta(db, id)

    # Notificar via SSE que la subasta se cerró
    await SubastaStreamer.broadcast(id, "cierre", {
        "message": "La subasta ha finalizado",
        "itemsCerrados": resultado["itemsCerrados"],
    })

    return resultado
