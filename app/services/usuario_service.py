from fastapi import HTTPException, status
from psycopg import Connection
from psycopg.rows import dict_row

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
