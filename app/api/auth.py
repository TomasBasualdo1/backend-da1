from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials
from psycopg import Connection
from pydantic import BaseModel
from datetime import datetime, timezone

from app.core.security import create_access_token, decode_access_token
from app.dependencies import get_db, security, get_current_user
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.storage_service import StorageService
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.schemas import ForgotPassword, ResetPassword

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


class RegistroPaso2Request(BaseModel):
    token: str
    password: str
    paymentTipo: Optional[str] = None
    paymentDatos: Optional[str] = None
    paymentMoneda: Optional[str] = None
    paymentLimite: Optional[float] = None
    paymentPais: Optional[str] = None


# --- Endpoints ---


@router.post("/registro/paso1", status_code=201)
async def registro_paso1(
    documento: str = Form(...),
    nombre: str = Form(...),
    apellido: str = Form(...),
    email: str = Form(...),
    direccion: str = Form(...),
    numeroPais: int = Form(...),
    telefono: Optional[str] = Form(None),
    fotoFrente: UploadFile = File(...),
    fotoDorso: UploadFile = File(...),
    db: Connection = Depends(get_db),
):
    UsuarioRepository.check_duplicate(db, documento, email)

    frente_bytes = await fotoFrente.read()
    dorso_bytes = await fotoDorso.read()

    foto_frente_url = StorageService.upload_file(
        frente_bytes,
        f"dni/{documento}/frente.jpg",
        fotoFrente.content_type or "image/jpeg",
    )
    foto_dorso_url = StorageService.upload_file(
        dorso_bytes,
        f"dni/{documento}/dorso.jpg",
        fotoDorso.content_type or "image/jpeg",
    )

    persona_id = UsuarioRepository.create_cliente_pendiente(
        db=db,
        nombre_completo=f"{nombre} {apellido}",
        documento=documento,
        email=email,
        direccion=direccion,
        numeropais=numeroPais,
        telefono=telefono,
        foto_frente_url=foto_frente_url,
        foto_dorso_url=foto_dorso_url,
    )

    result = UsuarioRepository.aprobar_registro(db, persona_id)
    try:
        EmailService.send_verification_email(result["email"], result["token"])
    except Exception as e:
        print(f"Error sending verification email to {result['email']}: {e}")
        print(f"FALLBACK DEBUG: Verification token for {result['email']} is: {result['token']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Usuario registrado pero falló el envío del email de verificación: {str(e)}"
        )


@router.post("/registro/paso2", status_code=201)
async def registro_paso2(
    body: RegistroPaso2Request,
    db: Connection = Depends(get_db),
):
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT identificador FROM personas_adicionales WHERE token_email = %s",
            (body.token,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Token no encontrado")
        user_id = row["identificador"]

    UsuarioRepository.set_password_from_token(db, body.token, body.password)

    if body.paymentTipo and body.paymentDatos and body.paymentMoneda:
        ultimos_digitos = "4321"
        digits = [c for c in body.paymentDatos if c.isdigit()]
        if len(digits) >= 4:
            ultimos_digitos = "".join(digits[-4:])
        else:
            ultimos_digitos = body.paymentDatos[-4:]

        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO medios_pago (
                    cliente_id, tipo, datos_encriptados, ultimos_digitos,
                    estado_verificacion, moneda, limite_reservado, pais_banco, es_cuenta_receptora
                ) VALUES (%s, %s, %s, %s, 'pendiente', %s, %s, %s, false)
                """,
                (
                    user_id,
                    body.paymentTipo,
                    body.paymentDatos,
                    ultimos_digitos,
                    body.paymentMoneda,
                    body.paymentLimite or 0.00,
                    body.paymentPais,
                ),
            )
        db.commit()


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
async def forgot_password(
    request: ForgotPassword,
    db: Connection = Depends(get_db)
):
    try:
        token = UsuarioRepository.generate_reset_token(db, request.email)
        EmailService.send_reset_password_email(request.email, token)
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            pass
        else:
            raise e
    except Exception as e:
        print(f"Error sending reset email to {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending reset email"
        )
    return {"message": "Si el email existe, se envió un código de recuperación."}


@router.post("/reset-password")
async def reset_password(
    request: ResetPassword,
    db: Connection = Depends(get_db)
):
    plain_password = request.newPassword.get_secret_value() if hasattr(request.newPassword, 'get_secret_value') else request.newPassword
    UsuarioRepository.set_password_from_token(db, request.token, plain_password)
    return {"message": "Contraseña actualizada exitosamente."}
