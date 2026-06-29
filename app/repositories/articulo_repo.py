from uuid import uuid4

from fastapi import HTTPException, status
from psycopg import Connection

from app.schemas.schemas import ArticuloEvaluacion, ArticuloInput


class ArticuloRepository:
    DEFAULT_VERIFICADOR_ID = 1
    DEFAULT_REVISOR_ID = 1
    DEFAULT_COMPANIA_SEGURO = "Cobertura DA1"

    @staticmethod
    def _dump_schema(data):
        if hasattr(data, "model_dump"):
            return data.model_dump()
        return data.dict()

    @staticmethod
    def _to_url_list(values) -> list[str]:
        return [str(value) for value in (values or [])]

    @staticmethod
    def _row_to_articulo(row: dict | None) -> dict | None:
        if not row:
            return None

        articulo = dict(row)
        for key in ("precioSugeridoUsuario", "precioBasePropuesto", "comisionPropuesta"):
            if articulo.get(key) is not None:
                articulo[key] = float(articulo[key])

        if articulo.get("moneda") is not None:
            articulo["moneda"] = str(articulo["moneda"])

        seguro_poliza = articulo.pop("seguroPoliza", None)
        seguro_compania = articulo.pop("seguroCompania", None)
        seguro_importe = articulo.pop("seguroImporte", None)
        articulo["seguro"] = None
        if seguro_poliza:
            articulo["seguro"] = {
                "poliza": seguro_poliza,
                "compania": seguro_compania,
                "montoAsegurado": (
                    float(seguro_importe) if seguro_importe is not None else None
                ),
            }

        articulo["fotos"] = articulo.get("fotos") or []
        articulo["documentacionOrigen"] = articulo.get("documentacionOrigen") or []
        return articulo

    @staticmethod
    def ensure_duenio(db: Connection, persona_id: int) -> int:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT identificador FROM duenios WHERE identificador = %s",
                (persona_id,),
            )
            duenio = cursor.fetchone()
            if duenio:
                return duenio["identificador"]

            cursor.execute(
                "SELECT numeropais FROM clientes WHERE identificador = %s",
                (persona_id,),
            )
            cliente = cursor.fetchone()
            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente no encontrado para crear duenio.",
                )

            cursor.execute(
                """
                INSERT INTO duenios (
                    identificador,
                    numeropais,
                    verificacionfinanciera,
                    verificacionjudicial,
                    calificacionriesgo,
                    verificador
                )
                VALUES (%s, %s, 'si', 'si', 1, %s)
                RETURNING identificador
                """,
                (
                    persona_id,
                    cliente["numeropais"],
                    ArticuloRepository.DEFAULT_VERIFICADOR_ID,
                ),
            )
            return cursor.fetchone()["identificador"]

    @staticmethod
    def create_articulo(
        db: Connection,
        duenio_id: int,
        data: ArticuloInput,
    ) -> dict:
        payload = ArticuloRepository._dump_schema(data)

        try:
            with db.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO articulos (
                        duenio_id,
                        descripcion,
                        historia,
                        artista,
                        fecha_creacion,
                        es_propietario,
                        declara_origen_licito,
                        estado,
                        fecha_envio,
                        fotos,
                        documentacion_origen,
                        precio_sugerido_usuario,
                        moneda
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendiente', CURRENT_TIMESTAMP, %s, %s, %s, %s)
                    RETURNING
                        identificador AS id,
                        duenio_id AS "duenioId",
                        descripcion,
                        historia,
                        artista,
                        fecha_creacion AS "fechaCreacion",
                        estado,
                        motivo_rechazo AS "motivoRechazo",
                        precio_sugerido_usuario AS "precioSugeridoUsuario",
                        moneda,
                        precio_base_propuesto AS "precioBasePropuesto",
                        comision_propuesta AS "comisionPropuesta",
                        tasacion_aceptada AS "tasacionAceptada",
                        fecha_envio AS "fechaEnvio",
                        ubicacion,
                        seguro_poliza AS "seguroPoliza",
                        fotos,
                        documentacion_origen AS "documentacionOrigen"
                    """,
                    (
                        duenio_id,
                        payload["descripcion"],
                        payload.get("historia"),
                        payload.get("artista"),
                        payload.get("fechaCreacion"),
                        payload.get("esPropietario", True),
                        payload.get("declaraOrigenLicito", True),
                        ArticuloRepository._to_url_list(payload.get("fotos")),
                        ArticuloRepository._to_url_list(
                            payload.get("documentacionOrigen")
                        ),
                        payload.get("precioSugeridoUsuario"),
                        payload.get("moneda"),
                    ),
                )
                created = ArticuloRepository._row_to_articulo(cursor.fetchone())

            db.commit()
            return created
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_articulo(db: Connection, id: int) -> dict | None:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.identificador AS id,
                    a.duenio_id AS "duenioId",
                    a.descripcion,
                    a.historia,
                    a.artista,
                    a.fecha_creacion AS "fechaCreacion",
                    a.estado,
                    a.motivo_rechazo AS "motivoRechazo",
                    a.precio_sugerido_usuario AS "precioSugeridoUsuario",
                    a.moneda,
                    a.precio_base_propuesto AS "precioBasePropuesto",
                    a.comision_propuesta AS "comisionPropuesta",
                    a.tasacion_aceptada AS "tasacionAceptada",
                    a.fecha_envio AS "fechaEnvio",
                    a.ubicacion,
                    a.fotos,
                    a.documentacion_origen AS "documentacionOrigen",
                    s.nropoliza AS "seguroPoliza",
                    s.compania AS "seguroCompania",
                    s.importe AS "seguroImporte",
                    sub_info."subastaId",
                    sub_info."subastaFecha",
                    sub_info."subastaHora",
                    sub_info."subastaEstado"
                FROM articulos a
                LEFT JOIN seguros s ON a.seguro_poliza = s.nropoliza
                LEFT JOIN LATERAL (
                    SELECT
                        sub.identificador AS "subastaId",
                        sub.fecha AS "subastaFecha",
                        sub.hora AS "subastaHora",
                        sub.estado AS "subastaEstado"
                    FROM productos p
                    JOIN itemscatalogo ic ON ic.producto = p.identificador
                    JOIN catalogos c ON ic.catalogo = c.identificador
                    JOIN subastas sub ON c.subasta = sub.identificador
                    WHERE p.seguro = a.seguro_poliza
                    ORDER BY
                        CASE sub.estado
                            WHEN 'abierta' THEN 0
                            WHEN 'proxima' THEN 1
                            WHEN 'cerrada' THEN 2
                            ELSE 3
                        END,
                        sub.fecha DESC,
                        sub.hora DESC,
                        sub.identificador DESC
                    LIMIT 1
                ) sub_info ON TRUE
                WHERE a.identificador = %s
                """,
                (id,),
            )
            return ArticuloRepository._row_to_articulo(cursor.fetchone())

    @staticmethod
    def list_articulos_by_owner(db: Connection, duenio_id: int) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.identificador AS id,
                    a.duenio_id AS "duenioId",
                    a.descripcion,
                    a.historia,
                    a.artista,
                    a.fecha_creacion AS "fechaCreacion",
                    a.estado,
                    a.motivo_rechazo AS "motivoRechazo",
                    a.precio_sugerido_usuario AS "precioSugeridoUsuario",
                    a.moneda,
                    a.precio_base_propuesto AS "precioBasePropuesto",
                    a.comision_propuesta AS "comisionPropuesta",
                    a.tasacion_aceptada AS "tasacionAceptada",
                    a.fecha_envio AS "fechaEnvio",
                    a.ubicacion,
                    a.fotos,
                    a.documentacion_origen AS "documentacionOrigen",
                    s.nropoliza AS "seguroPoliza",
                    s.compania AS "seguroCompania",
                    s.importe AS "seguroImporte",
                    sub_info."subastaId",
                    sub_info."subastaFecha",
                    sub_info."subastaHora",
                    sub_info."subastaEstado"
                FROM articulos a
                LEFT JOIN seguros s ON a.seguro_poliza = s.nropoliza
                LEFT JOIN LATERAL (
                    SELECT
                        sub.identificador AS "subastaId",
                        sub.fecha AS "subastaFecha",
                        sub.hora AS "subastaHora",
                        sub.estado AS "subastaEstado"
                    FROM productos p
                    JOIN itemscatalogo ic ON ic.producto = p.identificador
                    JOIN catalogos c ON ic.catalogo = c.identificador
                    JOIN subastas sub ON c.subasta = sub.identificador
                    WHERE p.seguro = a.seguro_poliza
                    ORDER BY
                        CASE sub.estado
                            WHEN 'abierta' THEN 0
                            WHEN 'proxima' THEN 1
                            WHEN 'cerrada' THEN 2
                            ELSE 3
                        END,
                        sub.fecha DESC,
                        sub.hora DESC,
                        sub.identificador DESC
                    LIMIT 1
                ) sub_info ON TRUE
                WHERE a.duenio_id = %s
                ORDER BY a.fecha_envio DESC, a.identificador DESC
                """,
                (duenio_id,),
            )
            return [
                ArticuloRepository._row_to_articulo(row)
                for row in cursor.fetchall()
            ]

    @staticmethod
    def evaluar_articulo(
        db: Connection,
        id: int,
        evaluacion: ArticuloEvaluacion,
    ) -> dict:
        payload = ArticuloRepository._dump_schema(evaluacion)
        estado_value = payload["estado"]
        if hasattr(estado_value, "value"):
            estado_value = estado_value.value

        try:
            with db.cursor() as cursor:
                cursor.execute(
                    "SELECT identificador FROM articulos WHERE identificador = %s",
                    (id,),
                )
                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Articulo no encontrado.",
                    )

                cursor.execute(
                    """
                    UPDATE articulos
                    SET
                        estado = %s,
                        motivo_rechazo = %s,
                        precio_base_propuesto = %s,
                        comision_propuesta = %s
                    WHERE identificador = %s
                    """,
                    (
                        estado_value,
                        payload.get("motivoRechazo"),
                        payload.get("precioBasePropuesto"),
                        payload.get("comisionPropuesta"),
                        id,
                    ),
                )

            db.commit()
            return ArticuloRepository.get_articulo(db, id)
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def aceptar_tasacion(db: Connection, id: int, acepta: bool) -> dict:
        try:
            articulo = ArticuloRepository.get_articulo(db, id)
            if not articulo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Articulo no encontrado.",
                )

            if articulo.get("tasacionAceptada") is True:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La tasacion ya fue aceptada.",
                )

            with db.cursor() as cursor:
                if not acepta:
                    cursor.execute(
                        """
                        UPDATE articulos
                        SET tasacion_aceptada = FALSE, estado = 'devuelto'
                        WHERE identificador = %s
                        """,
                        (id,),
                    )
                    db.commit()
                    return ArticuloRepository.get_articulo(db, id)

                if articulo.get("precioBasePropuesto") is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="El articulo no tiene precio base propuesto.",
                    )

                poliza = f"ART-{id}-{uuid4().hex[:8]}"
                cursor.execute(
                    """
                    INSERT INTO seguros (nropoliza, compania, polizacombinada, importe)
                    VALUES (%s, %s, 'no', %s)
                    RETURNING nropoliza
                    """,
                    (
                        poliza,
                        ArticuloRepository.DEFAULT_COMPANIA_SEGURO,
                        articulo["precioBasePropuesto"],
                    ),
                )
                seguro = cursor.fetchone()

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
                    RETURNING identificador AS "productoId"
                    """,
                    (
                        articulo["descripcion"],
                        articulo["descripcion"],
                        ArticuloRepository.DEFAULT_REVISOR_ID,
                        articulo["duenioId"],
                        seguro["nropoliza"],
                    ),
                )
                producto = cursor.fetchone()

                for foto_url in articulo.get("fotos") or []:
                    cursor.execute(
                        """
                        INSERT INTO fotos_adicionales (producto, foto_url)
                        VALUES (%s, %s)
                        """,
                        (producto["productoId"], str(foto_url)),
                    )

                cursor.execute(
                    """
                    UPDATE articulos
                    SET
                        tasacion_aceptada = TRUE,
                        estado = 'aprobado',
                        seguro_poliza = %s
                    WHERE identificador = %s
                    """,
                    (seguro["nropoliza"], id),
                )

            db.commit()
            result = ArticuloRepository.get_articulo(db, id)
            result["productoId"] = producto["productoId"]
            return result
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def aumentar_seguro(db: Connection, articulo_id: int, monto_nuevo: float) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT seguro_poliza FROM articulos WHERE identificador = %s",
                (articulo_id,),
            )
            row = cursor.fetchone()
            if row and row["seguro_poliza"]:
                cursor.execute(
                    "UPDATE seguros SET importe = %s WHERE nropoliza = %s",
                    (monto_nuevo, row["seguro_poliza"]),
                )

    @staticmethod
    def get_all_pendientes(db: Connection) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.identificador AS id,
                    a.duenio_id AS "duenioId",
                    a.descripcion,
                    a.historia,
                    a.artista,
                    a.fecha_creacion AS "fechaCreacion",
                    a.estado,
                    a.motivo_rechazo AS "motivoRechazo",
                    a.precio_sugerido_usuario AS "precioSugeridoUsuario",
                    a.moneda,
                    a.precio_base_propuesto AS "precioBasePropuesto",
                    a.comision_propuesta AS "comisionPropuesta",
                    a.tasacion_aceptada AS "tasacionAceptada",
                    a.fecha_envio AS "fechaEnvio",
                    a.ubicacion,
                    a.fotos,
                    a.documentacion_origen AS "documentacionOrigen",
                    p.nombre AS duenio_nombre
                FROM articulos a
                JOIN personas p ON a.duenio_id = p.identificador
                WHERE a.estado IN ('pendiente', 'en_inspeccion')
                ORDER BY a.fecha_envio
                """
            )
            return [
                ArticuloRepository._row_to_articulo(row)
                for row in cursor.fetchall()
            ]
