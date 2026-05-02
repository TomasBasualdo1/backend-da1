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
    try:
      database_url = os.getenv("DATABASE_URL")
        # Conectamos a PostgreSQL (y le pedimos que nos devuelva diccionarios en vez de tuplas sueltas)
      conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
      return conn
    except Exception as e:
      print(f"Error conectando a Supabase: {e}")
      raise e

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
