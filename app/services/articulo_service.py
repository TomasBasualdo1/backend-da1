from fastapi import HTTPException
from psycopg import Connection

from app.repositories.articulo_repo import ArticuloRepository
from app.schemas.schemas import ArticuloInput, ConfirmacionEnvioRequest


class ArticuloService:

    @staticmethod
    def crear_articulo(db: Connection, usuario_id: int, data: ArticuloInput) -> dict:
        if len(data.fotos) < 6:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar al menos 6 fotos del artículo",
            )
        if not data.esPropietario:
            raise HTTPException(
                status_code=400,
                detail="Debe declarar que es propietario del artículo",
            )
        if not data.declaraOrigenLicito:
            raise HTTPException(
                status_code=400,
                detail="Debe declarar el origen lícito del artículo",
            )

        duenio_id = ArticuloRepository.ensure_duenio(db, usuario_id)
        return ArticuloRepository.create_articulo(db, duenio_id, data)

    @staticmethod
    def get_mis_articulos(db: Connection, usuario_id: int) -> list[dict]:
        duenio_id = ArticuloRepository.ensure_duenio(db, usuario_id)
        return ArticuloRepository.list_articulos_by_owner(db, duenio_id)

    @staticmethod
    def get_articulo_detalle(db: Connection, articulo_id: int, usuario_id: int) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
        if usuario_id != 1 and articulo.get("duenioId") != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver este artículo",
            )
        return articulo

    @staticmethod
    def aceptar_tasacion(
        db: Connection, articulo_id: int, usuario_id: int, acepta: bool
    ) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
        if articulo.get("duenioId") != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para este artículo",
            )
        if acepta and articulo["estado"] != "aprobado":
            raise HTTPException(
                status_code=400,
                detail="El artículo no está aprobado por tasación aún",
            )

        result = ArticuloRepository.aceptar_tasacion(db, articulo_id, acepta)

        if not acepta:
            cargo = result.get("costoDevolucion")
            mensaje = (
                f"Rechazaste la tasación del artículo #{articulo_id}. "
                f"El bien será devuelto con cargo a vos."
            )
            if cargo is not None:
                mensaje += f" Cargo de devolución: ${cargo}."
            with db.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO notificaciones (persona_id, tipo, mensaje) "
                    "VALUES (%s, 'sistema', %s)",
                    (articulo["duenioId"], mensaje),
                )
            db.commit()

        return result

    @staticmethod
    def confirmar_envio(
        db: Connection, articulo_id: int, usuario_id: int, data: ConfirmacionEnvioRequest
    ) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
        if articulo.get("duenioId") != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para este artículo",
            )
        if articulo["estado"] != "interesado":
            raise HTTPException(
                status_code=400,
                detail="El artículo no está esperando confirmación de envío",
            )

        result = ArticuloRepository.confirmar_envio(db, articulo_id, data)

        if not data.aceptaCargoDevolucion:
            mensaje = (
                f"Declinaste el envío del artículo #{articulo_id}. "
                f"El proceso de consignación finalizó."
            )
            with db.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO notificaciones (persona_id, tipo, mensaje) "
                    "VALUES (%s, 'sistema', %s)",
                    (articulo["duenioId"], mensaje),
                )
            db.commit()

        return result

    @staticmethod
    def solicitar_aumento_seguro(
        db: Connection, articulo_id: int, usuario_id: int, monto_nuevo: float
    ) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
        if articulo.get("duenioId") != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para este artículo",
            )

        seguro = articulo.get("seguro")
        if not seguro or not seguro.get("poliza"):
            raise HTTPException(
                status_code=400,
                detail="El artículo no tiene una póliza de seguro asignada todavía",
            )

        if monto_nuevo <= (seguro.get("montoAsegurado") or 0.0):
            raise HTTPException(
                status_code=400,
                detail="El nuevo monto debe ser mayor al monto actual",
            )

        ArticuloRepository.aumentar_seguro(db, articulo_id, monto_nuevo)
        db.commit()
        return {
            "message": "Solicitud de aumento de seguro procesada. Se le contactará para cobrar la diferencia del premio."
        }
