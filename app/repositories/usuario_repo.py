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
    def get_user_id_by_token(db: Connection, token: str) -> int | None:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT identificador FROM personas_adicionales WHERE token_email = %s",
                (token,),
            )
            row = cursor.fetchone()
            return row["identificador"] if row else None

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
                COALESCE(ca.bloqueado, false) as bloqueado,
                (SELECT COUNT(DISTINCT mp.tipo) FROM medios_pago mp WHERE mp.cliente_id = p.identificador AND mp.estado_verificacion = 'validado') as "validatedPaymentDiversity"
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
    def get_user_category(db: Connection, usuario_id: int) -> str | None:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT categoria FROM clientes WHERE identificador = %s",
                (usuario_id,),
            )
            row = cursor.fetchone()
            return row["categoria"] if row else None

    @staticmethod
    def get_validated_payment_diversity(db: Connection, usuario_id: int) -> int:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(DISTINCT tipo) as diversity
                FROM medios_pago
                WHERE cliente_id = %s AND estado_verificacion = 'validado'
                """,
                (usuario_id,),
            )
            row = cursor.fetchone()
            return row["diversity"] if row else 0

    @staticmethod
    def get_person_for_profile_update(db: Connection, usuario_id: int) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT nombre, documento FROM personas WHERE identificador = %s",
                (usuario_id,),
            )
            return cursor.fetchone()

    @staticmethod
    def update_profile_person(
        db: Connection,
        usuario_id: int,
        nombre_completo: str | None = None,
        direccion: str | None = None,
    ) -> None:
        with db.cursor() as cursor:
            if nombre_completo:
                cursor.execute(
                    "UPDATE personas SET nombre = %s WHERE identificador = %s",
                    (nombre_completo, usuario_id),
                )
            if direccion is not None:
                cursor.execute(
                    "UPDATE personas SET direccion = %s WHERE identificador = %s",
                    (direccion, usuario_id),
                )

    @staticmethod
    def update_profile_additional(
        db: Connection,
        usuario_id: int,
        telefono: str | None = None,
        foto_url: str | None = None,
    ) -> None:
        with db.cursor() as cursor:
            if telefono is not None:
                cursor.execute(
                    "UPDATE personas_adicionales SET telefono = %s WHERE identificador = %s",
                    (telefono, usuario_id),
                )
            if foto_url is not None:
                cursor.execute(
                    "UPDATE personas_adicionales SET foto_url = %s WHERE identificador = %s",
                    (foto_url, usuario_id),
                )

    @staticmethod
    def clear_profile_picture(db: Connection, usuario_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE personas_adicionales SET foto_url = NULL WHERE identificador = %s",
                (usuario_id,),
            )

    @staticmethod
    def list_payment_methods(db: Connection, usuario_id: int) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    identificador as id,
                    tipo,
                    ultimos_digitos,
                    estado_verificacion as "estadoVerificacion",
                    moneda,
                    limite_reservado as "limiteReservado",
                    pais_banco as "paisBanco",
                    es_cuenta_receptora as "esCuentaReceptora"
                FROM medios_pago
                WHERE cliente_id = %s
                """,
                (usuario_id,),
            )
            rows = cursor.fetchall()
            for row in rows:
                row["limiteReservado"] = float(row["limiteReservado"] or 0)
                row["esCuentaReceptora"] = bool(row["esCuentaReceptora"])
            return rows

    @staticmethod
    def create_payment_method(
        db: Connection,
        usuario_id: int,
        tipo: str,
        datos_encriptados: str,
        ultimos_digitos: str,
        moneda: str,
        limite_reservado: float,
        pais_banco: str | None,
        es_cuenta_receptora: bool,
    ) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO medios_pago (
                    cliente_id, tipo, datos_encriptados, ultimos_digitos,
                    estado_verificacion, moneda, limite_reservado, pais_banco, es_cuenta_receptora
                ) VALUES (%s, %s, %s, %s, 'pendiente', %s, %s, %s, %s)
                """,
                (
                    usuario_id,
                    tipo,
                    datos_encriptados,
                    ultimos_digitos,
                    moneda,
                    limite_reservado,
                    pais_banco,
                    es_cuenta_receptora,
                ),
            )

    @staticmethod
    def payment_method_belongs_to_user(
        db: Connection, usuario_id: int, payment_method_id: int
    ) -> bool:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM medios_pago WHERE identificador = %s AND cliente_id = %s",
                (payment_method_id, usuario_id),
            )
            return bool(cursor.fetchone())

    @staticmethod
    def update_payment_method(
        db: Connection, payment_method_id: int, fields: dict[str, object]
    ) -> None:
        allowed_fields = {
            "limite_reservado": "limite_reservado",
            "es_cuenta_receptora": "es_cuenta_receptora",
        }
        updates = []
        params = []
        for field, value in fields.items():
            column = allowed_fields[field]
            updates.append(f"{column} = %s")
            params.append(value)

        params.append(payment_method_id)
        with db.cursor() as cursor:
            cursor.execute(
                f"UPDATE medios_pago SET {', '.join(updates)} WHERE identificador = %s",
                tuple(params),
            )

    @staticmethod
    def delete_payment_method(db: Connection, payment_method_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM medios_pago WHERE identificador = %s",
                (payment_method_id,),
            )

    @staticmethod
    def get_metrics(db: Connection, usuario_id: int) -> dict:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(DISTINCT subasta) as total FROM asistentes WHERE cliente = %s",
                (usuario_id,),
            )
            total_participadas = cursor.fetchone()["total"] or 0

            cursor.execute(
                "SELECT COUNT(DISTINCT subasta) as total FROM registrodesubasta WHERE cliente = %s",
                (usuario_id,),
            )
            total_ganadas = cursor.fetchone()["total"] or 0

            cursor.execute(
                "SELECT COUNT(*) as total_pujas, COALESCE(SUM(importe), 0) as total_importe FROM pujos p JOIN asistentes a ON p.asistente = a.identificador WHERE a.cliente = %s",
                (usuario_id,),
            )
            pujas_row = cursor.fetchone()
            total_pujas = pujas_row["total_pujas"] or 0
            monto_ofertado = float(pujas_row["total_importe"] or 0)

            cursor.execute(
                "SELECT COALESCE(SUM(total_final), 0) as total FROM pagos WHERE cliente_id = %s AND estado = 'pagado'",
                (usuario_id,),
            )
            total_pagado = float(cursor.fetchone()["total"] or 0)

            porcentaje_exito = 0.0
            if total_participadas > 0:
                porcentaje_exito = (total_ganadas / total_participadas) * 100.0

            cursor.execute(
                "SELECT DISTINCT s.categoria FROM subastas s JOIN asistentes a ON s.identificador = a.subasta WHERE a.cliente = %s",
                (usuario_id,),
            )
            categorias = [
                row["categoria"] for row in cursor.fetchall() if row["categoria"] is not None
            ]

            cursor.execute(
                "SELECT MAX(fecha_hora_inicio) as max_fecha FROM sesiones_subasta WHERE cliente_id = %s",
                (usuario_id,),
            )
            ultima_participacion = cursor.fetchone()["max_fecha"]

            return {
                "totalSubastasParticipadas": total_participadas,
                "totalSubastasGanadas": total_ganadas,
                "porcentajeExito": porcentaje_exito,
                "totalPujasRealizadas": total_pujas,
                "montoTotalOfertado": monto_ofertado,
                "montoTotalPagado": total_pagado,
                "categoriasParticipadas": categorias,
                "ultimaParticipacion": ultima_participacion,
            }

    @staticmethod
    def get_pagos_pendientes(db: Connection, usuario_id: int) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.identificador AS id,
                    p.subasta_id AS "subastaId",
                    p.cliente_id AS "usuarioId",
                    s.fecha AS "subastaFecha",
                    s.hora AS "subastaHora",
                    s.ubicacion AS "subastaUbicacion",
                    p.total_pujado AS "totalPujado",
                    p.comision,
                    p.costo_envio AS "costoEnvio",
                    p.total_final AS "totalFinal",
                    p.moneda,
                    p.modo_entrega AS "modoEntrega",
                    p.estado,
                    p.fecha_limite_pago AS "fechaLimitePago"
                FROM pagos p
                JOIN subastas s ON s.identificador = p.subasta_id
                WHERE p.cliente_id = %s
                  AND p.estado = 'pendiente'
                  AND s.estado = 'cerrada'
                ORDER BY p.fecha_limite_pago ASC, p.identificador DESC
                """,
                (usuario_id,),
            )
            pagos = cursor.fetchall()

        if not pagos:
            return []

        subasta_ids = [pago["subastaId"] for pago in pagos]
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.subasta AS "subastaId",
                    ic.identificador AS "itemId",
                    r.producto AS "productoId",
                    COALESCE(pr.descripcioncompleta, pr.descripcioncatalogo) AS descripcion,
                    r.importe,
                    r.comision
                FROM registrodesubasta r
                JOIN productos pr ON pr.identificador = r.producto
                LEFT JOIN catalogos c ON c.subasta = r.subasta
                LEFT JOIN itemscatalogo ic
                    ON ic.catalogo = c.identificador
                   AND ic.producto = r.producto
                WHERE r.cliente = %s
                  AND r.subasta = ANY(%s)
                ORDER BY r.subasta ASC, COALESCE(ic.identificador, r.producto) ASC
                """,
                (usuario_id, subasta_ids),
            )
            ventas = cursor.fetchall()

        items_by_subasta: dict[int, list[dict]] = {}
        for venta in ventas:
            item = dict(venta)
            subasta_id = item.pop("subastaId")
            for key in ("importe", "comision"):
                if item[key] is not None:
                    item[key] = float(item[key])
            items_by_subasta.setdefault(subasta_id, []).append(item)

        for pago in pagos:
            for key in ("totalPujado", "comision", "costoEnvio", "totalFinal"):
                if pago[key] is not None:
                    pago[key] = float(pago[key])
            pago["items"] = items_by_subasta.get(pago["subastaId"], [])

        return pagos

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
