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

    @staticmethod
    def get_pending_registrations(db: Connection) -> list[dict]:
        query = """
            SELECT 
                p.identificador as id,
                p.documento,
                p.nombre,
                pa.email,
                p.direccion,
                pa.telefono,
                pa.foto_url as foto,
                pa.foto_frente as "fotoFrente",
                pa.foto_dorso as "fotoDorso",
                c.numeropais as "numeroPais",
                c.admitido,
                ca.estado_registro as "estadoRegistro",
                c.categoria,
                COALESCE(ca.multa_activa, false) as "multaActiva",
                COALESCE(ca.bloqueado, false) as bloqueado
            FROM personas p
            LEFT JOIN personas_adicionales pa ON p.identificador = pa.identificador
            JOIN clientes c ON p.identificador = c.identificador
            LEFT JOIN clientes_adicionales ca ON c.identificador = ca.identificador
            WHERE ca.estado_registro = 'pendiente'
            ORDER BY p.identificador ASC
        """
        with db.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            results = []
            for row in rows:
                user = dict(row)
                nombre_completo = user["nombre"] or ""
                name_parts = nombre_completo.split(" ", 1)
                if len(name_parts) == 2:
                    user["nombre"] = name_parts[0]
                    user["apellido"] = name_parts[1]
                else:
                    user["apellido"] = ""
                results.append(user)
            return results

    @staticmethod
    def get_all_users(db: Connection) -> list[dict]:
        query = """
            SELECT 
                p.identificador as id,
                p.documento,
                p.nombre,
                pa.email,
                p.direccion,
                pa.telefono,
                pa.foto_url as foto,
                pa.foto_frente as "fotoFrente",
                pa.foto_dorso as "fotoDorso",
                c.numeropais as "numeroPais",
                c.admitido,
                ca.estado_registro as "estadoRegistro",
                c.categoria,
                COALESCE(ca.multa_activa, false) as "multaActiva",
                COALESCE(ca.bloqueado, false) as bloqueado
            FROM personas p
            LEFT JOIN personas_adicionales pa ON p.identificador = pa.identificador
            JOIN clientes c ON p.identificador = c.identificador
            LEFT JOIN clientes_adicionales ca ON c.identificador = ca.identificador
            ORDER BY p.nombre ASC
        """
        with db.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            results = []
            for row in rows:
                user = dict(row)
                nombre_completo = user["nombre"] or ""
                name_parts = nombre_completo.split(" ", 1)
                if len(name_parts) == 2:
                    user["nombre"] = name_parts[0]
                    user["apellido"] = name_parts[1]
                else:
                    user["apellido"] = ""
                results.append(user)
            return results

    @staticmethod
    def update_user_category(db: Connection, usuario_id: int, categoria: str) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM clientes WHERE identificador = %s",
                (usuario_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
            
            cursor.execute(
                "UPDATE clientes SET categoria = %s WHERE identificador = %s",
                (categoria, usuario_id),
            )
        db.commit()

    @staticmethod
    def get_multas(db: Connection, usuario_id: int) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    identificador AS id,
                    importe,
                    estado,
                    fecha_limite AS "fechaLimite",
                    motivo
                FROM multas
                WHERE cliente_id = %s
                ORDER BY
                    CASE estado WHEN 'pendiente' THEN 0 ELSE 1 END,
                    fecha_limite ASC,
                    identificador DESC
                """,
                (usuario_id,),
            )
            rows = cursor.fetchall()
            for row in rows:
                if row["importe"] is not None:
                    row["importe"] = float(row["importe"])
            return rows

    @staticmethod
    def get_multa_para_cliente(
        db: Connection, usuario_id: int, multa_id: int
    ) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    identificador AS id,
                    cliente_id,
                    importe,
                    estado,
                    fecha_limite AS "fechaLimite",
                    motivo
                FROM multas
                WHERE identificador = %s AND cliente_id = %s
                """,
                (multa_id, usuario_id),
            )
            row = cursor.fetchone()
            if row and row["importe"] is not None:
                row["importe"] = float(row["importe"])
            return row

    @staticmethod
    def get_medio_pago_para_cliente(
        db: Connection, usuario_id: int, medio_pago_id: int
    ) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    identificador AS id,
                    cliente_id,
                    estado_verificacion,
                    moneda,
                    limite_reservado
                FROM medios_pago
                WHERE identificador = %s AND cliente_id = %s
                """,
                (medio_pago_id, usuario_id),
            )
            row = cursor.fetchone()
            if row and row["limite_reservado"] is not None:
                row["limite_reservado"] = float(row["limite_reservado"])
            return row

    @staticmethod
    def pagar_multa(db: Connection, multa_id: int, medio_pago_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE multas
                SET estado = 'pagada', medio_pago_id = %s
                WHERE identificador = %s AND estado = 'pendiente'
                """,
                (medio_pago_id, multa_id),
            )

    @staticmethod
    def tiene_multas_pendientes(db: Connection, usuario_id: int) -> bool:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM multas WHERE cliente_id = %s AND estado = 'pendiente'",
                (usuario_id,),
            )
            return bool(cursor.fetchone())

    @staticmethod
    def set_multa_activa(db: Connection, usuario_id: int, activa: bool) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE clientes_adicionales SET multa_activa = %s WHERE identificador = %s",
                (activa, usuario_id),
            )

    @staticmethod
    def crear_notificacion(
        db: Connection, usuario_id: int, tipo: str, mensaje: str
    ) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO notificaciones (persona_id, tipo, mensaje) VALUES (%s, %s, %s)",
                (usuario_id, tipo, mensaje),
            )
