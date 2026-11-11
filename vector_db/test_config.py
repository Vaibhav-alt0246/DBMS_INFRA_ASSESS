from pathlib import Path

from vector_db.config import Settings


def test_default_qdrant_path_is_project_root_relative(monkeypatch):
    monkeypatch.delenv('QDRANT_PATH', raising=False)
    settings = Settings.from_env()
    assert settings.qdrant_path.is_absolute()
    assert settings.qdrant_path == Path(__file__).resolve().parents[1] / 'data' / 'qdrant_storage'


def test_absolute_qdrant_path_is_preserved(monkeypatch, tmp_path):
    monkeypatch.setenv('QDRANT_PATH', str(tmp_path / 'qdrant'))
    assert Settings.from_env().qdrant_path == tmp_path / 'qdrant'

def test_connection_timeout_has_bounded_default(monkeypatch, tmp_path):
    monkeypatch.delenv('PGCONNECT_TIMEOUT', raising=False)
    assert Settings(None, tmp_path).psycopg_kwargs()['connect_timeout'] == '5'

def test_database_url_preserves_explicit_timeout(monkeypatch, tmp_path):
    monkeypatch.setenv('PGCONNECT_TIMEOUT', '9')
    settings = Settings('postgresql://localhost/example?connect_timeout=2', tmp_path)
    assert settings.psycopg_kwargs()['connect_timeout'] == '2'
    assert settings.psycopg_kwargs()['dbname'] == 'example'
