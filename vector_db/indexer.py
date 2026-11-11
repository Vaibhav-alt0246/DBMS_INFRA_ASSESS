import hashlib
from qdrant_client import models
from .postgres import fetch_incidents

def content_hash(text): return hashlib.sha256(text.encode()).hexdigest()
def index_incidents(connection, store, embedder):
    docs = fetch_incidents(connection); store.ensure_collection()
    if not docs: return 0, 0
    vectors = embedder.embed([doc.text for doc in docs])
    points = [models.PointStruct(id=doc.incident_id, vector=vector, payload={'incident_id': doc.incident_id, 'incident_number': doc.incident_number, 'content_hash': content_hash(doc.text)}) for doc, vector in zip(docs, vectors)]
    store.upsert(points); return len(points), 0
