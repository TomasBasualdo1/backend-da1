import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from main import app
from app.dependencies import get_current_user, get_db

class TestUsuariosApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
        # Mock current user dependency
        self.mock_user = {"usuarioId": 123, "documento": "12345678"}
        app.dependency_overrides[get_current_user] = lambda: self.mock_user

        # Mock database connection and cursor dependency
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.cursor.return_value.__enter__.return_value = self.mock_cursor
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_delete_profile_picture(self):
        response = self.client.delete("/usuarios/me/foto")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Foto de perfil eliminada correctamente"})
        
        # Verify the database update query was executed with correct arguments
        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE personas_adicionales SET foto_url = NULL WHERE identificador = %s",
            (123,)
        )
        self.mock_db.commit.assert_called_once()

if __name__ == "__main__":
    unittest.main()
