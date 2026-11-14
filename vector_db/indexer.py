import hashlib
from dataclasses import dataclass

@dataclass
class IndexStats:
    scanned: int = 0
    embedded: int = 0
    upserted: int = 0
    removed: int = 0
    failures: int = 0

from qdrant_client import models
from .postgres import fetch_incidents

def content_hash(text): return hashlib.sha256(text.encode()).hexdigest()
def index_incidents(connection, store, embedder, batch_size=64):
    if batch_size < 1:
        raise ValueError('batch_size must be positive')
    docs = fetch_incidents(connection); store.ensure_collection()
    hashes = store.content_hashes()
    stats = IndexStats(scanned=len(docs))
    source_ids = set()
    pending = []

    def flush():
        vectors = embedder.embed([text for _, text, _ in pending])
        if len(vectors) != len(pending):
            raise ValueError('Embedding count does not match incident count')
        points = [models.PointStruct(id=doc.incident_id, vector=vector, payload={'incident_id': doc.incident_id, 'incident_number': doc.incident_number, 'content_hash': digest}) for (doc, _, digest), vector in zip(pending, vectors)]
        store.upsert(points)
        stats.embedded += len(pending)
        stats.upserted += len(points)
        pending.clear()

    for doc in docs:
        source_ids.add(doc.incident_id)
        text = doc.text
        digest = content_hash(getattr(embedder, 'model_name', type(embedder).__qualname__) + '\n' + text)
        if hashes.get(doc.incident_id) != digest:
            pending.append((doc, text, digest))
            if len(pending) >= batch_size:
                flush()
    if pending:
        flush()
    # Prune only after fetching the complete authoritative set and successful upserts.
    removed = set(hashes) - source_ids
    store.delete(removed)
    stats.removed = len(removed)
    return stats
