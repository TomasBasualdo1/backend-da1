from fastapi import HTTPException
from psycopg import Connection
from app.repositories.articulo_repo import ArticuloRepository
from app.schemas.schemas import ArticuloInput


class ArticuloService:

    @staticmethod
    def crear_articulo(db: Connection, duenio_id: int, data: ArticuloInput) -> dict:
        if len(data.fotos) < 6:
            raise HTTPException(status_code=400, detail="Debe proporcionar al menos 6 fotos del artículo")
        if not data.esPropietario:
            raise HTTPException(status_code=400, detail="Debe declarar que es propietario del artículo")
        if not data.declaraOrigenLicito:
            raise HTTPException(status_code=400, detail="Debe declarar el origen lícito del artículo")

        fotos_str = [str(url) for url in data.fotos]
        docs_str = [str(url) for url in data.documentacionOrigen] if data.documentacionOrigen else None

        articulo_id = ArticuloRepository.crear_articulo(
            db=db,
            duenio_id=duenio_id,
            descripcion=data.descripcion,
            historia=data.historia,
            artista=data.artista,
            fecha_creacion=data.fechaCreacion.isoformat() if data.fechaCreacion else None,
            es_propietario=data.esPropietario,
            declara_origen_licito=data.declaraOrigenLicito,
            fotos=fotos_str,
            documentacion=docs_str,
        )
        db.commit()
        return {"id": articulo_id, "message": "Artículo consignado exitosamente, pendiente de evaluación."}

    @staticmethod
    def get_mis_articulos(db: Connection, duenio_id: int) -> list[dict]:
        return ArticuloRepository.get_articulos_por_duenio(db, duenio_id)

    @staticmethod
    def get_articulo_detalle(db: Connection, articulo_id: int, duenio_id: int) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
        if articulo["duenio_id"] != duenio_id:
            raise HTTPException(status_code=403, detail="No tienes permisos para ver este artículo")
        return articulo

    @staticmethod
    def aceptar_tasacion(db: Connection, articulo_id: int, duenio_id: int) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
        if articulo["duenio_id"] != duenio_id:
            raise HTTPException(status_code=403, detail="No tienes permisos para este artículo")
        if articulo["estado"] != "aprobado":
            raise HTTPException(status_code=400, detail="El artículo no está aprobado por tasación aún")

        ArticuloRepository.aceptar_tasacion(db, articulo_id)
        db.commit()
        return {"message": "Tasación y condiciones aceptadas exitosamente"}

    @staticmethod
    def solicitar_aumento_seguro(db: Connection, articulo_id: int, duenio_id: int, monto_nuevo: float) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
        if articulo["duenio_id"] != duenio_id:
            raise HTTPException(status_code=403, detail="No tienes permisos para este artículo")
        
        seguro = articulo.get("seguro")
        if not seguro or not seguro.get("poliza"):
            raise HTTPException(status_code=400, detail="El artículo no tiene una póliza de seguro asignada todavía")

        if monto_nuevo <= (seguro.get("montoAsegurado") or 0.0):
            raise HTTPException(status_code=400, detail="El nuevo monto debe ser mayor al monto actual")

        ArticuloRepository.aumentar_seguro(db, articulo_id, monto_nuevo)
        db.commit()
        return {"message": "Solicitud de aumento de seguro procesada. Se le contactará para cobrar la diferencia del premio."}
