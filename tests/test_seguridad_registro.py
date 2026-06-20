import asyncio
import unittest
from datetime import date, time, timedelta
from unittest.mock import ANY, MagicMock, patch

from fastapi import HTTPException

from app.api.admin import (
    add_catalog_item,
    create_auction,
    verify_payment_method,
    verify_user,
)
from app.api.auth import registro_paso1
from app.api.subastas import close_auction
from app.repositories.usuario_repo import UsuarioRepository
from app.schemas.schemas import (
    CatalogoItemInput,
    MedioPagoVerificacion,
    SubastaCreate,
    UsuarioVerificacion,
)
from app.services.auth_service import AuthService


class FakeUpload:
    content_type = "image/jpeg"

    def __init__(self, content: bytes):
        self.content = content

    async def read(self):
        return self.content


def make_db(fetchone_value=None):
    db = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_value
    db.cursor.return_value.__enter__.return_value = cursor
    return db, cursor


class TestRegistroPendiente(unittest.TestCase):
    @patch("app.api.auth.EmailService.send_verification_email")
    @patch("app.api.auth.UsuarioRepository.aprobar_registro")
    @patch("app.api.auth.UsuarioRepository.create_cliente_pendiente", return_value=55)
    @patch(
        "app.api.auth.StorageService.upload_file",
        side_effect=["https://storage/frente.jpg", "https://storage/dorso.jpg"],
    )
    @patch("app.api.auth.UsuarioRepository.check_duplicate")
    def test_registro_paso1_deja_pendiente_y_no_autoaprueba(
        self,
        check_duplicate,
        upload_file,
        create_cliente_pendiente,
        aprobar_registro,
        send_verification_email,
    ):
        result = asyncio.run(
            registro_paso1(
                documento="35123456",
                nombre="Juan",
                apellido="Perez",
                email="juan@example.com",
                direccion="Av Corrientes 1234",
                numeroPais=1,
                telefono=None,
                fotoFrente=FakeUpload(b"frente"),
                fotoDorso=FakeUpload(b"dorso"),
                db=MagicMock(),
            )
        )

        self.assertIn("Solicitud de registro recibida", result["message"])
        check_duplicate.assert_called_once_with(ANY, "35123456", "juan@example.com")
        self.assertEqual(upload_file.call_count, 2)
        create_cliente_pendiente.assert_called_once()
        aprobar_registro.assert_not_called()
        send_verification_email.assert_not_called()

    @patch("app.services.auth_service.verify_password", return_value=True)
    def test_login_usuario_pendiente_devuelve_403(self, verify_password):
        db, _ = make_db(
            {
                "usuario_id": 55,
                "documento": "35123456",
                "nombre": "Juan Perez",
                "password_hash": "hash",
                "admitido": "no",
                "categoria": "comun",
                "estadoRegistro": "pendiente",
                "bloqueado": False,
                "multaActiva": False,
            }
        )

        with self.assertRaises(HTTPException) as ctx:
            AuthService.login(db, "35123456", "secret")

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "User registration not approved")


