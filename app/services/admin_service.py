from fastapi import HTTPException
from psycopg import Connection
from app.repositories.articulo_repo import ArticuloRepository
from app.schemas.schemas import SubastaCreate, CatalogoItemInput, ArticuloEvaluacion


class AdminService:

    @staticmethod
    def verify_payment_method(db: Connection, medio_pago_id: int, estado: str) -> dict:
        with db.cursor() as cursor:
            cursor.execute("SELECT cliente_id, estado_verificacion FROM medios_pago WHERE identificador = %s", (medio_pago_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Medio de pago no encontrado")

            if row["estado_verificacion"] != "pendiente":
                raise HTTPException(status_code=400, detail="Este medio de pago ya fue verificado")

            cursor.execute(
                "UPDATE medios_pago SET estado_verificacion = %s WHERE identificador = %s",
                (estado, medio_pago_id),
            )
            
            # Send notification
            cursor.execute(
                "INSERT INTO notificaciones (persona_id, tipo, mensaje) VALUES (%s, 'sistema', %s)",
                (row["cliente_id"], f"Tu medio de pago ha sido {estado} por el administrador."),
            )

        db.commit()
        return {"message": f"Medio de pago {estado} exitosamente."}

    @staticmethod
    def evaluate_article(db: Connection, articulo_id: int, data: ArticuloEvaluacion) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")

        if articulo["estado"] not in ["pendiente", "en_inspeccion"]:
            raise HTTPException(status_code=400, detail="El artículo ya fue evaluado anteriormente")

        if data.estado.value == "rechazado" and not data.motivoRechazo:
            raise HTTPException(status_code=400, detail="Debe indicar un motivo de rechazo")

        if data.estado.value == "aprobado":
            if data.precioBasePropuesto is None or data.comisionPropuesta is None:
                raise HTTPException(status_code=400, detail="Debe proponer un precio base y comisión para aprobar")
            
        ArticuloRepository.evaluar_articulo(
            db=db,
            articulo_id=articulo_id,
            estado=data.estado.value,
            motivo_rechazo=data.motivoRechazo,
            precio_base=data.precioBasePropuesto,
            comision=data.comisionPropuesta,
        )

        with db.cursor() as cursor:
            mensaje = f"Tu artículo #{articulo_id} fue {data.estado.value}."
            if data.estado.value == "aprobado":
                mensaje += f" Precio propuesto: ${data.precioBasePropuesto}. Comisión: {data.comisionPropuesta}%."
            else:
                mensaje += f" Motivo: {data.motivoRechazo}"

            cursor.execute(
                "INSERT INTO notificaciones (persona_id, tipo, mensaje) VALUES (%s, 'sistema', %s)",
                (articulo["duenio_id"], mensaje),
            )

        db.commit()
        return {"message": f"Artículo evaluado como {data.estado.value}."}

    @staticmethod
    def create_auction(db: Connection, data: SubastaCreate) -> dict:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO subastas (
                    fecha, hora, estado, categoria, subastador, 
                    ubicacion, capacidad_asistentes, tiene_deposito, seguridad_propia
                ) VALUES (%s, %s, 'abierta', %s, %s, %s, %s, %s, %s)
                RETURNING identificador
                """,
                (
                    data.fecha,
                    data.hora,
                    data.categoria.value,
                    data.subastadorId,
                    data.ubicacion,
                    data.capacidadAsistentes,
                    data.tieneDeposito or False,
                    data.seguridadPropia or False,
                ),
            )
            subasta_id = cursor.fetchone()["identificador"]

            # Crear un catalogo para la subasta
            cursor.execute(
                "INSERT INTO catalogos (subasta, descripcion) VALUES (%s, %s) RETURNING identificador",
                (subasta_id, f"Catálogo de Subasta #{subasta_id}"),
            )

        db.commit()
        return {"id": subasta_id, "message": "Subasta y catálogo creados exitosamente"}

    @staticmethod
    def add_catalog_item(db: Connection, subasta_id: int, data: CatalogoItemInput) -> dict:
        with db.cursor() as cursor:
            cursor.execute("SELECT identificador FROM catalogos WHERE subasta = %s", (subasta_id,))
            catalogo = cursor.fetchone()
            if not catalogo:
                raise HTTPException(status_code=404, detail="Catálogo de subasta no encontrado")

            producto_id = data.productoId
            if data.articuloId:
                # Si se envia un articulo (consignado), validar que este aprobado y tasacion aceptada
                cursor.execute(
                    "SELECT estado, tasacion_aceptada, descripcion, duenio_id FROM articulos WHERE identificador = %s",
                    (data.articuloId,),
                )
                articulo = cursor.fetchone()
                if not articulo:
                    raise HTTPException(status_code=404, detail="Artículo no encontrado")
                if articulo["estado"] != "aprobado" or not articulo["tasacion_aceptada"]:
                    raise HTTPException(status_code=400, detail="El artículo debe estar aprobado y la tasación aceptada por el dueño")

                # Insertar en productos si no existía (simplificado, se crea uno basado en el articulo)
                cursor.execute(
                    "INSERT INTO productos (descripcioncompleta, duenio) VALUES (%s, %s) RETURNING identificador",
                    (articulo["descripcion"], articulo["duenio_id"]),
                )
                producto_id = cursor.fetchone()["identificador"]

            if not producto_id:
                raise HTTPException(status_code=400, detail="Debe proveer productoId o articuloId")

            cursor.execute(
                """
                INSERT INTO itemscatalogo (catalogo, producto, preciobase, comision, subastado)
                VALUES (%s, %s, %s, %s, 'no')
                RETURNING identificador
                """,
                (catalogo["identificador"], producto_id, data.precioBase, data.comision),
            )
            item_id = cursor.fetchone()["identificador"]

        db.commit()
        return {"id": item_id, "message": "Ítem agregado al catálogo exitosamente"}
