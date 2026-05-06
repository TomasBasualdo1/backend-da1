from datetime import datetime
from fastapi import HTTPException, status
from psycopg import Connection

from app.core.security import verify_password


class AuthService:
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
                p.password_hash,
                c.admitido,
                c.categoria,
                c."estadoRegistro",
                c.bloqueado,
                c."multaActiva"
            FROM personas p
            JOIN clientes c ON p.identificador = c.identificador
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