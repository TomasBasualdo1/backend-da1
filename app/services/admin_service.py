from fastapi import HTTPException
from psycopg import Connection

from app.repositories.articulo_repo import ArticuloRepository
from app.schemas.schemas import ArticuloEvaluacion, CatalogoItemInput, SubastaCreate
from app.services.subasta_service import SubastaService


class AdminService:

    @staticmethod
    def verify_payment_method(db: Connection, medio_pago_id: int, estado: str) -> dict:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT cliente_id, estado_verificacion FROM medios_pago WHERE identificador = %s",
                (medio_pago_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Medio de pago no encontrado")

            if row["estado_verificacion"] != "pendiente":
                raise HTTPException(
                    status_code=400, detail="Este medio de pago ya fue verificado"
                )

            cursor.execute(
                "UPDATE medios_pago SET estado_verificacion = %s WHERE identificador = %s",
                (estado, medio_pago_id),
            )
            cursor.execute(
                "INSERT INTO notificaciones (persona_id, tipo, mensaje) VALUES (%s, 'sistema', %s)",
                (
                    row["cliente_id"],
                    f"Tu medio de pago ha sido {estado} por el administrador.",
                ),
            )

        db.commit()
        return {"message": f"Medio de pago {estado} exitosamente."}

    @staticmethod
    def evaluate_article(
        db: Connection, articulo_id: int, data: ArticuloEvaluacion
    ) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")

        if articulo["estado"] not in ["pendiente", "en_inspeccion"]:
            raise HTTPException(
                status_code=400, detail="El artículo ya fue evaluado anteriormente"
            )

        if data.estado.value == "rechazado" and not data.motivoRechazo:
            raise HTTPException(
                status_code=400, detail="Debe indicar un motivo de rechazo"
            )

        if data.estado.value == "aprobado" and (
            data.precioBasePropuesto is None or data.comisionPropuesta is None
        ):
            raise HTTPException(
                status_code=400,
                detail="Debe proponer un precio base y comisión para aprobar",
            )

        result = ArticuloRepository.evaluar_articulo(db, articulo_id, data)

        with db.cursor() as cursor:
            mensaje = f"Tu artículo #{articulo_id} fue {data.estado.value}."
            if data.estado.value == "aprobado":
                mensaje += (
                    f" Precio propuesto: ${data.precioBasePropuesto}. "
                    f"Comisión: {data.comisionPropuesta}%."
                )
            else:
                mensaje += f" Motivo: {data.motivoRechazo}"

            cursor.execute(
                "INSERT INTO notificaciones (persona_id, tipo, mensaje) VALUES (%s, 'sistema', %s)",
                (articulo["duenioId"], mensaje),
            )

        db.commit()
        return result

    @staticmethod
    def create_auction(
        db: Connection, data: SubastaCreate, usuario_id: int | None
    ) -> dict:
        return SubastaService.create_subasta(db, data, usuario_id)

    @staticmethod
    def add_catalog_item(
        db: Connection,
        subasta_id: int,
        data: CatalogoItemInput,
        usuario_id: int | None,
    ) -> dict:
        return SubastaService.add_catalog_item(db, subasta_id, data, usuario_id)
