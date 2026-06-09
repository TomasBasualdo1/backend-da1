import time
import uuid
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel
from psycopg import Connection

from app.config import settings
from app.dependencies import get_db

router = APIRouter(prefix="/uploads")


class PresignRequest(BaseModel):
    filename: str
    bucket: str | None = "imagenes"
    content_type: str | None = None
    expires_in: int | None = None


@router.post("/presign")
async def presign_upload(payload: PresignRequest):
    supabase_url = settings.supabase_url
    supabase_key = settings.supabase_service_role_key

    safe_filename = payload.filename.replace(" ", "_")
    path = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{safe_filename}"
    encoded_path = quote(path, safe="/")
    bucket = payload.bucket or "imagenes"

    sign_endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/upload/sign/{bucket}/{encoded_path}"
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
    }

    body = {"expiresIn": payload.expires_in} if payload.expires_in else None

    async with httpx.AsyncClient() as client:
        resp = await client.post(sign_endpoint, headers=headers, json=body, timeout=10)

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Error creating presigned url: {resp.status_code} {resp.text}",
        )

    data = resp.json()
    returned_url = data.get("url") or data.get("signedURL") or ""
    token = data.get("token")

    if returned_url.startswith("http"):
        full_upload_url = returned_url
    else:
        base = supabase_url.rstrip("/")
        if returned_url.startswith("/storage"):
            full_upload_url = f"{base}{returned_url}"
        elif returned_url.startswith("/"):
            full_upload_url = f"{base}/storage/v1{returned_url}"
        else:
            full_upload_url = f"{base}/storage/v1/{returned_url}"

    public_url = f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket}/{encoded_path}"

    return {
        "upload_url": full_upload_url,
        "token": token,
        "public_url": public_url,
        "path": path,
    }


@router.get("/fotos/{id}")
async def get_foto(id: int, db: Connection = Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("SELECT foto FROM fotos WHERE identificador = %s", (id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Foto no encontrada")
        return Response(content=row["foto"], media_type="image/png")
