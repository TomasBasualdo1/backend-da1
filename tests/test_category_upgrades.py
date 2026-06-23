import asyncio
import unittest
from unittest.mock import MagicMock, patch

from app.services.category_service import CATEGORY_RANK, CategoryService


class TestDetermineCategory(unittest.TestCase):
    """Tests puros de logica de _determine_category (no requieren DB)."""

    def test_comun_default(self):
        self.assertEqual(CategoryService._determine_category(0, 0, 0), "comun")
        self.assertEqual(CategoryService._determine_category(1, 0, 0), "comun")

    def test_especial_2_types_no_activity(self):
        self.assertEqual(CategoryService._determine_category(2, 0, 0), "especial")

    def test_plata_2_types_5_participaciones(self):
        self.assertEqual(CategoryService._determine_category(2, 5, 0), "plata")
        self.assertEqual(CategoryService._determine_category(2, 10, 0), "plata")

    def test_oro_3_types_10_participaciones_1_ganada(self):
        self.assertEqual(CategoryService._determine_category(3, 10, 1), "oro")
        self.assertEqual(CategoryService._determine_category(3, 14, 2), "oro")

    def test_oro_not_enough_ganadas(self):
        # 3 types, 10 participations, but 0 wins => should be plata
        self.assertEqual(CategoryService._determine_category(3, 10, 0), "plata")

    def test_platino_3_types_15_participaciones_3_ganadas(self):
        self.assertEqual(CategoryService._determine_category(3, 15, 3), "platino")
        self.assertEqual(CategoryService._determine_category(3, 20, 5), "platino")

    def test_platino_not_enough_ganadas(self):
        # 3 types, 15 participations, but only 2 wins => oro
        self.assertEqual(CategoryService._determine_category(3, 15, 2), "oro")

    def test_3_types_no_participations_downgrades_to_especial(self):
        # 3 types, but no participations => especial (no plata porque falta actividad)
        self.assertEqual(CategoryService._determine_category(3, 0, 0), "especial")


