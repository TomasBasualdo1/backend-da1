from uuid import uuid4
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from psycopg import Connection

from app.dependencies import get_current_user, get_db
from app.schemas.schemas import (
    AceptarTasacionRequest,
    Articulo,
    ArticuloInput,
    SeguroAumentoRequest,
)
from app.services.articulo_service import ArticuloService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/articulos")


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "si", "sí", "yes", "on")


async def _upload_form_files(files, prefix: str) -> list[str]:
    urls: list[str] = []
    for index, file in enumerate(files or []):
        if isinstance(file, str):
            parsed = urlparse(file)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                urls.append(file)
                continue
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Las fotos deben enviarse como archivos multipart o URLs validas. "
                    "Se recibio un valor invalido."
                ),
            )

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pueden subir archivos vacios.",
            )
        filename = (getattr(file, "filename", None) or f"file_{index}").replace(
            " ", "_"
        )
        content_type = getattr(file, "content_type", None) or "application/octet-stream"
        path = f"{prefix}/{uuid4().hex}_{filename}"
        try:
            urls.append(StorageService.upload_file(file_bytes, path, content_type))
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
    return urls


async def _build_articulo_input(request: Request, user_id: int) -> ArticuloInput:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        return ArticuloInput(**await request.json())

    form = await request.form()
    fotos = await _upload_form_files(
        form.getlist("fotos"),
        f"articulos/{user_id}/fotos",
    )
    documentacion = await _upload_form_files(
        form.getlist("documentacionOrigen"),
        f"articulos/{user_id}/documentacion",
    )

    payload = {
        "descripcion": form.get("descripcion"),
        "historia": form.get("historia") or None,
        "artista": form.get("artista") or None,
        "fechaCreacion": form.get("fechaCreacion") or None,
        "fotos": fotos,
        "documentacionOrigen": documentacion or None,
        "esPropietario": _parse_bool(form.get("esPropietario")),
        "declaraOrigenLicito": _parse_bool(form.get("declaraOrigenLicito")),
    }
    return ArticuloInput(**payload)


@router.post("", status_code=201, response_model=Articulo)
async def create_article(
    request: Request,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    articulo = await _build_articulo_input(request, user["usuarioId"])
    return ArticuloService.crear_articulo(db, user["usuarioId"], articulo)


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


@router.post("/{id}/aceptar-tasacion", response_model=Articulo)
async def accept_valuation(
    id: int,
    body: AceptarTasacionRequest,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return ArticuloService.aceptar_tasacion(db, id, user["usuarioId"], body.acepta)


@router.post("/{id}/seguro/aumentar")
async def request_insurance_increase(
    id: int,
    body: SeguroAumentoRequest,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return ArticuloService.solicitar_aumento_seguro(
        db, id, user["usuarioId"], body.montoNuevo
    )
