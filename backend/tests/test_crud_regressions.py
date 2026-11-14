from contextlib import contextmanager
from fastapi.testclient import TestClient
from psycopg.errors import ObjectNotInPrerequisiteState
from backend.app import main

client = TestClient(main.app, headers={"Authorization": "Bearer test-admin"})

def test_partial_patch_does_not_reset_defaults(monkeypatch):
    calls = []
    monkeypatch.setattr(main, 'generic_update', lambda *args: calls.append(args) or {'status': 'DEGRADED'})
    response = client.patch('/api/components/1', json={'status': 'DEGRADED'})
    assert response.status_code == 200
    assert calls == [('components', 1, {'status': 'DEGRADED'})]

def test_patch_preserves_explicit_nullable_clear(monkeypatch):
    calls = []
    monkeypatch.setattr(main, 'generic_update', lambda *args: calls.append(args) or {})
    assert client.patch('/api/work-orders/1', json={'technician_id': None}).status_code == 200
    assert calls[0][2] == {'technician_id': None}

def test_patch_rejects_null_required_field_and_invalid_score():
    assert client.patch('/api/components/1', json={'name': None}).status_code == 422
    assert client.patch('/api/assessments/1', json={'health_score': 101}).status_code == 422

def test_empty_patch_is_validation_error():
    assert client.patch('/api/components/1', json={}).status_code == 422

def test_internal_table_selector_cannot_redirect_route(monkeypatch):
    calls = []
    monkeypatch.setattr(main, 'generic_list', lambda *args: calls.append(args) or [])
    assert client.get('/api/components?_key=technicians').status_code == 200
    assert calls[0][0] == 'components'
    parameters = main.app.openapi()['paths']['/api/components']['get']['parameters']
    assert '_key' not in {parameter['name'] for parameter in parameters}

def test_reference_records_are_validated():
    assert client.post('/api/locations', json={}).status_code == 422
    assert client.post('/api/categories', json={'category_code': 'X', 'name': 'X', 'unexpected': 1}).status_code == 422

def test_alerts_are_generated_and_audit_is_read_only():
    assert client.post('/api/maintenance-alerts', json={'status': 'OPEN'}).status_code == 405
    assert client.delete('/api/maintenance-alerts/1').status_code == 405
    assert client.post('/api/audit-logs', json={}).status_code == 405

def test_whitespace_query_rejected_before_model_loading(monkeypatch):
    monkeypatch.setattr(main, 'embedding_provider', lambda: (_ for _ in ()).throw(AssertionError('must not load model')))
    assert client.get('/api/search/incidents', params={'query': '   '}).status_code == 422

def test_repeated_completion_reports_conflict():
    assert main.db_error(ObjectNotInPrerequisiteState()).status_code == 409

def test_update_sends_sql_null(monkeypatch):
    class Cursor:
        description = []
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params):
            if sql.startswith('SELECT status'): return
            assert 'technician_id=%s' in sql
            assert params == (None, 1)
        def fetchone(self): return ('PLANNED',)
        def fetchall(self): return [()]
    class Connection:
        def cursor(self): return Cursor()
    @contextmanager
    def connection(): yield Connection()
    monkeypatch.setattr(main, 'connection', connection)
    assert main.generic_update('work-orders', 1, {'technician_id': None}) == {}
