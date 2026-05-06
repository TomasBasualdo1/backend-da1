from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from psycopg import Connection
from pydantic import BaseModel
from datetime import datetime, timezone

from app.core.security import create_access_token, decode_access_token
from app.dependencies import get_db, security, get_current_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")


# --- Pydantic Models ---

class LoginRequest(BaseModel):
    documento: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str = "Successfully logged out"


# --- Endpoints ---


@router.post("/registro/paso1", status_code=201)
async def registro_paso1():
    pass


@router.post("/registro/paso2", status_code=201)
async def registro_paso2():
    pass


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Connection = Depends(get_db)):
    # Authenticate user
    user_data = AuthService.login(db, credentials.documento, credentials.password)

    # Create JWT token with required claims
    token_data = {
        "usuarioId": user_data["usuario_id"],
        "categoria": user_data["categoria"],
        "admitido": user_data["admitido"],
    }
    access_token = create_access_token(token_data)

    return TokenResponse(access_token=access_token)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    payload: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    AuthService.logout(
        db,
        jti=payload["jti"],
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    )
    db.commit()
    return LogoutResponse()

@router.post("/verify-email")
async def verify_email():
    pass


@router.post("/forgot-password")
async def forgot_password():
    pass


@router.post("/reset-password")
async def reset_password():
    pass
