from psycopg import Connection

from app.repositories.usuario_repo import UsuarioRepository

CATEGORY_RANK = {"comun": 0, "especial": 1, "plata": 2, "oro": 3, "platino": 4}


class CategoryService:

    @staticmethod
    def evaluate_and_upgrade(db: Connection, usuario_id: int) -> dict:
        try:
            return CategoryService._evaluate_and_upgrade_impl(db, usuario_id)
        except Exception as e:
            return {
                "categoriaAnterior": "comun",
                "categoriaNueva": "comun",
                "motivo": f"Error al evaluar categoría: {e}",
                "upgraded": False,
            }

    @staticmethod
    def _evaluate_and_upgrade_impl(db: Connection, usuario_id: int) -> dict:
        current_category = UsuarioRepository.get_user_category(db, usuario_id)
        if not current_category:
            return {
                "categoriaAnterior": "comun",
                "categoriaNueva": "comun",
                "motivo": "Usuario no encontrado",
                "upgraded": False,
            }

        diversity = UsuarioRepository.get_validated_payment_diversity(db, usuario_id)
        metrics = UsuarioRepository.get_metrics(db, usuario_id)
        participaciones = metrics["totalSubastasParticipadas"] or 0
        ganadas = metrics["totalSubastasGanadas"] or 0

        suggested_category = CategoryService._determine_category(
            diversity, participaciones, ganadas
        )

        current_rank = CATEGORY_RANK.get(current_category, 0)
        suggested_rank = CATEGORY_RANK.get(suggested_category, 0)

        if suggested_rank <= current_rank:
            return {
                "categoriaAnterior": current_category,
                "categoriaNueva": current_category,
                "motivo": (
                    f"El usuario ya tiene categoría '{current_category}' "
                    f"(rango {current_rank}) >= '{suggested_category}' (rango {suggested_rank}). "
                    f"Diversidad de pagos: {diversity}, participaciones: {participaciones}, "
                    f"ganadas: {ganadas}."
                ),
                "upgraded": False,
            }

        UsuarioRepository.update_user_category(db, usuario_id, suggested_category)
        UsuarioRepository.crear_notificacion(
            db,
            usuario_id,
            "sistema",
            (
                f"Tu categoría ha sido mejorada automáticamente de '{current_category}' "
                f"a '{suggested_category}' por tu diversidad de medios de pago ({diversity} tipos validados) "
                f"y tu actividad en subastas ({participaciones} participaciones, {ganadas} ganadas)."
            ),
        )

        return {
            "categoriaAnterior": current_category,
            "categoriaNueva": suggested_category,
            "motivo": (
                f"Upgrade de '{current_category}' a '{suggested_category}'. "
                f"Diversidad de pagos: {diversity}, participaciones: {participaciones}, "
                f"ganadas: {ganadas}."
            ),
            "upgraded": True,
        }

    @staticmethod
    def _determine_category(
        diversity: int, participaciones: int, ganadas: int
    ) -> str:
        if diversity >= 3 and participaciones >= 15 and ganadas >= 3:
            return "platino"
        if diversity >= 3 and participaciones >= 10 and ganadas >= 1:
            return "oro"
        if diversity >= 2 and participaciones >= 5:
            return "plata"
        if diversity >= 2:
            return "especial"
        return "comun"
