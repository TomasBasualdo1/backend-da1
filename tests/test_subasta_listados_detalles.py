from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.repositories.subasta_repo import SubastaRepository
from app.services.subasta_service import SubastaService


def make_db(fetchone_value=None, fetchall_value=None):
    db = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_value
    cursor.fetchall.return_value = fetchall_value if fetchall_value is not None else []
    db.cursor.return_value.__enter__.return_value = cursor
    return db, cursor


def subasta_row(**overrides):
    data = {
        "id": 5,
        "fecha": "2026-07-10",
        "hora": "12:00:00",
        "estado": "abierta",
        "categoria": "comun",
        "ubicacion": "CABA",
        "moneda": "USD",
    }
    data.update(overrides)
    return data


def item_publico(**overrides):
    data = {
        "id": 9,
        "descripcion": "Reloj antiguo",
        "mejorOfertaActual": None,
        "subastado": "no",
        "fotos": ["https://example.com/reloj.png"],
    }
    data.update(overrides)
    return data


def item_privado(**overrides):
    data = {
        "id": 9,
        "descripcion": "Reloj antiguo",
        "precioBase": 1000.0,
        "mejorOfertaActual": None,
        "subastado": "no",
        "fotos": ["https://example.com/reloj.png"],
    }
    data.update(overrides)
    return data


class TestSubastaListadosDetallesRepository(unittest.TestCase):
    def test_publicas_filtra_estado_abierta(self):
        db, cursor = make_db(fetchall_value=[subasta_row()])

        result = SubastaRepository.get_publicas(db)

        self.assertEqual(result[0]["id"], 5)
        sql = cursor.execute.call_args.args[0]
        self.assertIn("WHERE s.estado = 'abierta'", sql)

    def test_listado_publico_moneda_estable_sin_precio_base(self):
        db, cursor = make_db(fetchall_value=[subasta_row()])

        result = SubastaRepository.get_publicas(db)

        self.assertEqual(result[0]["moneda"], "USD")
        self.assertNotIn("precioBase", result[0])
        executed_sql = cursor.execute.call_args.args[0]
        self.assertIn("s.moneda", executed_sql)
        self.assertEqual(cursor.execute.call_args.args[1], ())

    def test_detalle_publico_no_expone_precio_base(self):
        db, _ = make_db(fetchone_value=subasta_row(), fetchall_value=[item_publico()])

        result = SubastaRepository.get_publica_detalle(db, 5, "http://test")

        self.assertIsNotNone(result)
        self.assertNotIn("precioBase", result["catalogo"][0])
        self.assertNotIn("limiteMinimo", result["catalogo"][0])
        self.assertNotIn("limiteMaximo", result["catalogo"][0])

    def test_detalle_publico_normaliza_subastado_no(self):
        db, _ = make_db(fetchone_value=subasta_row(), fetchall_value=[item_publico(subastado=False)])

        result = SubastaRepository.get_publica_detalle(db, 5, "http://test")

        self.assertEqual(result["catalogo"][0]["subastado"], "no")

    def test_subastas_autenticadas_devuelve_abiertas_shape_listado(self):
        db, cursor = make_db(fetchall_value=[subasta_row(categoria="oro")])

        result = SubastaRepository.get_todas(db)

        sql = cursor.execute.call_args.args[0]
        self.assertIn("WHERE s.estado = 'abierta'", sql)
        self.assertEqual(
            set(result[0].keys()),
            {"id", "fecha", "hora", "estado", "categoria", "ubicacion", "moneda"},
        )

    def test_detalle_autenticado_expone_precio_base_y_limites(self):
        db, _ = make_db(fetchone_value=subasta_row(), fetchall_value=[item_privado()])

        result = SubastaRepository.get_detalle(db, 5, "http://test")

        item = result["catalogo"][0]
        self.assertEqual(item["precioBase"], 1000.0)
        self.assertEqual(item["limiteMinimo"], 1000.0)
        self.assertEqual(item["limiteMaximo"], 1200.0)

    def test_moneda_sale_estable_como_usd_en_detalle(self):
        db, _ = make_db(fetchone_value=subasta_row(moneda="USD"), fetchall_value=[])

        result = SubastaRepository.get_detalle(db, 5, "http://test")

        self.assertEqual(result["moneda"], "USD")


class TestSubastaListadosDetallesService(unittest.TestCase):
    def test_detalle_autenticado_categoria_insuficiente_devuelve_403(self):
        db = MagicMock()

        with patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value={"identificador": 5, "estado": "abierta", "categoria": "oro", "moneda": "USD"},
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_detalle",
        ) as get_detalle:
            with self.assertRaises(HTTPException) as ctx:
                SubastaService.get_detalle(
                    db,
                    5,
                    "http://test",
                    usuario_id=20,
                    categoria_usuario="plata",
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("categoria", ctx.exception.detail)
        get_detalle.assert_not_called()

    def test_detalle_autenticado_categoria_suficiente_devuelve_catalogo(self):
        db = MagicMock()
        detalle = subasta_row(categoria="especial")
        detalle["catalogo"] = [item_privado()]

        with patch(
            "app.services.subasta_service.SubastaRepository.get_subasta_basica",
            return_value={
                "identificador": 5,
                "estado": "abierta",
                "categoria": "especial",
            },
        ), patch(
            "app.services.subasta_service.SubastaRepository.get_detalle",
            return_value=detalle,
        ) as get_detalle:
            result = SubastaService.get_detalle(
                db,
                5,
                "http://test",
                usuario_id=20,
                categoria_usuario="oro",
            )

        self.assertEqual(result["catalogo"][0]["id"], 9)
        get_detalle.assert_called_once_with(db, 5, "http://test")

    def test_moneda_usd_esta_documentada_en_nota_p1_1(self):
        note_path = (
            Path(__file__).resolve().parents[1]
            / "context"
            / "20_P1_1_AUCTION_LISTINGS_DETAILS_NOTES.md"
        )

        self.assertTrue(note_path.exists())
        note = note_path.read_text(encoding="utf-8")
        self.assertIn("USD", note)
        self.assertIn("PENDIENTE DE CONFIRMAR", note)


if __name__ == "__main__":
    unittest.main()
