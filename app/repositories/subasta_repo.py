from fastapi import HTTPException, status
from psycopg import Connection

from app.schemas.schemas import CatalogoItemInput, SubastaCreate


class SubastaRepository:

    # ─────────────────────── LISTADOS ───────────────────────

    @staticmethod
    def _normalizar_subastado(value) -> str:
        return "si" if value == "si" else "no"

    @staticmethod
    def _normalizar_fotos(value) -> list:
        if not value:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value]
        return list(value)

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
                        categoria, moneda
                    )
                    VALUES (%s, %s, 'abierta', %s, %s, %s, %s, %s, %s, %s)
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
                        subasta.moneda.value,
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

                    # Verificamos si ya existe un producto creado para la póliza de este artículo
                    cursor.execute(
                        "SELECT identificador FROM productos WHERE seguro = %s",
                        (articulo["seguro_poliza"],),
                    )
                    existing_product = cursor.fetchone()
                    if existing_product:
                        producto_id = existing_product["identificador"]
                    else:
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
                    s.moneda
                FROM subastas s
                WHERE s.estado = 'abierta'
                ORDER BY s.fecha, s.hora
                """,
                (),
            )
            return cursor.fetchall()

    @staticmethod
    def get_todas(db: Connection) -> list[dict]:
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
                    s.moneda
                FROM subastas s
                WHERE s.estado = 'abierta'
                ORDER BY s.fecha, s.hora
                """,
                (),
            )
            return cursor.fetchall()

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
                    s.moneda
                FROM subastas s
                WHERE s.identificador = %s
                  AND s.estado = 'abierta'
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
                ORDER BY ic.identificador
                """,
                (subasta_id,),
            )
            catalog_rows = cursor.fetchall()

            for item in catalog_rows:
                if item["mejorOfertaActual"] is not None:
                    item["mejorOfertaActual"] = float(item["mejorOfertaActual"])
                item["subastado"] = SubastaRepository._normalizar_subastado(
                    item.get("subastado")
                )
                item["fotos"] = SubastaRepository._normalizar_fotos(item.get("fotos"))

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
                    s.moneda
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
                ORDER BY ic.identificador
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

                item["subastado"] = SubastaRepository._normalizar_subastado(
                    item.get("subastado")
                )
                item["fotos"] = SubastaRepository._normalizar_fotos(item.get("fotos"))

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
    def get_item_activo_id(db: Connection, subasta_id: int) -> int | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT ic.identificador AS id
                FROM itemscatalogo ic
                JOIN catalogos c ON ic.catalogo = c.identificador
                WHERE c.subasta = %s
                  AND ic.subastado = 'no'
                ORDER BY ic.identificador
                LIMIT 1
                """,
                (subasta_id,),
            )
            row = cursor.fetchone()
            return row["id"] if row else None

    @staticmethod
    def get_item_activo_detalle(db: Connection, subasta_id: int) -> dict | None:
        with db.cursor() as cursor:
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
                  AND ic.subastado = 'no'
                ORDER BY ic.identificador
                LIMIT 1
                """,
                (subasta_id,),
            )
            item = cursor.fetchone()

        if not item:
            return None

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

        item["subastado"] = SubastaRepository._normalizar_subastado(
            item.get("subastado")
        )
        item["fotos"] = SubastaRepository._normalizar_fotos(item.get("fotos"))
        return item

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

    @staticmethod
    def get_garantia_validada_for_update(
        db: Connection,
        cliente_id: int,
        moneda: str,
    ) -> dict:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT identificador, limite_reservado
                FROM medios_pago
                WHERE cliente_id = %s
                  AND estado_verificacion = 'validado'
                  AND moneda = %s
                  AND limite_reservado > 0
                  AND tipo IN ('cheque_certificado', 'cuenta_bancaria')
                FOR UPDATE
                """,
                (cliente_id, moneda),
            )
            rows = cursor.fetchall()

        total = sum(float(row["limite_reservado"] or 0.0) for row in rows)
        return {"total": total, "medios": len(rows), "moneda": moneda}

    @staticmethod
    def get_exposicion_pagos_pendientes(
        db: Connection,
        cliente_id: int,
        moneda: str,
    ) -> float:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(total_final), 0) AS total
                FROM pagos
                WHERE cliente_id = %s
                  AND estado = 'pendiente'
                  AND moneda = %s
                """,
                (cliente_id, moneda),
            )
            row = cursor.fetchone()
            return float(row["total"] or 0.0)

    @staticmethod
    def get_pujas_ganadoras_parciales_activas(
        db: Connection,
        cliente_id: int,
    ) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    mejores.item_id AS "itemId",
                    mejores.importe
                FROM (
                    SELECT DISTINCT ON (pu.item)
                        pu.item AS item_id,
                        pu.importe,
                        a.cliente
                    FROM pujos pu
                    JOIN asistentes a ON pu.asistente = a.identificador
                    JOIN itemscatalogo ic ON pu.item = ic.identificador
                    JOIN catalogos c ON ic.catalogo = c.identificador
                    JOIN subastas s ON c.subasta = s.identificador
                    WHERE s.estado = 'abierta'
                      AND ic.subastado = 'no'
                    ORDER BY pu.item, pu.importe DESC, pu.identificador DESC
                ) mejores
                WHERE mejores.cliente = %s
                """,
                (cliente_id,),
            )
            rows = cursor.fetchall()

        for row in rows:
            row["importe"] = float(row["importe"] or 0.0)
        return rows

    # ─────────────────── JOIN / LEAVE ───────────────────

    @staticmethod
    def get_subasta_basica(db: Connection, subasta_id: int) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute("SELECT identificador, estado, categoria, moneda FROM subastas WHERE identificador = %s", (subasta_id,))
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
                """
                SELECT 1
                FROM sesiones_subasta ss
                JOIN subastas s ON s.identificador = ss.subasta_id
                WHERE ss.cliente_id = %s
                  AND ss.estado = 'activa'
                  AND ss.subasta_id != %s
                  AND s.estado = 'abierta'
                  AND s.fecha = CURRENT_DATE
                  AND s.hora <= CURRENT_TIME
                LIMIT 1
                """,
                (cliente_id, subasta_id),
            )
            return bool(cursor.fetchone())

    @staticmethod
    def tiene_sesion_activa(db: Connection, subasta_id: int, cliente_id: int) -> bool:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM sesiones_subasta
                WHERE subasta_id = %s AND cliente_id = %s AND estado = 'activa'
                """,
                (subasta_id, cliente_id),
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
                ORDER BY ic.identificador
                """,
                (subasta_id,),
            )
            return cursor.fetchall()

    @staticmethod
    def obtener_item_activo_con_puja(db: Connection, subasta_id: int) -> dict | None:
        """Devuelve el primer item pendiente con su mejor puja y datos del producto."""
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
                    ORDER BY pu.importe DESC, pu.identificador DESC
                    LIMIT 1
                ) puja ON true
                LEFT JOIN asistentes a ON puja.asistente = a.identificador
                WHERE c.subasta = %s AND ic.subastado = 'no'
                ORDER BY ic.identificador
                LIMIT 1
                FOR UPDATE OF ic
                """,
                (subasta_id,),
            )
            return cursor.fetchone()

    @staticmethod
    def contar_items_pendientes(db: Connection, subasta_id: int) -> int:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM itemscatalogo ic
                JOIN catalogos c ON ic.catalogo = c.identificador
                WHERE c.subasta = %s AND ic.subastado = 'no'
                """,
                (subasta_id,),
            )
            row = cursor.fetchone()
            return int(row["total"] or 0) if row else 0

    @staticmethod
    def cerrar_item(db: Connection, item_id: int, puja_id: int | None) -> None:
        with db.cursor() as cursor:
            cursor.execute("UPDATE itemscatalogo SET subastado = 'si' WHERE identificador = %s", (item_id,))
            if puja_id:
                cursor.execute("UPDATE pujos SET ganador = 'no' WHERE item = %s", (item_id,))
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
            cursor.execute(
                """
                SELECT identificador
                    , estado
                    , total_pujado
                    , comision
                    , costo_envio
                FROM pagos
                WHERE subasta_id = %s AND cliente_id = %s
                ORDER BY identificador DESC
                LIMIT 1
                """,
                (subasta_id, cliente_id),
            )
            existing = cursor.fetchone()
            if existing:
                if existing.get("estado") == "pendiente":
                    total_pujado_actual = float(existing.get("total_pujado") or 0.0)
                    comision_actual = float(existing.get("comision") or 0.0)
                    costo_envio_actual = float(existing.get("costo_envio") or 0.0)
                    nuevo_total_pujado = total_pujado_actual + total_pujado
                    nueva_comision = comision_actual + comision
                    nuevo_total_final = (
                        nuevo_total_pujado + nueva_comision + costo_envio_actual
                    )
                    cursor.execute(
                        """
                        UPDATE pagos
                        SET total_pujado = %s,
                            comision = %s,
                            total_final = %s,
                            moneda = %s
                        WHERE identificador = %s
                        """,
                        (
                            nuevo_total_pujado,
                            nueva_comision,
                            nuevo_total_final,
                            moneda,
                            existing["identificador"],
                        ),
                    )
                return existing["identificador"]

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
                    s.moneda,
                    pu.ganador = 'si' AS "esGanadoraParcial"
                FROM pujos pu
                JOIN asistentes a ON pu.asistente = a.identificador
                JOIN subastas s ON a.subasta = s.identificador
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
    def get_pagos_pendientes_vencidos(
        db: Connection, cliente_id: int | None = None
    ) -> list[dict]:
        query = """
            SELECT
                identificador AS id,
                subasta_id AS "subastaId",
                cliente_id AS "usuarioId",
                total_pujado AS "totalPujado",
                comision,
                total_final AS "totalFinal",
                moneda,
                estado,
                fecha_limite_pago AS "fechaLimitePago"
            FROM pagos
            WHERE estado = 'pendiente'
              AND fecha_limite_pago < NOW()
        """
        params: tuple = ()
        if cliente_id is not None:
            query += " AND cliente_id = %s"
            params = (cliente_id,)
        query += " ORDER BY fecha_limite_pago ASC FOR UPDATE"

        with db.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for row in rows:
                for key in ("totalPujado", "comision", "totalFinal"):
                    if row[key] is not None:
                        row[key] = float(row[key])
            return rows

    @staticmethod
    def marcar_pago_vencido(db: Connection, pago_id: int) -> bool:
        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE pagos
                SET estado = 'vencido'
                WHERE identificador = %s AND estado = 'pendiente'
                RETURNING identificador
                """,
                (pago_id,),
            )
            return bool(cursor.fetchone())

    @staticmethod
    def get_medio_pago_para_cliente(db: Connection, cliente_id: int, medio_pago_id: int) -> dict | None:
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
                (medio_pago_id, cliente_id),
            )
            return cursor.fetchone()

    @staticmethod
    def confirmar_pago(
        db: Connection,
        pago_id: int,
        medio_pago_id: int,
        modo_entrega: str,
        direccion_envio: str | None,
        acepta_perder_seguro: bool,
        costo_envio: float,
        total_final: float,
    ) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE pagos
                SET estado = 'pagado',
                    medio_pago_id = %s,
                    modo_entrega = %s,
                    direccion_envio = %s,
                    costo_envio = %s,
                    total_final = %s,
                    acepta_perder_seguro = %s
                WHERE identificador = %s
                """,
                (
                    medio_pago_id,
                    modo_entrega,
                    direccion_envio,
                    costo_envio,
                    total_final,
                    acepta_perder_seguro,
                    pago_id,
                ),
            )

    @staticmethod
    def get_primer_medio_pago_validado(db: Connection, cliente_id: int, moneda: str) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute( #Aca agarramos el id del ganador y la moneda de la subasta. Despues verifico el medio de pago que esta validado y que coincida con la moneda.
                """
                SELECT
                    identificador AS id,
                    cliente_id,
                    estado_verificacion,
                    moneda,
                    limite_reservado
                FROM medios_pago
                WHERE cliente_id = %s
                  AND estado_verificacion = 'validado'
                  AND moneda = %s
                  AND (es_cuenta_receptora = false OR es_cuenta_receptora IS NULL)
                ORDER BY identificador ASC
                LIMIT 1
                """,
                (cliente_id, moneda),
            )
            return cursor.fetchone()

    @staticmethod# Aca pedimos la direccion para mandarselo por envio
    def get_direccion_usuario(db: Connection, persona_id: int) -> str | None:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT direccion FROM personas WHERE identificador = %s",
                (persona_id,),
            )
            row = cursor.fetchone()
            return row["direccion"] if row else None

    @staticmethod
    def generar_multa(
        db: Connection, cliente_id: int, importe_pujado: float, motivo: str
    ) -> tuple[dict, bool]:
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
                WHERE cliente_id = %s AND motivo = %s
                ORDER BY identificador DESC
                LIMIT 1
                """,
                (cliente_id, motivo),
            )
            existing = cursor.fetchone()
            if existing:
                if existing["importe"] is not None:
                    existing["importe"] = float(existing["importe"])
                if existing["estado"] == "pendiente":
                    cursor.execute(
                        """
                        UPDATE clientes_adicionales
                        SET multa_activa = true
                        WHERE identificador = %s
                        """,
                        (cliente_id,),
                    )
                return existing, False

            multa_importe = importe_pujado * 0.10
            cursor.execute(
                """
                INSERT INTO multas (cliente_id, importe, estado, fecha_limite, motivo)
                VALUES (%s, %s, 'pendiente', NOW() + INTERVAL '72 hours', %s)
                RETURNING
                    identificador AS id,
                    importe,
                    estado,
                    fecha_limite AS "fechaLimite",
                    motivo
                """,
                (cliente_id, multa_importe, motivo),
            )
            multa = cursor.fetchone()
            if multa["importe"] is not None:
                multa["importe"] = float(multa["importe"])
            cursor.execute(
                "UPDATE clientes_adicionales SET multa_activa = true WHERE identificador = %s",
                (cliente_id,),
            )
            return multa, True

    @staticmethod
    def get_multas_pendientes_vencidas(
        db: Connection, cliente_id: int | None = None
    ) -> list[dict]:
        query = """
            SELECT
                m.identificador AS id,
                m.cliente_id,
                m.fecha_limite AS "fechaLimite",
                m.motivo,
                COALESCE(ca.bloqueado, false) AS bloqueado
            FROM multas m
            JOIN clientes_adicionales ca ON m.cliente_id = ca.identificador
            WHERE m.estado = 'pendiente'
              AND m.fecha_limite < NOW()
        """
        params: tuple = ()
        if cliente_id is not None:
            query += " AND m.cliente_id = %s"
            params = (cliente_id,)
        query += " ORDER BY m.fecha_limite ASC FOR UPDATE OF m, ca"

        with db.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    @staticmethod
    def bloquear_usuario(db: Connection, cliente_id: int) -> bool:
        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE clientes_adicionales
                SET bloqueado = true
                WHERE identificador = %s AND bloqueado = false
                RETURNING identificador
                """,
                (cliente_id,),
            )
            return bool(cursor.fetchone())

    # ─────────────────── NOTIFICACIONES ───────────────────

    @staticmethod
    def crear_notificacion(db: Connection, persona_id: int, tipo: str, mensaje: str) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO notificaciones (persona_id, tipo, mensaje) VALUES (%s, %s, %s)",
                (persona_id, tipo, mensaje),
            )
