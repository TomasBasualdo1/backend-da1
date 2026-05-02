import os
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from fastapi import FastAPI, HTTPException
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@contextmanager
def get_db_connection():
    conn = None
    try:
        database_url = os.getenv("DATABASE_URL")
        # Conectamos a PostgreSQL
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        
        # En lugar de return, usamos yield para que funcione el 'with'
        yield conn
        
    except Exception as e:
        print(f"Error conectando a Supabase: {e}")
        raise e
    finally:
        # Esto asegura que la conexión se cierre siempre, pase lo que pase
        if conn is not None:
            conn.close()

@app.get("/paises")
def get_paises():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Seleccionamos columnas del esquema del profesor
        cursor.execute("SELECT numero, nombre, capital FROM paises")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return results

@app.get("/")
def read_root():
    return {"message": "Hello, Snickers!"}
