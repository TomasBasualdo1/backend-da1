import asyncio
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.admin import evaluate_article
from app.api.articulos import create_article
from app.repositories.articulo_repo import ArticuloRepository
from app.schemas.schemas import ArticuloEvaluacion, ArticuloInput


def make_db(fetchone_values=None):
    db = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = fetchone_values or []
    cursor.fetchall.return_value = []
    db.cursor.return_value.__enter__.return_value = cursor
    return db, cursor


def articulo_row(**overrides):
    row = {
        "id": 10,
        "duenioId": 123,
        "descripcion": "Reloj antiguo",
        "historia": None,
        "artista": None,
        "fechaCreacion": None,
        "estado": "pendiente",
        "motivoRechazo": None,
        "precioBasePropuesto": None,
        "comisionPropuesta": None,
        "tasacionAceptada": None,
        "fechaEnvio": None,
        "ubicacion": "Deposito CABA",
        "fotos": [
            "https://example.com/foto-1.jpg",
            "https://example.com/foto-2.jpg",
        ],
        "documentacionOrigen": [],
        "seguroPoliza": None,
        "seguroCompania": None,
        "seguroImporte": None,
    }
    row.update(overrides)
    return row


class JsonRequest:
    headers = {"content-type": "application/json"}

    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class TestFlowArticuloProducto(unittest.TestCase):
    def setUp(self):
        self.user = {"usuarioId": 123, "documento": "12345678"}

    def test_crear_articulo_estado_pendiente(self):
        created = articulo_row()
        db, cursor = make_db(
            [
                None,
                {"numeropais": 1},
                {"identificador": 123},
                created,
            ]
        )

        result = asyncio.run(
            create_article(
                JsonRequest(
                    {
                        "descripcion": "Reloj antiguo",
                        "fotos": [
                            "https://example.com/foto-1.jpg",
                            "https://example.com/foto-2.jpg",
                            "https://example.com/foto-3.jpg",
                            "https://example.com/foto-4.jpg",
                            "https://example.com/foto-5.jpg",
                            "https://example.com/foto-6.jpg",
                        ],
                        "esPropietario": True,
                        "declaraOrigenLicito": True,
                    }
                ),
                db,
                self.user,
            )
        )

        self.assertEqual(result["estado"], "pendiente")
        executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertIn("INSERT INTO duenios", executed_sql)
        self.assertIn("INSERT INTO articulos", executed_sql)
        db.commit.assert_called_once()

    def test_evaluar_articulo_rechaza_no_admin(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                evaluate_article(
                    10,
                    ArticuloEvaluacion(
                        **{
                            "estado": "aprobado",
                            "precioBasePropuesto": 1000,
                            "comisionPropuesta": 10,
                        }
                    ),
                    MagicMock(),
                    self.user,
                )
            )

        self.assertEqual(ctx.exception.status_code, 403)

    def test_evaluar_articulo_permite_admin(self):
        admin_user = {"usuarioId": 1, "documento": "1"}

        with patch(
            "app.api.admin.ArticuloRepository.evaluar_articulo",
            return_value=articulo_row(
                estado="aprobado",
                precioBasePropuesto=1000,
                comisionPropuesta=10,
            ),
        ) as evaluar:
            result = asyncio.run(
                evaluate_article(
                    10,
                    ArticuloEvaluacion(
                        **{
                            "estado": "aprobado",
                            "precioBasePropuesto": 1000,
                            "comisionPropuesta": 10,
                        }
                    ),
                    MagicMock(),
                    admin_user,
                )
            )

        self.assertEqual(result["estado"], "aprobado")
        evaluar.assert_called_once()

    def test_create_articulo_repository_inserta_pendiente(self):
        db, cursor = make_db(
            [
                articulo_row(),
            ]
        )

        result = ArticuloRepository.create_articulo(
            db,
            123,
            ArticuloInput(
                **{
                    "descripcion": "Reloj antiguo",
                    "fotos": [
                        "https://example.com/foto-1.jpg",
                        "https://example.com/foto-2.jpg",
                        "https://example.com/foto-3.jpg",
                        "https://example.com/foto-4.jpg",
                        "https://example.com/foto-5.jpg",
                        "https://example.com/foto-6.jpg",
                    ],
                    "esPropietario": True,
                    "declaraOrigenLicito": True,
                }
            ),
        )

        self.assertEqual(result["estado"], "pendiente")
        executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertIn("INSERT INTO articulos", executed_sql)
        db.commit.assert_called_once()

    def test_aceptar_tasacion_inserta_seguro_producto_y_fotos(self):
        db, cursor = make_db(
            [
                articulo_row(
                    estado="aprobado",
                    precioBasePropuesto=1000,
                    comisionPropuesta=10,
                ),
                {"nropoliza": "ART-10-test"},
                {"productoId": 77},
                articulo_row(
                    estado="aprobado",
                    precioBasePropuesto=1000,
                    comisionPropuesta=10,
                    tasacionAceptada=True,
                    seguroPoliza="ART-10-test",
                    seguroCompania="Cobertura DA1",
                    seguroImporte=1000,
                ),
            ]
        )

        result = ArticuloRepository.aceptar_tasacion(db, 10, True)

        self.assertTrue(result["tasacionAceptada"])
        self.assertEqual(result["productoId"], 77)
        executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertIn("INSERT INTO seguros", executed_sql)
        self.assertIn("INSERT INTO productos", executed_sql)
        self.assertIn("INSERT INTO fotos_adicionales", executed_sql)
        db.commit.assert_called_once()

    def test_rechazar_tasacion_deja_articulo_devuelto(self):
        db, cursor = make_db(
            [
                articulo_row(
                    estado="aprobado",
                    precioBasePropuesto=1000,
                    comisionPropuesta=10,
                ),
                articulo_row(
                    estado="devuelto",
                    precioBasePropuesto=1000,
                    comisionPropuesta=10,
                    tasacionAceptada=False,
                ),
            ]
        )

        result = ArticuloRepository.aceptar_tasacion(db, 10, False)

        self.assertEqual(result["estado"], "devuelto")
        self.assertFalse(result["tasacionAceptada"])
        executed_sql = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        self.assertIn("estado = 'devuelto'", executed_sql)
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
