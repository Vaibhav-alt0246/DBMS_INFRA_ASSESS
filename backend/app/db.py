import psycopg
from .config import settings

def connection():
    return psycopg.connect(**settings.psycopg_kwargs())

def rows(cur):
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
