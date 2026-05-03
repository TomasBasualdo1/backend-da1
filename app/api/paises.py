from fastapi import APIRouter, Depends
from psycopg import Connection

from app.dependencies import get_db

router = APIRouter()


@router.get("/paises")
async def get_paises(db: Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT numero, nombre, capital FROM paises")
    results = [dict(row) for row in cursor.fetchall()]
    return results
