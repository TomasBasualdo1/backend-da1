import httpx
from app.config import settings


class StorageService:
    BUCKET = "documentos"

    @staticmethod
    def upload_file(file_bytes: bytes, path: str, content_type: str = "image/jpeg") -> str:
        upload_url = f"{settings.supabase_url}/storage/v1/object/{StorageService.BUCKET}/{path}"
        headers = {
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": content_type,
        }
        response = httpx.put(upload_url, content=file_bytes, headers=headers)
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Storage upload failed ({response.status_code}): {response.text}")

        return f"{settings.supabase_url}/storage/v1/object/public/{StorageService.BUCKET}/{path}"
