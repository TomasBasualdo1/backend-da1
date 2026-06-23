from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from app.dependencies import get_current_user, get_db, require_admin
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.schemas import (
    Articulo,
    ArticuloEvaluacion,
    AutoCategoryResult,
    CatalogoItemInput,
    MedioPagoVerificacion,
    SubastaCreate,
    Usuario,
    UsuarioVerificacion,
    UpdateCategoriaRequest,
)
from app.services.admin_service import AdminService
from app.services.category_service import CategoryService
from app.services.email_service import EmailService
from app.services.subasta_service import SubastaService
from app.services.streamer import SubastaStreamer

router = APIRouter(prefix="/admin")


def _require_admin(user: dict) -> None:
    require_admin(user)


@router.post("/usuarios/{id}/verificar")
async def verify_user(
    id: int,
    body: UsuarioVerificacion,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    if body.admitido:
        if body.categoria is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe indicar una categoría para aprobar el usuario.",
            )

        categoria_str = body.categoria.value
        result = UsuarioRepository.aprobar_registro(db, id, categoria_str)
        try:
            EmailService.send_verification_email(result["email"], result["token"])
        except Exception as e:
            print(f"Error sending verification email: {e}")
        return {"message": "Usuario aprobado. Se envió el email de verificación."}

    if not body.motivoRechazo or not body.motivoRechazo.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe indicar un motivo de rechazo.",
        )

    result = UsuarioRepository.rechazar_registro(db, id, body.motivoRechazo)
    try:
        EmailService.send_rejection_email(
            result["email"], body.motivoRechazo
        )
    except Exception as e:
        print(f"Error sending rejection email: {e}")
    return {"message": "Usuario rechazado. Se envió la notificación de rechazo."}


@router.post("/medios-pago/{id}/verificar")
async def verify_payment_method(
    id: int,
    body: MedioPagoVerificacion,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.verify_payment_method(db, id, body.estadoVerificacion.value)


@router.post("/pagos/procesar-vencimientos")
async def process_overdue_payments(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return SubastaService.procesar_vencimientos(db)


@router.post("/articulos/{id}/evaluar", response_model=Articulo)
async def evaluate_article(
    id: int,
    body: ArticuloEvaluacion,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.evaluate_article(db, id, body)


@router.post("/subastas", status_code=201)
async def create_auction(
    body: SubastaCreate,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.create_auction(db, body, user.get("usuarioId"))


@router.post("/subastas/{id}/catalogo/items", status_code=201)
async def add_catalog_item(
    id: int,
    body: CatalogoItemInput,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.add_catalog_item(db, id, body, user.get("usuarioId"))


@router.post("/subastas/{id}/items/{item_id}/abrir")
async def open_catalog_item(
    id: int,
    item_id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    from datetime import datetime, timezone, timedelta
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT duracion_item_minutos FROM subastas WHERE identificador = %s",
            (id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Subasta no encontrada.")
        duracion = row["duracion_item_minutos"]

    fecha_fin = datetime.now(timezone.utc) + timedelta(minutes=duracion)
    await SubastaStreamer.broadcast(id, "item", {
        "itemId": item_id,
        "fechaFinItem": fecha_fin.isoformat(),
    })
    return {"itemId": item_id, "fechaFinItem": fecha_fin.isoformat()}


@router.get("/usuarios/pendientes", response_model=list[Usuario])
async def get_pending_users(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.get_pending_users(db)


@router.get("/usuarios", response_model=list[Usuario])
async def get_all_users(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.get_all_users(db)


@router.patch("/usuarios/{id}/categoria")
async def update_user_category(
    id: int,
    body: UpdateCategoriaRequest,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.update_user_category(db, id, body.categoria.value)


@router.post("/usuarios/{id}/recalcular-categoria", response_model=AutoCategoryResult)
async def recalculate_user_category(
    id: int,
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return CategoryService.evaluate_and_upgrade(db, id)


@router.get("/articulos/pendientes")
async def get_pending_articles(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.get_pending_articles(db)


@router.get("/medios-pago/pendientes")
async def get_pending_payment_methods(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.get_pending_payment_methods(db)


@router.get("/subastadores")
async def get_subastadores(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.get_all_subastadores(db)


@router.get("/articulos/aprobados-no-catalogados")
async def get_approved_non_cataloged_articles(
    db: Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    return AdminService.get_approved_non_cataloged_articles(db)
