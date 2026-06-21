from fastapi import HTTPException
from psycopg import Connection

from app.repositories.articulo_repo import ArticuloRepository
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.schemas import ArticuloEvaluacion, CatalogoItemInput, SubastaCreate
from app.services.subasta_service import SubastaService


class AdminService:

    @staticmethod
    def verify_payment_method(db: Connection, medio_pago_id: int, estado: str) -> dict:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT cliente_id, estado_verificacion FROM medios_pago WHERE identificador = %s",
                (medio_pago_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Medio de pago no encontrado")

            if row["estado_verificacion"] != "pendiente":
                raise HTTPException(
                    status_code=400, detail="Este medio de pago ya fue verificado"
                )

            cursor.execute(
                "UPDATE medios_pago SET estado_verificacion = %s WHERE identificador = %s",
                (estado, medio_pago_id),
            )
            cursor.execute(
                "INSERT INTO notificaciones (persona_id, tipo, mensaje) VALUES (%s, 'sistema', %s)",
                (
                    row["cliente_id"],
                    f"Tu medio de pago ha sido {estado} por el administrador.",
                ),
            )

        db.commit()
        return {"message": f"Medio de pago {estado} exitosamente."}

    @staticmethod
    def evaluate_article(
        db: Connection, articulo_id: int, data: ArticuloEvaluacion
    ) -> dict:
        articulo = ArticuloRepository.get_articulo(db, articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")

        if articulo["estado"] not in ["pendiente", "en_inspeccion"]:
            raise HTTPException(
                status_code=400, detail="El artículo ya fue evaluado anteriormente"
            )

        if data.estado.value == "rechazado" and not data.motivoRechazo:
            raise HTTPException(
                status_code=400, detail="Debe indicar un motivo de rechazo"
            )

        if data.estado.value == "aprobado" and (
            data.precioBasePropuesto is None or data.comisionPropuesta is None
        ):
            raise HTTPException(
                status_code=400,
                detail="Debe proponer un precio base y comisión para aprobar",
            )

        result = ArticuloRepository.evaluar_articulo(db, articulo_id, data)

        with db.cursor() as cursor:
            mensaje = f"Tu artículo #{articulo_id} fue {data.estado.value}."
            if data.estado.value == "aprobado":
                mensaje += (
                    f" Precio propuesto: ${data.precioBasePropuesto}. "
                    f"Comisión: {data.comisionPropuesta}%."
                )
            else:
                mensaje += f" Motivo: {data.motivoRechazo}"

            cursor.execute(
                "INSERT INTO notificaciones (persona_id, tipo, mensaje) VALUES (%s, 'sistema', %s)",
                (articulo["duenioId"], mensaje),
            )

        db.commit()
        return result

    @staticmethod
    def create_auction(
        db: Connection, data: SubastaCreate, usuario_id: int | None
    ) -> dict:
        return SubastaService.create_subasta(db, data, usuario_id)

    @staticmethod
    def add_catalog_item(
        db: Connection,
        subasta_id: int,
        data: CatalogoItemInput,
        usuario_id: int | None,
    ) -> dict:
        return SubastaService.add_catalog_item(db, subasta_id, data, usuario_id)

    @staticmethod
    def get_pending_users(db: Connection) -> list[dict]:
        return UsuarioRepository.get_pending_registrations(db)

    @staticmethod
    def get_all_users(db: Connection) -> list[dict]:
        return UsuarioRepository.get_all_users(db)

    @staticmethod
    def update_user_category(db: Connection, usuario_id: int, categoria: str) -> dict:
        UsuarioRepository.update_user_category(db, usuario_id, categoria)
        return {"message": f"Categoría del usuario actualizada a {categoria} exitosamente."}

    @staticmethod
    def get_pending_articles(db: Connection) -> list[dict]:
        return ArticuloRepository.get_all_pendientes(db)

    @staticmethod
    def get_pending_payment_methods(db: Connection) -> list[dict]:
        query = """
            SELECT 
                m.identificador as id,
                m.cliente_id as "clienteId",
                m.tipo,
                m.ultimos_digitos as "ultimosDigitos",
                m.estado_verificacion as "estadoVerificacion",
                m.moneda,
                m.limite_reservado as "limiteReservado",
                m.pais_banco as "paisBanco",
                m.es_cuenta_receptora as "esCuentaReceptora",
                p.nombre as "clienteNombre"
            FROM medios_pago m
            JOIN personas p ON m.cliente_id = p.identificador
            WHERE m.estado_verificacion = 'pendiente'
            ORDER BY m.identificador ASC
        """
        with db.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_all_subastadores(db: Connection) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    s.identificador AS id, 
                    p.nombre, 
                    p.apellido, 
                    s.matricula, 
                    s.region
                FROM subastadores s
                JOIN personas p ON s.identificador = p.identificador
                ORDER BY p.apellido, p.nombre
                """
            )
            return cursor.fetchall()

    @staticmethod
    def get_approved_non_cataloged_articles(db: Connection) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    a.identificador AS id, 
                    a.descripcion, 
                    a.precio_base_propuesto AS "precioBasePropuesto", 
                    a.comision_propuesta AS "comisionPropuesta"
                FROM articulos a
                LEFT JOIN productos p ON p.seguro = a.seguro_poliza
                LEFT JOIN itemscatalogo ic ON ic.producto = p.identificador
                WHERE a.estado = 'aprobado' 
                  AND a.tasacion_aceptada = TRUE 
                  AND ic.identificador IS NULL
                ORDER BY a.fecha_envio DESC
                """
            )
            return cursor.fetchall()
