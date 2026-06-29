import unittest
from unittest.mock import MagicMock

from app.repositories.subasta_repo import SubastaRepository


def make_db(fetchone_value=None):
    db = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_value
    db.cursor.return_value.__enter__.return_value = cursor
    return db, cursor


class TestSubastaJoinSessionsRepository(unittest.TestCase):
    def test_otra_sesion_solo_bloquea_si_la_otra_subasta_esta_en_vivo(self):
        db, cursor = make_db(fetchone_value=None)

        result = SubastaRepository.check_otra_sesion_activa(db, 99, 20)

        self.assertFalse(result)
        sql = cursor.execute.call_args.args[0]
        self.assertIn("JOIN subastas s", sql)
        self.assertIn("s.estado = 'abierta'", sql)
        self.assertIn("s.fecha = CURRENT_DATE", sql)
        self.assertIn("s.hora <= CURRENT_TIME", sql)
        self.assertEqual(cursor.execute.call_args.args[1], (20, 99))

    def test_otra_sesion_en_vivo_activa_devuelve_true(self):
        db, _ = make_db(fetchone_value={"?column?": 1})

        result = SubastaRepository.check_otra_sesion_activa(db, 99, 20)

        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
