from typing import Optional
from fastapi import APIRouter, Depends, Form, File, UploadFile
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.schemas.schemas import (
    Usuario,
    MedioPago,
    MedioPagoInput,
    MedioPagoUpdate,
    UsuarioMetricas,
    Multa,
    MultaPagoRequest,
)
from app.services.usuario_service import UsuarioService

router = APIRouter(prefix="/usuarios")


@router.get("/me", response_model=Usuario)
async def get_profile(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    profile_data = UsuarioService.get_profile(db, user["usuarioId"])
    return Usuario(**profile_data)


@router.patch("/me")
async def update_profile(
    nombre: Optional[str] = Form(None),
    apellido: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None),
    telefono: Optional[str] = Form(None),
    foto: Optional[UploadFile] = File(None),
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return await UsuarioService.update_profile(
        db,
        user["usuarioId"],
        nombre=nombre,
        apellido=apellido,
        direccion=direccion,
        telefono=telefono,
        foto=foto,
    )


@router.delete("/me/foto")
async def delete_profile_picture(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return UsuarioService.delete_profile_picture(db, user["usuarioId"])


@router.get("/me/medios-pago", response_model=list[MedioPago])
async def list_payment_methods(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return [
        MedioPago(**row)
        for row in UsuarioService.list_payment_methods(db, user["usuarioId"])
    ]


@router.post("/me/medios-pago", status_code=201)
async def add_payment_method(
    body: MedioPagoInput,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return UsuarioService.add_payment_method(db, user["usuarioId"], body)


@router.patch("/me/medios-pago/{id}")
async def update_payment_method(
    id: int,
    body: MedioPagoUpdate,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return UsuarioService.update_payment_method(db, user["usuarioId"], id, body)


@router.delete("/me/medios-pago/{id}", status_code=204)
async def delete_payment_method(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    UsuarioService.delete_payment_method(db, user["usuarioId"], id)


@router.get("/me/metricas", response_model=UsuarioMetricas)
async def get_metrics(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return UsuarioMetricas(**UsuarioService.get_metrics(db, user["usuarioId"]))


@router.get("/me/multas", response_model=list[Multa])
async def list_fines(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return [Multa(**multa) for multa in UsuarioService.list_multas(db, user["usuarioId"])]


@router.post("/me/multas/pagar")
async def pay_fine(
    body: MultaPagoRequest,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return UsuarioService.pagar_multa(
        db,
        user["usuarioId"],
        body.multaId,
        body.medioPagoId,
    )