class TestAdminGuards(unittest.TestCase):
    def setUp(self):
        self.normal_user = {"usuarioId": 2, "documento": "222"}
        self.admin_user = {"usuarioId": 1, "documento": "1"}

    def test_usuario_comun_no_puede_verificar_usuarios(self):
        with patch("app.api.admin.UsuarioRepository.aprobar_registro") as aprobar:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    verify_user(
                        55,
                        UsuarioVerificacion(admitido=True, categoria="comun"),
                        MagicMock(),
                        self.normal_user,
                    )
                )

        self.assertEqual(ctx.exception.status_code, 403)
        aprobar.assert_not_called()

    def test_usuario_comun_no_puede_verificar_medios_pago(self):
        with patch("app.api.admin.AdminService.verify_payment_method") as verify_payment:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    verify_payment_method(
                        9,
                        MedioPagoVerificacion(estadoVerificacion="validado"),
                        MagicMock(),
                        self.normal_user,
                    )
                )

        self.assertEqual(ctx.exception.status_code, 403)
        verify_payment.assert_not_called()

    def test_usuario_comun_no_puede_crear_subastas(self):
        body = SubastaCreate(
            fecha=date.today() + timedelta(days=20),
            hora=time(10, 0),
            categoria="comun",
            moneda="ARS",
        )
        with patch("app.api.admin.AdminService.create_auction") as create:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(create_auction(body, MagicMock(), self.normal_user))

        self.assertEqual(ctx.exception.status_code, 403)
        create.assert_not_called()

    def test_usuario_comun_no_puede_agregar_items_catalogo(self):
        body = CatalogoItemInput(productoId=77, precioBase=1000, comision=10)
        with patch("app.api.admin.AdminService.add_catalog_item") as add_item:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(add_catalog_item(5, body, MagicMock(), self.normal_user))

        self.assertEqual(ctx.exception.status_code, 403)
        add_item.assert_not_called()

    def test_usuario_comun_no_puede_cerrar_subastas(self):
        with patch("app.api.subastas.SubastaService.cerrar_subasta") as cerrar:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(close_auction(5, MagicMock(), self.normal_user))

        self.assertEqual(ctx.exception.status_code, 403)
        cerrar.assert_not_called()

    def test_admin_puede_aprobar_usuario(self):
        db = MagicMock()
        with patch(
            "app.api.admin.UsuarioRepository.aprobar_registro",
            return_value={"email": "juan@example.com", "token": "123456"},
        ) as aprobar, patch(
            "app.api.admin.EmailService.send_verification_email"
        ) as send_email:
            result = asyncio.run(
                verify_user(
                    55,
                    UsuarioVerificacion(admitido=True, categoria="comun"),
                    db,
                    self.admin_user,
                )
            )

        self.assertEqual(
            result, {"message": "Usuario aprobado. Se envió el email de verificación."}
        )
        aprobar.assert_called_once_with(db, 55, "comun")
        send_email.assert_called_once_with("juan@example.com", "123456")

    def test_aprobar_sin_categoria_devuelve_400(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                verify_user(
                    55,
                    UsuarioVerificacion(admitido=True),
                    MagicMock(),
                    self.admin_user,
                )
            )

        self.assertEqual(ctx.exception.status_code, 400)

    def test_rechazar_sin_motivo_devuelve_400(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                verify_user(
                    55,
                    UsuarioVerificacion(admitido=False),
                    MagicMock(),
                    self.admin_user,
                )
            )

        self.assertEqual(ctx.exception.status_code, 400)


class TestUsuarioRepositoryRegistro(unittest.TestCase):
    @patch("app.repositories.usuario_repo.random.randint", return_value=123456)
    def test_aprobar_registro_genera_token_y_setea_categoria(self, randint):
        db, cursor = make_db({"email": "juan@example.com"})

        result = UsuarioRepository.aprobar_registro(db, 55, "oro")

        self.assertEqual(result, {"token": "123456", "email": "juan@example.com"})
        executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertIn("UPDATE clientes SET admitido = 'si', categoria = %s", executed_sql)
        self.assertIn("estado_registro = 'aprobado'", executed_sql)
        self.assertIn("motivo_rechazo = NULL", executed_sql)
        self.assertIn("token_email = %s", executed_sql)
        db.commit.assert_called_once()

    def test_rechazar_registro_guarda_motivo_y_limpia_token(self):
        db, cursor = make_db({"email": "juan@example.com"})
        motivo = "Documentacion ilegible"

        result = UsuarioRepository.rechazar_registro(db, 55, motivo)

        self.assertEqual(result, {"email": "juan@example.com"})
        executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertIn("UPDATE clientes SET admitido = 'no'", executed_sql)
        self.assertIn("estado_registro = 'rechazado'", executed_sql)
        self.assertIn("motivo_rechazo = %s", executed_sql)
        self.assertIn("token_email = NULL", executed_sql)
        self.assertIn((motivo, 55), [call.args[1] for call in cursor.execute.call_args_list])
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