class TestEvaluateAndUpgrade(unittest.TestCase):
    """Tests de evaluate_and_upgrade con DB mockeada."""

    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.cursor.return_value.__enter__.return_value = self.mock_cursor

    def test_user_not_found_returns_comun_no_upgrade(self):
        self.mock_cursor.fetchone.return_value = None
        result = CategoryService.evaluate_and_upgrade(self.mock_db, 999)
        self.assertEqual(result["categoriaAnterior"], "comun")
        self.assertEqual(result["categoriaNueva"], "comun")
        self.assertFalse(result["upgraded"])

    def test_no_upgrade_when_already_max_category(self):
        # Simulate user at platino with max stats
        self.mock_cursor.fetchone.side_effect = [
            {"categoria": "platino"},                    # get_user_category
            None,                                         # get_validated_payment_diversity -> MagicMock or None
            {"totalSubastasParticipadas": 15, "totalSubastasGanadas": 5},  # get_metrics fake
        ]
        # get_metrics also queries "total_pujas" etc, so need to mock all fetchone calls...
        # This is getting complex. Let me use a more targeted approach with patch.
        pass

    def test_upgrade_comun_to_especial_with_2_validated_types(self):
        with (
            patch("app.services.category_service.UsuarioRepository.get_user_category") as mock_get_cat,
            patch("app.services.category_service.UsuarioRepository.get_validated_payment_diversity") as mock_get_div,
            patch("app.services.category_service.UsuarioRepository.get_metrics") as mock_get_met,
            patch("app.services.category_service.UsuarioRepository.update_user_category") as mock_upd,
            patch("app.services.category_service.UsuarioRepository.crear_notificacion") as mock_notif,
        ):
            mock_get_cat.return_value = "comun"
            mock_get_div.return_value = 2
            mock_get_met.return_value = {
                "totalSubastasParticipadas": 0,
                "totalSubastasGanadas": 0,
            }

            result = CategoryService.evaluate_and_upgrade(self.mock_db, 1)

            self.assertTrue(result["upgraded"])
            self.assertEqual(result["categoriaAnterior"], "comun")
            self.assertEqual(result["categoriaNueva"], "especial")
            mock_upd.assert_called_once_with(self.mock_db, 1, "especial")
            mock_notif.assert_called_once()

    def test_upgrade_comun_to_plata_with_2_types_and_5_participaciones(self):
        with (
            patch("app.services.category_service.UsuarioRepository.get_user_category") as mock_get_cat,
            patch("app.services.category_service.UsuarioRepository.get_validated_payment_diversity") as mock_get_div,
            patch("app.services.category_service.UsuarioRepository.get_metrics") as mock_get_met,
            patch("app.services.category_service.UsuarioRepository.update_user_category") as mock_upd,
            patch("app.services.category_service.UsuarioRepository.crear_notificacion") as mock_notif,
        ):
            mock_get_cat.return_value = "comun"
            mock_get_div.return_value = 2
            mock_get_met.return_value = {
                "totalSubastasParticipadas": 5,
                "totalSubastasGanadas": 0,
            }

            result = CategoryService.evaluate_and_upgrade(self.mock_db, 1)

            self.assertTrue(result["upgraded"])
            self.assertEqual(result["categoriaAnterior"], "comun")
            self.assertEqual(result["categoriaNueva"], "plata")
            mock_upd.assert_called_once_with(self.mock_db, 1, "plata")
            mock_notif.assert_called_once()

    def test_upgrade_especial_to_oro_with_3_types_10_participaciones_1_win(self):
        with (
            patch("app.services.category_service.UsuarioRepository.get_user_category") as mock_get_cat,
            patch("app.services.category_service.UsuarioRepository.get_validated_payment_diversity") as mock_get_div,
            patch("app.services.category_service.UsuarioRepository.get_metrics") as mock_get_met,
            patch("app.services.category_service.UsuarioRepository.update_user_category") as mock_upd,
            patch("app.services.category_service.UsuarioRepository.crear_notificacion") as mock_notif,
        ):
            mock_get_cat.return_value = "especial"
            mock_get_div.return_value = 3
            mock_get_met.return_value = {
                "totalSubastasParticipadas": 10,
                "totalSubastasGanadas": 1,
            }

            result = CategoryService.evaluate_and_upgrade(self.mock_db, 1)

            self.assertTrue(result["upgraded"])
            self.assertEqual(result["categoriaAnterior"], "especial")
            self.assertEqual(result["categoriaNueva"], "oro")
            mock_upd.assert_called_once_with(self.mock_db, 1, "oro")
            mock_notif.assert_called_once()

    def test_upgrade_oro_to_platino_with_3_types_15_participaciones_3_wins(self):
        with (
            patch("app.services.category_service.UsuarioRepository.get_user_category") as mock_get_cat,
            patch("app.services.category_service.UsuarioRepository.get_validated_payment_diversity") as mock_get_div,
            patch("app.services.category_service.UsuarioRepository.get_metrics") as mock_get_met,
            patch("app.services.category_service.UsuarioRepository.update_user_category") as mock_upd,
            patch("app.services.category_service.UsuarioRepository.crear_notificacion") as mock_notif,
        ):
            mock_get_cat.return_value = "oro"
            mock_get_div.return_value = 3
            mock_get_met.return_value = {
                "totalSubastasParticipadas": 15,
                "totalSubastasGanadas": 3,
            }

            result = CategoryService.evaluate_and_upgrade(self.mock_db, 1)

            self.assertTrue(result["upgraded"])
            self.assertEqual(result["categoriaAnterior"], "oro")
            self.assertEqual(result["categoriaNueva"], "platino")
            mock_upd.assert_called_once_with(self.mock_db, 1, "platino")
            mock_notif.assert_called_once()

    def test_no_downgrade_when_manually_promoted(self):
        # Admin manually set to oro, but user only has 2 payment types => no downgrade
        with (
            patch("app.services.category_service.UsuarioRepository.get_user_category") as mock_get_cat,
            patch("app.services.category_service.UsuarioRepository.get_validated_payment_diversity") as mock_get_div,
            patch("app.services.category_service.UsuarioRepository.get_metrics") as mock_get_met,
            patch("app.services.category_service.UsuarioRepository.update_user_category") as mock_upd,
            patch("app.services.category_service.UsuarioRepository.crear_notificacion") as mock_notif,
        ):
            mock_get_cat.return_value = "oro"
            mock_get_div.return_value = 2
            mock_get_met.return_value = {
                "totalSubastasParticipadas": 3,
                "totalSubastasGanadas": 0,
            }

            result = CategoryService.evaluate_and_upgrade(self.mock_db, 1)

            self.assertFalse(result["upgraded"])
            self.assertEqual(result["categoriaAnterior"], "oro")
            self.assertEqual(result["categoriaNueva"], "oro")
            mock_upd.assert_not_called()
            mock_notif.assert_not_called()

    def test_user_already_at_suggested_category_no_change(self):
        with (
            patch("app.services.category_service.UsuarioRepository.get_user_category") as mock_get_cat,
            patch("app.services.category_service.UsuarioRepository.get_validated_payment_diversity") as mock_get_div,
            patch("app.services.category_service.UsuarioRepository.get_metrics") as mock_get_met,
            patch("app.services.category_service.UsuarioRepository.update_user_category") as mock_upd,
            patch("app.services.category_service.UsuarioRepository.crear_notificacion") as mock_notif,
        ):
            mock_get_cat.return_value = "plata"
            mock_get_div.return_value = 2
            mock_get_met.return_value = {
                "totalSubastasParticipadas": 5,
                "totalSubastasGanadas": 0,
            }

            result = CategoryService.evaluate_and_upgrade(self.mock_db, 1)

            self.assertFalse(result["upgraded"])
            self.assertEqual(result["categoriaAnterior"], "plata")
            self.assertEqual(result["categoriaNueva"], "plata")
            mock_upd.assert_not_called()
            mock_notif.assert_not_called()

    def test_exception_during_evaluation_returns_no_upgrade(self):
        with patch("app.services.category_service.UsuarioRepository.get_user_category") as mock_get_cat:
            mock_get_cat.side_effect = Exception("DB connection error")

            result = CategoryService.evaluate_and_upgrade(self.mock_db, 1)

            self.assertFalse(result["upgraded"])
            self.assertIn("Error al evaluar categor", result["motivo"])


class TestCategoryRank(unittest.TestCase):
    """Verifica que los rangos sean correctos y esten en orden ascendente."""

    def test_rank_values(self):
        self.assertEqual(CATEGORY_RANK["comun"], 0)
        self.assertEqual(CATEGORY_RANK["especial"], 1)
        self.assertEqual(CATEGORY_RANK["plata"], 2)
        self.assertEqual(CATEGORY_RANK["oro"], 3)
        self.assertEqual(CATEGORY_RANK["platino"], 4)

    def test_rank_ordering(self):
        self.assertLess(CATEGORY_RANK["comun"], CATEGORY_RANK["especial"])
        self.assertLess(CATEGORY_RANK["especial"], CATEGORY_RANK["plata"])
        self.assertLess(CATEGORY_RANK["plata"], CATEGORY_RANK["oro"])
        self.assertLess(CATEGORY_RANK["oro"], CATEGORY_RANK["platino"])
