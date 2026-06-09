from psycopg import Connection

class SubastaRepository:
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
                        SELECT COALESCE(jsonb_agg(f.identificador), '[]'::jsonb)
                        FROM fotos f
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
                
                photo_ids = item.get("fotos") or []
                item["fotos"] = [f"{base_url}/uploads/fotos/{fid}" for fid in photo_ids]

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
                        SELECT COALESCE(jsonb_agg(f.identificador), '[]'::jsonb)
                        FROM fotos f
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
                
                photo_ids = item.get("fotos") or []
                item["fotos"] = [f"{base_url}/uploads/fotos/{fid}" for fid in photo_ids]

            subasta["catalogo"] = catalog_rows
            return subasta
