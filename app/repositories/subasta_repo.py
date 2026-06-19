from fastapi import HTTPException, status
from psycopg import Connection

from app.schemas.schemas import CatalogoItemInput, SubastaCreate


class SubastaRepository:
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
        producto_id = (
            item.productoId if item.productoId is not None else item.articuloId
        )

        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM productos WHERE identificador = %s",
                    (producto_id,),
                )
                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="El productoId/articuloId indicado no existe como producto.",
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
                
                # Convert 'no' to False for Pydantic enum validation consistency
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
                
                item["limiteMinimo"] = None
                item["limiteMaximo"] = None
                
                # Convert 'no' to False for Pydantic enum validation consistency
                item["subastado"] = "si" if item.get("subastado") == "si" else False
                
                item["fotos"] = item.get("fotos") or []

            subasta["catalogo"] = catalog_rows
            return subasta
