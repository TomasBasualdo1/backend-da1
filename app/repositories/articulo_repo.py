from psycopg import Connection


class ArticuloRepository:

    @staticmethod
    def crear_articulo(db: Connection, duenio_id: int, descripcion: str, historia: str | None,
                       artista: str | None, fecha_creacion: str | None, es_propietario: bool,
                       declara_origen_licito: bool, fotos: list[str], documentacion: list[str] | None) -> int:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO articulos (
                    duenio_id, descripcion, historia, artista, fecha_creacion,
                    es_propietario, declara_origen_licito, estado, fotos, documentacion_origen, fecha_envio
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendiente', %s, %s, NOW())
                RETURNING identificador
                """,
                (duenio_id, descripcion, historia, artista, fecha_creacion,
                 es_propietario, declara_origen_licito, fotos, documentacion or []),
            )
            return cursor.fetchone()["identificador"]

    @staticmethod
    def get_articulos_por_duenio(db: Connection, duenio_id: int) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.identificador AS id,
                    a.descripcion,
                    a.precio_base_propuesto AS "precioBasePropuesto",
                    a.comision_propuesta AS "comisionPropuesta",
                    a.tasacion_aceptada AS "tasacionAceptada",
                    a.historia,
                    a.artista,
                    a.fecha_creacion AS "fechaCreacion",
                    a.estado,
                    a.motivo_rechazo AS "motivoRechazo",
                    a.fecha_envio AS "fechaEnvio",
                    a.fotos,
                    a.ubicacion,
                    s.nropoliza AS seguro_poliza,
                    s.compania AS seguro_compania,
                    s.importe AS seguro_monto
                FROM articulos a
                LEFT JOIN seguros s ON a.seguro_poliza = s.nropoliza
                WHERE a.duenio_id = %s
                ORDER BY a.fecha_envio DESC
                """,
                (duenio_id,),
            )
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                if item.get("seguro_poliza"):
                    item["seguro"] = {
                        "poliza": item["seguro_poliza"],
                        "compania": item["seguro_compania"],
                        "montoAsegurado": float(item["seguro_monto"]) if item["seguro_monto"] else None,
                    }
                else:
                    item["seguro"] = None
                for k in ("seguro_poliza", "seguro_compania", "seguro_monto"):
                    item.pop(k, None)
                if item.get("precioBasePropuesto") is not None:
                    item["precioBasePropuesto"] = float(item["precioBasePropuesto"])
                if item.get("comisionPropuesta") is not None:
                    item["comisionPropuesta"] = float(item["comisionPropuesta"])
                result.append(item)
            return result

    @staticmethod
    def get_articulo(db: Connection, articulo_id: int) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.identificador AS id, a.duenio_id, a.descripcion,
                    a.precio_base_propuesto AS "precioBasePropuesto",
                    a.comision_propuesta AS "comisionPropuesta",
                    a.tasacion_aceptada AS "tasacionAceptada",
                    a.historia, a.artista,
                    a.fecha_creacion AS "fechaCreacion",
                    a.estado,
                    a.motivo_rechazo AS "motivoRechazo",
                    a.fecha_envio AS "fechaEnvio",
                    a.fotos, a.ubicacion,
                    s.nropoliza AS seguro_poliza,
                    s.compania AS seguro_compania,
                    s.importe AS seguro_monto
                FROM articulos a
                LEFT JOIN seguros s ON a.seguro_poliza = s.nropoliza
                WHERE a.identificador = %s
                """,
                (articulo_id,),
            )
            r = cursor.fetchone()
            if not r:
                return None
            item = dict(r)
            if item.get("seguro_poliza"):
                item["seguro"] = {
                    "poliza": item["seguro_poliza"],
                    "compania": item["seguro_compania"],
                    "montoAsegurado": float(item["seguro_monto"]) if item["seguro_monto"] else None,
                }
            else:
                item["seguro"] = None
            for k in ("seguro_poliza", "seguro_compania", "seguro_monto"):
                item.pop(k, None)
            if item.get("precioBasePropuesto") is not None:
                item["precioBasePropuesto"] = float(item["precioBasePropuesto"])
            if item.get("comisionPropuesta") is not None:
                item["comisionPropuesta"] = float(item["comisionPropuesta"])
            return item

    @staticmethod
    def aceptar_tasacion(db: Connection, articulo_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE articulos SET tasacion_aceptada = true WHERE identificador = %s",
                (articulo_id,),
            )

    @staticmethod
    def rechazar_tasacion(db: Connection, articulo_id: int) -> None:
        """El dueño rechaza la tasación => se devuelve el artículo."""
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE articulos SET tasacion_aceptada = false, estado = 'devuelto' WHERE identificador = %s",
                (articulo_id,),
            )

    @staticmethod
    def evaluar_articulo(db: Connection, articulo_id: int, estado: str, motivo_rechazo: str | None,
                         precio_base: float | None, comision: float | None) -> None:
        with db.cursor() as cursor:
            if estado == "aprobado":
                cursor.execute(
                    """
                    UPDATE articulos
                    SET estado = 'aprobado', precio_base_propuesto = %s, comision_propuesta = %s
                    WHERE identificador = %s
                    """,
                    (precio_base, comision, articulo_id),
                )
            else:
                cursor.execute(
                    "UPDATE articulos SET estado = 'rechazado', motivo_rechazo = %s WHERE identificador = %s",
                    (motivo_rechazo, articulo_id),
                )

    @staticmethod
    def aumentar_seguro(db: Connection, articulo_id: int, monto_nuevo: float) -> None:
        with db.cursor() as cursor:
            cursor.execute("SELECT seguro_poliza FROM articulos WHERE identificador = %s", (articulo_id,))
            row = cursor.fetchone()
            if row and row["seguro_poliza"]:
                cursor.execute(
                    "UPDATE seguros SET importe = %s WHERE nropoliza = %s",
                    (monto_nuevo, row["seguro_poliza"]),
                )

    @staticmethod
    def get_all_pendientes(db: Connection) -> list[dict]:
        """Para el admin: lista todos los articulos en estado pendiente."""
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.identificador AS id, a.descripcion, a.estado, a.fecha_envio AS "fechaEnvio",
                       p.nombre AS duenio_nombre, a.duenio_id
                FROM articulos a
                JOIN personas p ON a.duenio_id = p.identificador
                WHERE a.estado IN ('pendiente', 'en_inspeccion')
                ORDER BY a.fecha_envio
                """
            )
            return cursor.fetchall()
