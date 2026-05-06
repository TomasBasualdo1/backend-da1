from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from psycopg import Connection

from app.core.database import get_db_connection
from app.core.security import decode_access_token

security = HTTPBearer()


def get_db():
    with get_db_connection() as conn:
        yield conn


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db:Connection = Depends(get_db)) -> dict:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )
    from app.services.auth_service import AuthService
    if AuthService.is_token_blacklisted(db, payload.get("jti")):
      raise HTTPException(
        status_code=401,
        detail="Token revoked",
    )
    return payload
