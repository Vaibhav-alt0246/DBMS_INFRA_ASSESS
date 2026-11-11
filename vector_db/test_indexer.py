import pytest
from qdrant_client import QdrantClient
from vector_db import indexer
from vector_db.postgres import IncidentDocument
from vector_db.qdrant_store import IncidentStore

class Embedder:
    def __init__(self): self.calls = []
    def embed(self, texts):
        self.calls.append(texts)
        return [[1.0, 0.0] for _ in texts]

def document(id, title='Pump leak'):
    return IncidentDocument(id, f'INC-{id}', title, 'Description', None, 'HIGH', 'OPEN', '', '')

def test_incremental_index_updates_and_prunes(monkeypatch):
    docs = [document(1), document(2)]
    monkeypatch.setattr(indexer, 'fetch_incidents', lambda conn: docs)
    embedder = Embedder()
    store = IncidentStore('', 'test', 2, client=QdrantClient(':memory:'))
    try:
        assert indexer.index_incidents(None, store, embedder) == (2, 0)
        indexer.index_incidents(None, store, embedder)
        assert len(embedder.calls) == 1
        docs[:] = [document(2, 'Repaired pump')]
        indexer.index_incidents(None, store, embedder)
        assert len(embedder.calls[-1]) == 1
        assert store.count() == 1
        assert set(store.content_hashes()) == {2}
        docs.clear()
        indexer.index_incidents(None, store, embedder)
        assert store.count() == 0
    finally: store.close()

def test_incomplete_embeddings_do_not_prune_existing_index(monkeypatch):
    docs = [document(1)]
    monkeypatch.setattr(indexer, 'fetch_incidents', lambda conn: docs)
    store = IncidentStore('', 'test', 2, client=QdrantClient(':memory:'))
    try:
        indexer.index_incidents(None, store, Embedder())
        docs[:] = [document(2)]
        embedder = Embedder()
        embedder.embed = lambda texts: []
        with pytest.raises(ValueError): indexer.index_incidents(None, store, embedder)
        assert set(store.content_hashes()) == {1}
    finally: store.close()

def test_large_index_is_embedded_and_upserted_in_bounded_batches(monkeypatch):
    docs = [document(id) for id in range(1, 131)]
    monkeypatch.setattr(indexer, 'fetch_incidents', lambda conn: docs)
    embedder = Embedder()
    store = IncidentStore('', 'test', 2, client=QdrantClient(':memory:'))
    try:
        assert indexer.index_incidents(None, store, embedder) == (130, 0)
        assert [len(call) for call in embedder.calls] == [64, 64, 2]
        assert store.count() == 130
    finally: store.close()

def test_later_batch_failure_preserves_stale_points_for_retry(monkeypatch):
    docs = [document(99)]
    monkeypatch.setattr(indexer, 'fetch_incidents', lambda conn: docs)
    store = IncidentStore('', 'test', 2, client=QdrantClient(':memory:'))
    embedder = Embedder()
    try:
        indexer.index_incidents(None, store, embedder)
        docs[:] = [document(1), document(2)]
        attempts = []
        def embed(texts):
            attempts.append(texts)
            if len(attempts) == 2: raise RuntimeError('Embedding failed')
            return [[1.0, 0.0]]
        embedder.embed = embed
        with pytest.raises(RuntimeError): indexer.index_incidents(None, store, embedder, batch_size=1)
        assert set(store.content_hashes()) == {1, 99}
        indexer.index_incidents(None, store, Embedder())
        assert set(store.content_hashes()) == {1, 2}
    finally: store.close()
