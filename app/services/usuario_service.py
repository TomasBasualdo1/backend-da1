from fastapi import HTTPException, UploadFile, status
from psycopg import Connection
from psycopg.rows import dict_row

from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.schemas import MedioPagoInput, MedioPagoUpdate
from app.services.storage_service import StorageService
from app.services.subasta_service import SubastaService

class UsuarioService:
    @staticmethod
    def _extract_last_digits(payment_data: str) -> str:
        ultimos_digitos = "4321"
        if payment_data:
            digits = [c for c in payment_data if c.isdigit()]
            if len(digits) >= 4:
                ultimos_digitos = "".join(digits[-4:])
            else:
                ultimos_digitos = payment_data[-4:]
        return ultimos_digitos

    @staticmethod
    def get_profile(db: Connection, usuario_id: int) -> dict:
        query = """
            SELECT 
                p.identificador as id,
                p.documento,
                p.nombre,
                pa.email,
                p.direccion,
                pa.telefono,
                pa.foto_url as foto,
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
            WHERE p.identificador = %s
        """
        with db.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (usuario_id,))
            user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
            
        # Split the full name into nombre and apellido
        nombre_completo = user["nombre"] or ""
        name_parts = nombre_completo.split(" ", 1)
        if len(name_parts) == 2:
            user["nombre"] = name_parts[0]
            user["apellido"] = name_parts[1]
        else:
            user["apellido"] = ""
            
        return user

    @staticmethod
    async def update_profile(
        db: Connection,
        usuario_id: int,
        nombre: str | None = None,
        apellido: str | None = None,
        direccion: str | None = None,
        telefono: str | None = None,
        foto: UploadFile | None = None,
    ) -> dict:
        person = UsuarioRepository.get_person_for_profile_update(db, usuario_id)
        if not person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        current_full_name = person["nombre"] or ""
        parts = current_full_name.split(" ", 1)
        curr_nombre = parts[0]
        curr_apellido = parts[1] if len(parts) > 1 else ""

        new_nombre = nombre if nombre is not None else curr_nombre
        new_apellido = apellido if apellido is not None else curr_apellido
        new_full_name = f"{new_nombre} {new_apellido}".strip()

        UsuarioRepository.update_profile_person(
            db,
            usuario_id,
            nombre_completo=new_full_name,
            direccion=direccion,
        )

        foto_url = None
        if foto:
            foto_bytes = await foto.read()
            foto_url = StorageService.upload_file(
                foto_bytes,
                f"profile/{usuario_id}/photo.jpg",
                foto.content_type or "image/jpeg",
            )

        UsuarioRepository.update_profile_additional(
            db,
            usuario_id,
            telefono=telefono,
            foto_url=foto_url,
        )
        db.commit()
        return {"message": "Perfil actualizado correctamente"}

    @staticmethod
    def delete_profile_picture(db: Connection, usuario_id: int) -> dict:
        UsuarioRepository.clear_profile_picture(db, usuario_id)
        db.commit()
        return {"message": "Foto de perfil eliminada correctamente"}

    @staticmethod
    def list_payment_methods(db: Connection, usuario_id: int) -> list[dict]:
        return UsuarioRepository.list_payment_methods(db, usuario_id)

    @staticmethod
    def add_payment_method(
        db: Connection, usuario_id: int, body: MedioPagoInput
    ) -> dict:
        UsuarioRepository.create_payment_method(
            db,
            usuario_id=usuario_id,
            tipo=body.tipo.value,
            datos_encriptados=body.datos_encriptados,
            ultimos_digitos=UsuarioService._extract_last_digits(
                body.datos_encriptados
            ),
            moneda=body.moneda.value,
            limite_reservado=body.limiteReservado or 0.00,
            pais_banco=body.paisBanco,
            es_cuenta_receptora=body.esCuentaReceptora or False,
        )
        db.commit()
        return {"message": "Medio de pago agregado correctamente"}

    @staticmethod
    def update_payment_method(
        db: Connection, usuario_id: int, payment_method_id: int, body: MedioPagoUpdate
    ) -> dict:
        if not UsuarioRepository.payment_method_belongs_to_user(
            db, usuario_id, payment_method_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medio de pago no encontrado",
            )

        fields = {}
        if body.limiteReservado is not None:
            fields["limite_reservado"] = body.limiteReservado
        if body.esCuentaReceptora is not None:
            fields["es_cuenta_receptora"] = body.esCuentaReceptora

        if not fields:
            return {"message": "No se realizaron cambios"}

        UsuarioRepository.update_payment_method(db, payment_method_id, fields)
        db.commit()
        return {"message": "Medio de pago actualizado"}

    @staticmethod
    def delete_payment_method(
        db: Connection, usuario_id: int, payment_method_id: int
    ) -> None:
        if not UsuarioRepository.payment_method_belongs_to_user(
            db, usuario_id, payment_method_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medio de pago no encontrado",
            )

        UsuarioRepository.delete_payment_method(db, payment_method_id)
        db.commit()

    @staticmethod
    def get_metrics(db: Connection, usuario_id: int) -> dict:
        return UsuarioRepository.get_metrics(db, usuario_id)

    @staticmethod
    def list_multas(db: Connection, usuario_id: int) -> list[dict]:
        SubastaService.procesar_vencimientos(db, usuario_id)
        return UsuarioRepository.get_multas(db, usuario_id)

    @staticmethod
    def pagar_multa(db: Connection, usuario_id: int, multa_id: int, medio_pago_id: int):
        SubastaService.procesar_vencimientos(db, usuario_id)

        try:
            multa = UsuarioRepository.get_multa_para_cliente(db, usuario_id, multa_id)
            if not multa:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Multa no encontrada",
                )

            if multa["estado"] != "pendiente":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="La multa no se encuentra pendiente",
                )

            medio = UsuarioRepository.get_medio_pago_para_cliente(
                db, usuario_id, medio_pago_id
            )
            if not medio:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Medio de pago no autorizado para este usuario",
                )

            if medio["estado_verificacion"] != "validado":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Medio de pago no validado",
                )

            limite_reservado = float(medio["limite_reservado"] or 0.0)
            if limite_reservado > 0 and limite_reservado < float(multa["importe"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Fondos insuficientes",
                )

            UsuarioRepository.pagar_multa(db, multa_id, medio_pago_id)

            if not UsuarioRepository.tiene_multas_pendientes(db, usuario_id):
                UsuarioRepository.set_multa_activa(db, usuario_id, False)

            UsuarioRepository.crear_notificacion(
                db,
                usuario_id,
                "pago",
                f"Multa #{multa_id} pagada correctamente.",
            )
            db.commit()
            return {"message": "Multa pagada correctamente"}
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise
