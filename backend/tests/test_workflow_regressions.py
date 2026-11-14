from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from psycopg import OperationalError

from backend.app import main


@pytest.mark.parametrize('current,new,expected', [
    ('IN_PROGRESS', 'COMPLETED', 422),
    ('COMPLETED', 'PLANNED', 409),
    ('CANCELLED', 'IN_PROGRESS', 409),
    (None, 'ASSIGNED', 404),
    ('PLANNED', 'ASSIGNED', 200),
    ('COMPLETED', 'COMPLETED', 409),
])
def test_status_check_and_write_share_locked_transaction(monkeypatch, current, new, expected):
    queries = []
    transactions = []

    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params): queries.append((sql, params))
        def fetchone(self): return (current,) if current else None

    @contextmanager
    def connection():
        transactions.append('begin')
        try:
            yield SimpleNamespace(cursor=Cursor)
        except Exception:
            transactions.append('rollback')
            raise
        else:
            transactions.append('commit')

    monkeypatch.setattr(main, 'connection', connection)
    monkeypatch.setattr(main, 'rows', lambda cur: [{'work_order_id': 1, 'status': new}])
    if expected == 200:
        assert main.generic_update('work-orders', 1, {'status': new})['status'] == new
        assert transactions == ['begin', 'commit']
        assert len(queries) == 2 and queries[1][0].startswith('UPDATE ')
    else:
        with pytest.raises(HTTPException) as error:
            main.generic_update('work-orders', 1, {'status': new})
        assert error.value.status_code == expected
        assert transactions == ['begin', 'rollback']
        assert len(queries) == 1
    assert queries[0] == ('SELECT status FROM work_order WHERE work_order_id=%s FOR UPDATE', (1,))


def test_unavailable_database_has_consistent_json_error(monkeypatch):
    def fail(): raise OperationalError('internal connection details')
    monkeypatch.setattr(main, 'connection', fail)
    response = TestClient(main.app, headers={"Authorization": "Bearer test-admin"}).get('/api/components')
    assert response.status_code == 503
    assert response.json() == {'detail': 'The database is temporarily unavailable.'}


def test_health_does_not_wait_for_busy_vector_store(monkeypatch):
    @contextmanager
    def connection(): yield SimpleNamespace(execute=lambda sql: None)
    class BusyLock:
        def acquire(self, *, blocking):
            assert blocking is False
            return False
    monkeypatch.setattr(main, 'connection', connection)
    monkeypatch.setattr(main, 'vector_lock', BusyLock())
    assert main.health() == {'api': 'ok', 'postgres': 'ok', 'vector_search': 'busy'}
