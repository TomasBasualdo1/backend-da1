import os
import pyodbc
from fastapi import FastAPI, HTTPException
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configuración de la cadena de conexión
connection_string = (
    f"DRIVER={os.getenv('DB_DRIVER')};"
    f"SERVER={os.getenv('DB_SERVER')};"
    f"DATABASE={os.getenv('DB_NAME')};"
    f"UID={os.getenv('DB_USER')};"
    f"PWD={os.getenv('DB_PASSWORD')};"
    "Encrypt=yes;"
    "TrustServerCertificate=Yes;"
    "Login Timeout=60;"
    "Connection Timeout=60;"
)

@contextmanager
def get_db_connection():
    conn = pyodbc.connect(connection_string)
    try:
        yield conn
    finally:
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
