from psycopg import Connection
from app.repositories.subasta_repo import SubastaRepository

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
