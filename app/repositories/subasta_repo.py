from fastapi import HTTPException, status
from psycopg import Connection

from app.schemas.schemas import CatalogoItemInput, SubastaCreate


class SubastaRepository:

    # ─────────────────────── LISTADOS ───────────────────────

    @staticmethod
    def _resolve_catalog_responsable(db: Connection, usuario_id: int | None) -> int:
        with db.cursor() as cursor:
            if usuario_id is not None:
                cursor.execute(
                    "SELECT identificador FROM empleados WHERE identificador = %s",
                    (usuario_id,),
                )
                row = cursor.fetchone()
                if row:
                    return row["identificador"]

            cursor.execute(
                "SELECT identificador FROM empleados ORDER BY identificador LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No hay empleados disponibles para asignar como responsable del catalogo.",
                )
            return row["identificador"]

    @staticmethod
    def _ensure_subastador_exists(db: Connection, subastador_id: int | None) -> None:
        if subastador_id is None:
            return

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM subastadores WHERE identificador = %s",
                (subastador_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El subastadorId indicado no existe.",
                )

    @staticmethod
    def create_subasta(
        db: Connection,
        subasta: SubastaCreate,
        usuario_id: int | None,
    ) -> dict:
        try:
            SubastaRepository._ensure_subastador_exists(db, subasta.subastadorId)
            responsable_id = SubastaRepository._resolve_catalog_responsable(
                db, usuario_id
            )

            with db.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO subastas (
                        fecha, hora, estado, subastador, ubicacion,
                        capacidadasistentes, tienedeposito, seguridadpropia,
                        categoria
                    )
                    VALUES (%s, %s, 'abierta', %s, %s, %s, %s, %s, %s)
                    RETURNING
                        identificador AS id,
                        fecha,
                        hora::text AS hora,
                        estado,
                        categoria,
                        ubicacion
                    """,
                    (
                        subasta.fecha,
                        subasta.hora,
                        subasta.subastadorId,
                        subasta.ubicacion,
                        subasta.capacidadAsistentes,
                        "si" if subasta.tieneDeposito else "no",
                        "si" if subasta.seguridadPropia else "no",
                        subasta.categoria.value,
                    ),
                )
                created = cursor.fetchone()

                cursor.execute(
                    """
                    INSERT INTO catalogos (descripcion, subasta, responsable)
                    VALUES (%s, %s, %s)
                    RETURNING identificador
                    """,
                    (
                        f"Catalogo de subasta {created['id']}",
                        created["id"],
                        responsable_id,
                    ),
                )
                catalogo_id = cursor.fetchone()["identificador"]

            db.commit()
            created["moneda"] = subasta.moneda.value
            created["catalogoId"] = catalogo_id
            return created
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _get_or_create_catalogo(
        db: Connection,
        subasta_id: int,
        usuario_id: int | None,
    ) -> int:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT identificador FROM subastas WHERE identificador = %s",
                (subasta_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subasta no encontrada.",
                )

            cursor.execute(
                """
                SELECT identificador
                FROM catalogos
                WHERE subasta = %s
                ORDER BY identificador
                LIMIT 1
                """,
                (subasta_id,),
            )
            catalogo = cursor.fetchone()
            if catalogo:
                return catalogo["identificador"]

            responsable_id = SubastaRepository._resolve_catalog_responsable(
                db, usuario_id
            )
            cursor.execute(
                """
                INSERT INTO catalogos (descripcion, subasta, responsable)
                VALUES (%s, %s, %s)
                RETURNING identificador
                """,
                (f"Catalogo de subasta {subasta_id}", subasta_id, responsable_id),
            )
            return cursor.fetchone()["identificador"]

    @staticmethod
    def add_catalog_item(
        db: Connection,
        subasta_id: int,
        item: CatalogoItemInput,
        usuario_id: int | None,
    ) -> dict:
        try:
            with db.cursor() as cursor:
                producto_id = item.productoId
                if producto_id is None:
                    cursor.execute(
                        """
                        SELECT
                            identificador,
                            descripcion,
                            duenio_id,
                            estado,
                            tasacion_aceptada,
                            seguro_poliza,
                            fotos
                        FROM articulos
                        WHERE identificador = %s
                        """,
                        (item.articuloId,),
                    )
                    articulo = cursor.fetchone()
                    if not articulo:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Artículo no encontrado.",
                        )
                    if (
                        articulo["estado"] != "aprobado"
                        or not articulo["tasacion_aceptada"]
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="El artículo debe estar aprobado y con tasación aceptada.",
                        )

                    revisor_id = SubastaRepository._resolve_catalog_responsable(
                        db, usuario_id
                    )
                    cursor.execute(
                        """
                        INSERT INTO productos (
                            fecha,
                            disponible,
                            descripcioncatalogo,
                            descripcioncompleta,
                            revisor,
                            duenio,
                            seguro
                        )
                        VALUES (CURRENT_DATE, 'si', %s, %s, %s, %s, %s)
                        RETURNING identificador
                        """,
                        (
                            articulo["descripcion"],
                            articulo["descripcion"],
                            revisor_id,
                            articulo["duenio_id"],
                            articulo["seguro_poliza"],
                        ),
                    )
                    producto_id = cursor.fetchone()["identificador"]
                    for foto_url in articulo.get("fotos") or []:
                        cursor.execute(
                            """
                            INSERT INTO fotos_adicionales (producto, foto_url)
                            VALUES (%s, %s)
                            """,
                            (producto_id, str(foto_url)),
                        )
                else:
                    cursor.execute(
                        "SELECT 1 FROM productos WHERE identificador = %s",
                        (producto_id,),
                    )
                    if not cursor.fetchone():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="El productoId indicado no existe.",
                        )

            catalogo_id = SubastaRepository._get_or_create_catalogo(
                db, subasta_id, usuario_id
            )

            with db.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO itemscatalogo (
                        catalogo, producto, preciobase, comision, subastado
                    )
                    VALUES (%s, %s, %s, %s, 'no')
                    RETURNING
                        identificador AS id,
                        producto AS "productoId",
                        preciobase AS "precioBase",
                        comision,
                        subastado
                    """,
                    (
                        catalogo_id,
                        producto_id,
                        item.precioBase,
                        item.comision,
                    ),
                )
                created = cursor.fetchone()

            db.commit()
            created["subastaId"] = subasta_id
            created["catalogoId"] = catalogo_id
            created["precioBase"] = float(created["precioBase"])
            created["comision"] = float(created["comision"])
            return created
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_publicas(db: Connection) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.identificador AS id,
                    s.fecha,
                    s.hora::text AS hora,
                    CASE WHEN s.estado = 'carrada' THEN 'cerrada' ELSE s.estado END AS estado,
                    s.categoria,
                    s.ubicacion,
                    'USD' AS moneda
                FROM subastas s
                ORDER BY s.fecha, s.hora
                """
            )
            return cursor.fetchall()

    @staticmethod
    def get_todas(db: Connection) -> list[dict]:
        return SubastaRepository.get_publicas(db)

    @staticmethod
    def get_publica_detalle(db: Connection, subasta_id: int, base_url: str) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.identificador AS id,
                    s.fecha,
                    s.hora::text AS hora,
                    CASE WHEN s.estado = 'carrada' THEN 'cerrada' ELSE s.estado END AS estado,
                    s.categoria,
                    s.ubicacion,
                    'USD' AS moneda
                FROM subastas s
                WHERE s.identificador = %s
                """,
                (subasta_id,),
            )
            subasta = cursor.fetchone()
            if not subasta:
                return None

            cursor.execute(
                """
                SELECT
                    ic.identificador AS id,
                    p.descripcioncompleta AS descripcion,
                    (SELECT MAX(importe) FROM pujos WHERE item = ic.identificador) AS "mejorOfertaActual",
                    ic.subastado,
                    (
                        SELECT COALESCE(jsonb_agg(f.foto_url), '[]'::jsonb)
                        FROM fotos_adicionales f
                        WHERE f.producto = ic.producto
                    ) AS fotos
                FROM itemscatalogo ic
                JOIN catalogos c ON ic.catalogo = c.identificador
                JOIN productos p ON ic.producto = p.identificador
                WHERE c.subasta = %s
                """,
                (subasta_id,),
            )
            catalog_rows = cursor.fetchall()

            for item in catalog_rows:
                if item["mejorOfertaActual"] is not None:
                    item["mejorOfertaActual"] = float(item["mejorOfertaActual"])
                item["subastado"] = "si" if item.get("subastado") == "si" else False
                item["fotos"] = item.get("fotos") or []

            subasta["catalogo"] = catalog_rows
            return subasta

    @staticmethod
    def get_detalle(db: Connection, subasta_id: int, base_url: str) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.identificador AS id,
                    s.fecha,
                    s.hora::text AS hora,
                    CASE WHEN s.estado = 'carrada' THEN 'cerrada' ELSE s.estado END AS estado,
                    s.categoria,
                    s.ubicacion,
                    'USD' AS moneda
                FROM subastas s
                WHERE s.identificador = %s
                """,
                (subasta_id,),
            )
            subasta = cursor.fetchone()
            if not subasta:
                return None

            cursor.execute(
                """
                SELECT
                    ic.identificador AS id,
                    p.descripcioncompleta AS descripcion,
                    ic.preciobase AS "precioBase",
                    (SELECT MAX(importe) FROM pujos WHERE item = ic.identificador) AS "mejorOfertaActual",
                    ic.subastado,
                    (
                        SELECT COALESCE(jsonb_agg(f.foto_url), '[]'::jsonb)
                        FROM fotos_adicionales f
                        WHERE f.producto = ic.producto
                    ) AS fotos
                FROM itemscatalogo ic
                JOIN catalogos c ON ic.catalogo = c.identificador
                JOIN productos p ON ic.producto = p.identificador
                WHERE c.subasta = %s
                """,
                (subasta_id,),
            )
            catalog_rows = cursor.fetchall()

            for item in catalog_rows:
                if item["precioBase"] is not None:
                    item["precioBase"] = float(item["precioBase"])
                if item["mejorOfertaActual"] is not None:
                    item["mejorOfertaActual"] = float(item["mejorOfertaActual"])

                precio_base = item["precioBase"] or 0.0
                mejor_oferta = item["mejorOfertaActual"] or 0.0

                if mejor_oferta == 0.0:
                    item["limiteMinimo"] = precio_base
                    item["limiteMaximo"] = precio_base + (precio_base * 0.20)
                else:
                    item["limiteMinimo"] = mejor_oferta + (precio_base * 0.01)
                    item["limiteMaximo"] = mejor_oferta + (precio_base * 0.20)

                item["subastado"] = "si" if item.get("subastado") == "si" else False
                item["fotos"] = item.get("fotos") or []

            subasta["catalogo"] = catalog_rows
            return subasta

    # ─────────────────── PUJAS ───────────────────

    @staticmethod
    def get_asistente_id(db: Connection, subasta_id: int, cliente_id: int) -> int | None:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT identificador FROM asistentes WHERE subasta = %s AND cliente = %s",
                (subasta_id, cliente_id),
            )
            row = cursor.fetchone()
            return row["identificador"] if row else None

    @staticmethod
    def get_item_for_update(db: Connection, subasta_id: int, item_id: int) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT ic.identificador AS id, ic.preciobase, ic.subastado, ic.comision
                FROM itemscatalogo ic
                JOIN catalogos c ON ic.catalogo = c.identificador
                WHERE ic.identificador = %s AND c.subasta = %s
                FOR UPDATE OF ic
                """,
                (item_id, subasta_id),
            )
            return cursor.fetchone()

    @staticmethod
    def get_mejor_oferta(db: Connection, item_id: int) -> float:
        with db.cursor() as cursor:
            cursor.execute("SELECT MAX(importe) AS max_importe FROM pujos WHERE item = %s", (item_id,))
            row = cursor.fetchone()
            if row and row["max_importe"] is not None:
                return float(row["max_importe"])
            return 0.0

    @staticmethod
    def registrar_puja(db: Connection, asistente_id: int, item_id: int, importe: float) -> int:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pujos (asistente, item, importe, ganador)
                VALUES (%s, %s, %s, 'no')
                RETURNING identificador
                """,
                (asistente_id, item_id, importe),
            )
            return cursor.fetchone()["identificador"]

    # ─────────────────── JOIN / LEAVE ───────────────────

    @staticmethod
    def get_subasta_basica(db: Connection, subasta_id: int) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute("SELECT identificador, estado, categoria FROM subastas WHERE identificador = %s", (subasta_id,))
            return cursor.fetchone()

    @staticmethod
    def tiene_medio_pago_validado(db: Connection, cliente_id: int) -> bool:
        with db.cursor() as cursor:
            cursor.execute("SELECT 1 FROM medios_pago WHERE cliente_id = %s AND estado_verificacion = 'validado'", (cliente_id,))
            return bool(cursor.fetchone())

    @staticmethod
    def puede_participar(db: Connection, cliente_id: int) -> bool:
        with db.cursor() as cursor:
            cursor.execute("SELECT bloqueado, multa_activa FROM clientes_adicionales WHERE identificador = %s", (cliente_id,))
            row = cursor.fetchone()
            if not row:
                return False
            return not (row["bloqueado"] or row["multa_activa"])

    @staticmethod
    def check_otra_sesion_activa(db: Connection, subasta_id: int, cliente_id: int) -> bool:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM sesiones_subasta WHERE cliente_id = %s AND estado = 'activa' AND subasta_id != %s",
                (cliente_id, subasta_id),
            )
            return bool(cursor.fetchone())

    @staticmethod
    def join_subasta(db: Connection, subasta_id: int, cliente_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute("SELECT 1 FROM asistentes WHERE subasta = %s AND cliente = %s", (subasta_id, cliente_id))
            if not cursor.fetchone():
                cursor.execute("SELECT COALESCE(MAX(numeropostor), 0) + 1 AS next_nro FROM asistentes WHERE subasta = %s", (subasta_id,))
                next_nro = cursor.fetchone()["next_nro"]
                cursor.execute(
                    "INSERT INTO asistentes (numeropostor, cliente, subasta) VALUES (%s, %s, %s)",
                    (next_nro, cliente_id, subasta_id),
                )

            cursor.execute("SELECT identificador FROM sesiones_subasta WHERE subasta_id = %s AND cliente_id = %s", (subasta_id, cliente_id))
            sesion = cursor.fetchone()
            if sesion:
                cursor.execute("UPDATE sesiones_subasta SET estado = 'activa' WHERE identificador = %s", (sesion["identificador"],))
            else:
                cursor.execute(
                    "INSERT INTO sesiones_subasta (subasta_id, cliente_id, estado) VALUES (%s, %s, 'activa')",
                    (subasta_id, cliente_id),
                )

    @staticmethod
    def leave_subasta(db: Connection, subasta_id: int, cliente_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE sesiones_subasta SET estado = 'finalizada' WHERE subasta_id = %s AND cliente_id = %s",
                (subasta_id, cliente_id),
            )

    # ─────────────────── CIERRE DE SUBASTA ───────────────────

    @staticmethod
    def marcar_subasta_cerrada(db: Connection, subasta_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute("UPDATE subastas SET estado = 'cerrada' WHERE identificador = %s", (subasta_id,))

    @staticmethod
    def obtener_items_con_pujas(db: Connection, subasta_id: int) -> list[dict]:
        """Devuelve cada item del catalogo con su puja maxima (ganadora) y datos del producto."""
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ic.identificador AS item_id,
                    ic.preciobase,
                    ic.comision,
                    ic.producto,
                    p.duenio,
                    puja.identificador AS puja_id,
                    puja.importe AS puja_importe,
                    a.cliente AS cliente_ganador
                FROM itemscatalogo ic
                JOIN catalogos c ON ic.catalogo = c.identificador
                JOIN productos p ON ic.producto = p.identificador
                LEFT JOIN LATERAL (
                    SELECT pu.identificador, pu.importe, pu.asistente
                    FROM pujos pu
                    WHERE pu.item = ic.identificador
                    ORDER BY pu.importe DESC
                    LIMIT 1
                ) puja ON true
                LEFT JOIN asistentes a ON puja.asistente = a.identificador
                WHERE c.subasta = %s AND ic.subastado = 'no'
                """,
                (subasta_id,),
            )
            return cursor.fetchall()

    @staticmethod
    def cerrar_item(db: Connection, item_id: int, puja_id: int | None) -> None:
        with db.cursor() as cursor:
            cursor.execute("UPDATE itemscatalogo SET subastado = 'si' WHERE identificador = %s", (item_id,))
            if puja_id:
                cursor.execute("UPDATE pujos SET ganador = 'si' WHERE identificador = %s", (puja_id,))

    @staticmethod
    def registrar_venta(db: Connection, subasta_id: int, duenio_id: int, producto_id: int, cliente_id: int, importe: float, comision: float) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO registrodesubasta (subasta, duenio, producto, cliente, importe, comision)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (subasta_id, duenio_id, producto_id, cliente_id, importe, comision),
            )

    @staticmethod
    def generar_pago(db: Connection, subasta_id: int, cliente_id: int, total_pujado: float, comision: float, moneda: str) -> int:
        with db.cursor() as cursor:
            total_final = total_pujado + comision
            cursor.execute(
                """
                INSERT INTO pagos (subasta_id, cliente_id, total_pujado, comision, total_final, moneda, estado, fecha_limite_pago)
                VALUES (%s, %s, %s, %s, %s, %s, 'pendiente', NOW() + INTERVAL '72 hours')
                RETURNING identificador
                """,
                (subasta_id, cliente_id, total_pujado, comision, total_final, moneda),
            )
            return cursor.fetchone()["identificador"]

    @staticmethod
    def finalizar_sesiones(db: Connection, subasta_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE sesiones_subasta SET estado = 'finalizada' WHERE subasta_id = %s AND estado = 'activa'",
                (subasta_id,),
            )

    # ─────────────────── HISTORIAL ───────────────────

    @staticmethod
    def get_historial_pujas(db: Connection, subasta_id: int) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    pu.identificador AS id,
                    a.cliente AS "usuarioId",
                    pu.item AS "itemId",
                    pu.importe,
                    'USD' AS moneda,
                    pu.ganador = 'si' AS "esGanadoraParcial"
                FROM pujos pu
                JOIN asistentes a ON pu.asistente = a.identificador
                WHERE a.subasta = %s
                ORDER BY pu.importe DESC
                """,
                (subasta_id,),
            )
            rows = cursor.fetchall()
            for r in rows:
                r["importe"] = float(r["importe"])
            return rows

    # ─────────────────── PAGOS ───────────────────

    @staticmethod
    def get_pago_usuario(db: Connection, subasta_id: int, cliente_id: int) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    identificador AS id,
                    subasta_id AS "subastaId",
                    cliente_id AS "usuarioId",
                    total_pujado AS "totalPujado",
                    comision,
                    costo_envio AS "costoEnvio",
                    total_final AS "totalFinal",
                    moneda,
                    modo_entrega AS "modoEntrega",
                    estado,
                    fecha_limite_pago AS "fechaLimitePago"
                FROM pagos
                WHERE subasta_id = %s AND cliente_id = %s
                """,
                (subasta_id, cliente_id),
            )
            row = cursor.fetchone()
            if row:
                for key in ("totalPujado", "comision", "costoEnvio", "totalFinal"):
                    if row[key] is not None:
                        row[key] = float(row[key])
            return row

    @staticmethod
    def confirmar_pago(db: Connection, pago_id: int, medio_pago_id: int, modo_entrega: str, direccion_envio: str | None, acepta_perder_seguro: bool) -> None:
        with db.cursor() as cursor:
            costo_envio = 0.0
            if modo_entrega == "envio":
                costo_envio = 500.0  # Costo fijo de envio simplificado

            cursor.execute(
                """
                UPDATE pagos
                SET estado = 'pagado',
                    medio_pago_id = %s,
                    modo_entrega = %s,
                    direccion_envio = %s,
                    costo_envio = %s,
                    total_final = total_pujado + comision + %s,
                    acepta_perder_seguro = %s
                WHERE identificador = %s
                """,
                (medio_pago_id, modo_entrega, direccion_envio, costo_envio, costo_envio, acepta_perder_seguro, pago_id),
            )

    @staticmethod
    def generar_multa(db: Connection, cliente_id: int, importe_pujado: float, motivo: str) -> None:
        with db.cursor() as cursor:
            multa_importe = importe_pujado * 0.10
            cursor.execute(
                """
                INSERT INTO multas (cliente_id, importe, estado, fecha_limite, motivo)
                VALUES (%s, %s, 'pendiente', NOW() + INTERVAL '72 hours', %s)
                """,
                (cliente_id, multa_importe, motivo),
            )
            cursor.execute(
                "UPDATE clientes_adicionales SET multa_activa = true WHERE identificador = %s",
                (cliente_id,),
            )

    @staticmethod
    def bloquear_usuario(db: Connection, cliente_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE clientes_adicionales SET bloqueado = true WHERE identificador = %s",
                (cliente_id,),
            )

    # ─────────────────── NOTIFICACIONES ───────────────────

    @staticmethod
    def crear_notificacion(db: Connection, persona_id: int, tipo: str, mensaje: str) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO notificaciones (persona_id, tipo, mensaje) VALUES (%s, %s, %s)",
                (persona_id, tipo, mensaje),
            )
