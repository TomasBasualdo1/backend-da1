import asyncio
import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.api.usuarios import delete_profile_picture, get_profile

class TestUsuariosApi(unittest.TestCase):
    def setUp(self):
        self.mock_user = {"usuarioId": 123, "documento": "12345678"}
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.cursor.return_value.__enter__.return_value = self.mock_cursor

    def test_delete_profile_picture(self):
        response = asyncio.run(
            delete_profile_picture(db=self.mock_db, user=self.mock_user)
        )

        self.assertEqual(response, {"message": "Foto de perfil eliminada correctamente"})

        # Verify the database update query was executed with correct arguments
        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE personas_adicionales SET foto_url = NULL WHERE identificador = %s",
            (123,)
        )
        self.mock_db.commit.assert_called_once()

    def test_get_profile_success(self):
        self.mock_cursor.fetchone.return_value = {
            "id": 123,
            "documento": "12345678",
            "nombre": "Juan Carlos Perez",
            "email": "juan@example.com",
            "direccion": "Av. Corrientes 1234",
            "telefono": "+54 11 5555-5555",
            "foto": "http://example.com/avatar.jpg",
            "numeroPais": 1,
            "admitido": "si",
            "estadoRegistro": "aprobado",
            "categoria": "comun",
            "multaActiva": False,
            "bloqueado": False
        }

        response = asyncio.run(get_profile(db=self.mock_db, user=self.mock_user))

        self.assertEqual(response.id, 123)
        self.assertEqual(response.nombre, "Juan")
        self.assertEqual(response.apellido, "Carlos Perez")
        self.assertEqual(response.admitido.value, "si")
        self.assertEqual(response.telefono, "+54 11 5555-5555")

        executed_sql = self.mock_cursor.execute.call_args.args[0]
        self.assertIn("WHERE p.identificador = %s", executed_sql)
        self.assertEqual(self.mock_cursor.execute.call_args.args[1], (123,))

    def test_get_profile_not_found(self):
        self.mock_cursor.fetchone.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_profile(db=self.mock_db, user=self.mock_user))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Usuario no encontrado")

if __name__ == "__main__":
    unittest.main()
