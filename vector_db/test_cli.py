from vector_db import cli

def test_status_does_not_download_embedding_model(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv('QDRANT_PATH', str(tmp_path / 'qdrant'))
    def fail(*args): raise AssertionError('Status must not initialize an embedding model')
    monkeypatch.setattr(cli, 'SentenceTransformerProvider', fail)
    cli.main(['status'])
    assert 'dimension=384 points=0' in capsys.readouterr().out
