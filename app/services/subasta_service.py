from datetime import date, timedelta

from fastapi import HTTPException, status
from psycopg import Connection

from app.repositories.subasta_repo import SubastaRepository
from app.schemas.schemas import CatalogoItemInput, SubastaCreate


class SubastaService:
    @staticmethod
    def get_publicas(db: Connection) -> list[dict]:
        return SubastaRepository.get_publicas(db)

    @staticmethod
    def get_publica_detalle(db: Connection, subasta_id: int, base_url: str) -> dict | None:
        return SubastaRepository.get_publica_detalle(db, subasta_id, base_url)

    @staticmethod
    def get_todas(db: Connection) -> list[dict]:
        return SubastaRepository.get_todas(db)

    @staticmethod
    def get_detalle(db: Connection, subasta_id: int, base_url: str) -> dict | None:
        return SubastaRepository.get_detalle(db, subasta_id, base_url)

    @staticmethod
    def create_subasta(
        db: Connection,
        subasta: SubastaCreate,
        usuario_id: int | None,
    ) -> dict:
        min_fecha = date.today() + timedelta(days=10)
        if subasta.fecha <= min_fecha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de la subasta debe ser posterior a 10 dias desde hoy.",
            )

        return SubastaRepository.create_subasta(db, subasta, usuario_id)

    @staticmethod
    def add_catalog_item(
        db: Connection,
        subasta_id: int,
        item: CatalogoItemInput,
        usuario_id: int | None,
    ) -> dict:
        has_producto = item.productoId is not None
        has_articulo = item.articuloId is not None
        if has_producto == has_articulo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe enviar exactamente uno de productoId o articuloId.",
            )

        if item.precioBase <= 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="precioBase debe ser mayor a 0.01.",
            )

        if item.comision <= 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="comision debe ser mayor a 0.01.",
            )

        return SubastaRepository.add_catalog_item(db, subasta_id, item, usuario_id)
