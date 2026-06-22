from datetime import datetime
from fastapi import HTTPException, status
from psycopg import Connection

from app.core.security import verify_password
from app.repositories.usuario_repo import UsuarioRepository


class AuthService:
    @staticmethod
    def _extract_last_digits(payment_data: str) -> str:
        ultimos_digitos = "4321"
        if payment_data:
            digits = [c for c in payment_data if c.isdigit()]
            if len(digits) >= 4:
                ultimos_digitos = "".join(digits[-4:])
            else:
                ultimos_digitos = payment_data[-4:]
        return ultimos_digitos

    @staticmethod
    def complete_registration_step2(
        db: Connection,
        token: str,
        password: str,
        payment_tipo: str | None = None,
        payment_datos: str | None = None,
        payment_moneda: str | None = None,
        payment_limite: float | None = None,
        payment_pais: str | None = None,
    ) -> None:
        user_id = UsuarioRepository.get_user_id_by_token(db, token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token no encontrado",
            )

        UsuarioRepository.set_password_from_token(db, token, password)

        if payment_tipo and payment_datos and payment_moneda:
            UsuarioRepository.create_payment_method(
                db,
                usuario_id=user_id,
                tipo=payment_tipo,
                datos_encriptados=payment_datos,
                ultimos_digitos=AuthService._extract_last_digits(payment_datos),
                moneda=payment_moneda,
                limite_reservado=payment_limite or 0.00,
                pais_banco=payment_pais,
                es_cuenta_receptora=False,
            )
            db.commit()

    @staticmethod
    def login(db: Connection, documento: str, password: str) -> dict:
        """
        Authenticate user with documento and password.
        Returns user data dict or raises HTTPException.
        """
        # Join personas and clientes tables
        query = """
            SELECT 
                p.identificador as usuario_id,
                p.documento,
                p.nombre,
                pa.password_hash,
                c.admitido,
                c.categoria,
                ca.estado_registro as "estadoRegistro",
                ca.bloqueado,
                ca.multa_activa as "multaActiva"
            FROM personas p
            LEFT JOIN personas_adicionales pa ON p.identificador = pa.identificador
            JOIN clientes c ON p.identificador = c.identificador
            LEFT JOIN clientes_adicionales ca ON c.identificador = ca.identificador
            WHERE p.documento = %s
        """

        with db.cursor() as cursor:
            cursor.execute(query, (documento,))
            user = cursor.fetchone()

        # Check if user exists
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Verify password using password_hash column
        if not user.get("password_hash"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not verify_password(password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Check if user is blocked
        if user.get("bloqueado"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is blocked",
            )

        # Check if registration is approved
        if user.get("estadoRegistro") != "aprobado":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User registration not approved",
            )

        # Check if user is admitted
        if user.get("admitido") != "si":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not admitted",
            )

        return {
            "usuario_id": user["usuario_id"],
            "categoria": user["categoria"],
            "admitido": user["admitido"],
        }
      
    @staticmethod
    def logout(db:Connection, jti: str, expires_at:datetime):
      query = "INSERT INTO blacklisted_tokens (jti, expires_at) VALUES (%s, %s) ON CONFLICT (jti) DO NOTHING"
      with db.cursor() as cursor:
        cursor.execute(query, (jti, expires_at))
      
    @staticmethod
    def is_token_blacklisted(db: Connection, jti: str) -> bool:
      query = "SELECT 1 FROM blacklisted_tokens WHERE jti = %s"
      with db.cursor() as cursor:
        cursor.execute(query, (jti,))
        return cursor.fetchone() is not None
