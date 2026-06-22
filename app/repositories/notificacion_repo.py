from psycopg import Connection


class NotificacionRepository:
    @staticmethod
    def list_for_user(db: Connection, usuario_id: int) -> list[dict]:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    identificador as id,
                    tipo,
                    mensaje,
                    fecha_hora as "fechaHora",
                    leida
                FROM notificaciones
                WHERE persona_id = %s
                ORDER BY fecha_hora DESC
                """,
                (usuario_id,),
            )
            return cursor.fetchall()

    @staticmethod
    def exists_for_user(db: Connection, notificacion_id: int, usuario_id: int) -> bool:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM notificaciones WHERE identificador = %s AND persona_id = %s",
                (notificacion_id, usuario_id),
            )
            return bool(cursor.fetchone())

    @staticmethod
    def mark_read(db: Connection, notificacion_id: int) -> None:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE notificaciones SET leida = true WHERE identificador = %s",
                (notificacion_id,),
            )
