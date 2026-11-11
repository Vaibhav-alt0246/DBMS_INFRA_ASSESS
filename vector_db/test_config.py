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
