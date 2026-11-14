from contextlib import contextmanager
from decimal import Decimal
from .auth import actor
import psycopg
from .config import settings

@contextmanager
def connection():
    with psycopg.connect(**settings.psycopg_kwargs()) as conn:
        conn.execute("SELECT set_config('app.user', %s, true)", (actor.get(),))
        yield conn

def rows(cur):
    cols = [d.name for d in cur.description]
    return [{key: str(value) if isinstance(value, Decimal) else value for key, value in zip(cols, row)} for row in cur.fetchall()]
