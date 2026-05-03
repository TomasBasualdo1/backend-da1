import os
from contextlib import contextmanager
from dotenv import load_dotenv
from typing import Optional

import httpx
from urllib.parse import quote
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg
from psycopg.rows import dict_row

load_dotenv()

app = FastAPI()

# Allow CORS for testing (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PresignRequest(BaseModel):
    filename: str
    bucket: Optional[str] = "imagenes"
    content_type: Optional[str] = None
    expires_in: Optional[int] = None

@contextmanager
def get_db_connection():
    conn = None
    try:
        database_url = os.getenv("DATABASE_URL")
        # Conectamos a PostgreSQL
        conn = psycopg.connect(database_url, row_factory=dict_row)
        
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
        cursor.execute("SELECT numero, nombre, capital FROM paises")
      
        results = [dict(row) for row in cursor.fetchall()]
        return results

@app.get("/")
def read_root():
    return {"message": "Hello, Snickers!"}


@app.post("/uploads/presign")
async def presign_upload(payload: PresignRequest):
    """Genera una URL firmada para subir directamente a Supabase Storage.

    Request JSON: { "filename": "name.jpg", "bucket": "avatars" }
    Response: { upload_url, token, public_url, path }
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    missing_vars = []
    if not supabase_url:
        missing_vars.append("SUPABASE_URL")
    if not supabase_key:
        missing_vars.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing_vars:
        raise HTTPException(
            status_code=500,
            detail=f"Missing required environment variables: {', '.join(missing_vars)}. Add them to backend-da1/.env before using /uploads/presign.",
        )

    # Build a unique path to avoid collisions
    import time
    import uuid

    safe_filename = payload.filename.replace(' ', '_')
    path = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{safe_filename}"
    encoded_path = quote(path, safe='/')
    bucket = payload.bucket or 'imagenes'

    sign_endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/upload/sign/{bucket}/{encoded_path}"
    headers = {
        "Authorization": f"Bearer {supabase_key}",
      "apikey": supabase_key}

    body = None
    if payload.expires_in:
        body = {"expiresIn": payload.expires_in}

    async with httpx.AsyncClient() as client:
        resp = await client.post(sign_endpoint, headers=headers, json=body, timeout=10)

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Error creating presigned url: {resp.status_code} {resp.text}")

    data = resp.json()
    returned_url = data.get('url') or data.get('signedURL') or ''
    token = data.get('token')

    # Construct the full upload URL the client should PUT to
    if returned_url.startswith('http'):
        full_upload_url = returned_url
    else:
        base = supabase_url.rstrip('/')
        if returned_url.startswith('/storage'):
            full_upload_url = f"{base}{returned_url}"
        elif returned_url.startswith('/'):
            full_upload_url = f"{base}/storage/v1{returned_url}"
        else:
            full_upload_url = f"{base}/storage/v1/{returned_url}"

    public_url = f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket}/{encoded_path}"

    return {"upload_url": full_upload_url, "token": token, "public_url": public_url, "path": path}
