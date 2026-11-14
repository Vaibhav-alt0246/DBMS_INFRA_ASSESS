import hashlib
from fastapi.testclient import TestClient
from backend.app import main
from backend.app.auth import _buckets


def test_missing_and_invalid_credentials_are_rejected():
    client = TestClient(main.app)
    assert client.get('/api/components').status_code == 401
    assert client.get('/api/components', headers={'Authorization':'Bearer wrong'}).status_code == 401


def test_roles_enforce_mutation_delete_and_audit_permissions(monkeypatch):
    monkeypatch.setattr(main, 'generic_list', lambda *a: [])
    viewer = TestClient(main.app, headers={'Authorization':'Bearer test-viewer'})
    operator = TestClient(main.app, headers={'Authorization':'Bearer test-operator'})
    assert viewer.get('/api/components').status_code == 200
    assert viewer.post('/api/components', json={}).status_code == 403
    assert viewer.get('/api/audit-logs').status_code == 403
    assert operator.delete('/api/components/1').status_code == 403
    assert operator.post('/api/sensor-thresholds', json={}).status_code == 403


def test_rate_limit(monkeypatch):
    _buckets.clear()
    monkeypatch.setenv('API_REQUESTS_PER_MINUTE', '1')
    monkeypatch.setattr(main, 'generic_list', lambda *a: [])
    client = TestClient(main.app, headers={'Authorization':'Bearer test-viewer'})
    assert client.get('/api/components').status_code == 200
    assert client.get('/api/components').status_code == 429
    _buckets.clear()


def test_readiness_fails_when_database_is_down(monkeypatch):
    def fail(): raise RuntimeError('secret')
    monkeypatch.setattr(main, 'connection', fail)
    assert TestClient(main.app).get('/api/ready').status_code == 503
    assert TestClient(main.app).get('/api/live').status_code == 200


def test_semantic_failure_uses_lexical_fallback(monkeypatch):
    monkeypatch.setattr(main, 'embedding_provider', lambda: (_ for _ in ()).throw(RuntimeError('offline')))
    monkeypatch.setattr(main, 'lexical_search', lambda query, limit: [{'title':'Pump leak','search_mode':'lexical'}])
    assert main.semantic_search('pump leak', 5)[0]['search_mode'] == 'lexical'


def test_decimal_response_values_remain_exact():
    from decimal import Decimal
    from types import SimpleNamespace
    from backend.app.db import rows
    cursor=SimpleNamespace(description=[SimpleNamespace(name='actual_cost')],fetchall=lambda:[(Decimal('9999999999.99'),)])
    assert rows(cursor)==[{'actual_cost':'9999999999.99'}]
