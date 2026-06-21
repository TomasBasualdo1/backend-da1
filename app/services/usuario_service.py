from fastapi import HTTPException, status
from psycopg import Connection
from psycopg.rows import dict_row

from app.repositories.usuario_repo import UsuarioRepository
from app.services.subasta_service import SubastaService

class UsuarioService:
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
