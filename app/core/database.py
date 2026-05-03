from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.config import settings


@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg.connect(settings.database_url, row_factory=dict_row)
        yield conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise e
    finally:
        if conn is not None:
            conn.close()
