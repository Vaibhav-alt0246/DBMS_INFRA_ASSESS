import hashlib
import json
import pytest

@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    monkeypatch.setenv('INFRAASSESS_CREDENTIALS', json.dumps({hashlib.sha256(('test-'+role).encode()).hexdigest(): {'name':'test-'+role,'role':role} for role in ('admin','operator','viewer')}))
    monkeypatch.setenv('API_REQUESTS_PER_MINUTE', '10000')
