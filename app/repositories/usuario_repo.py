import random

from fastapi import HTTPException, status
from psycopg import Connection

from app.core.security import get_password_hash


class UsuarioRepository:
    DEFAULT_VERIFICADOR_ID = 1

    @staticmethod
    def check_duplicate(db: Connection, documento: str, email: str) -> None:
        with db.cursor() as cursor:
            cursor.execute("SELECT 1 FROM personas WHERE documento = %s", (documento,))
            if cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Documento ya registrado")
            cursor.execute("SELECT 1 FROM personas_adicionales WHERE email = %s", (email,))
            if cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ya registrado")

    @staticmethod
    def create_cliente_pendiente(
        db: Connection,
        nombre_completo: str,
        documento: str,
        email: str,
        direccion: str,
        numeropais: int,
        telefono: str | None,
        foto_frente_url: str,
        foto_dorso_url: str,
    ) -> int:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO personas (documento, nombre, direccion, estado)
                VALUES (%s, %s, %s, 'activo')
                RETURNING identificador
                """,
                (documento, nombre_completo, direccion),
            )
            persona_id = cursor.fetchone()["identificador"]

            cursor.execute(
                """
                INSERT INTO personas_adicionales (identificador, email, foto_frente, foto_dorso, telefono)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (persona_id, email, foto_frente_url, foto_dorso_url, telefono),
            )

            cursor.execute(
                """
                INSERT INTO clientes (identificador, numeropais, admitido, categoria, verificador)
                VALUES (%s, %s, 'no', 'comun', %s)
                """,
                (persona_id, numeropais, UsuarioRepository.DEFAULT_VERIFICADOR_ID),
            )

            cursor.execute(
                """
                INSERT INTO clientes_adicionales (identificador, estado_registro)
                VALUES (%s, 'pendiente')
                """,
                (persona_id,),
            )

        db.commit()
        return persona_id

    @staticmethod
    def aprobar_registro(db: Connection, usuario_id: int, categoria: str | None = None) -> dict:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT email FROM personas_adicionales WHERE identificador = %s",
                (usuario_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

            token = str(random.randint(100000, 999999))

            if categoria:
                cursor.execute(
                    "UPDATE clientes SET admitido = 'si', categoria = %s WHERE identificador = %s",
                    (categoria, usuario_id),
                )
            else:
                cursor.execute(
                    "UPDATE clientes SET admitido = 'si' WHERE identificador = %s",
                    (usuario_id,),
                )
            cursor.execute(
                """
                UPDATE clientes_adicionales
                SET estado_registro = 'aprobado', motivo_rechazo = NULL
                WHERE identificador = %s
                """,
                (usuario_id,),
            )
            cursor.execute(
                "UPDATE personas_adicionales SET token_email = %s WHERE identificador = %s",
                (token, usuario_id),
            )
        db.commit()
        return {"token": token, "email": row["email"]}

    @staticmethod
    def rechazar_registro(db: Connection, usuario_id: int, motivo_rechazo: str | None = None) -> dict:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT email FROM personas_adicionales WHERE identificador = %s",
                (usuario_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

            cursor.execute(
                "UPDATE clientes SET admitido = 'no' WHERE identificador = %s",
                (usuario_id,),
            )
            cursor.execute(
                """
                UPDATE clientes_adicionales 
                SET estado_registro = 'rechazado', motivo_rechazo = %s
                WHERE identificador = %s
                """,
                (motivo_rechazo, usuario_id),
            )
            cursor.execute(
                "UPDATE personas_adicionales SET token_email = NULL WHERE identificador = %s",
                (usuario_id,),
            )
        db.commit()
        return {"email": row["email"]}

    @staticmethod
    def set_password_from_token(db: Connection, token: str, password: str) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT identificador FROM personas_adicionales WHERE token_email = %s",
                (token,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token no encontrado")

            cursor.execute(
                "UPDATE personas_adicionales SET password_hash = %s, token_email = NULL WHERE identificador = %s",
                (get_password_hash(password), row["identificador"]),
            )
        db.commit()

    @staticmethod
    def generate_reset_token(db: Connection, email: str) -> str:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT identificador FROM personas_adicionales WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

            token = str(random.randint(100000, 999999))
            cursor.execute(
                "UPDATE personas_adicionales SET token_email = %s WHERE identificador = %s",
                (token, row["identificador"]),
            )
        db.commit()
        return token
