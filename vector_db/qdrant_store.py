import os
from qdrant_client import QdrantClient, models

class IncidentStore:
    def __init__(self, path, collection, dimension, client=None):
        self.collection = collection; self.dimension = dimension
        self.client = client or (QdrantClient(url=os.environ['QDRANT_URL'], api_key=os.getenv('QDRANT_API_KEY')) if os.getenv('QDRANT_URL') else QdrantClient(path=str(path)))
    def close(self): self.client.close()
    def ensure_collection(self):
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(self.collection, vectors_config=models.VectorParams(size=self.dimension, distance=models.Distance.COSINE)); return
        vectors = self.client.get_collection(self.collection).config.params.vectors
        size = getattr(vectors, 'size', None); distance = str(getattr(vectors, 'distance', '')).split('.')[-1].upper()
        if size != self.dimension or distance != 'COSINE': raise ValueError(f'incompatible collection settings: size={size}, distance={distance}')
    def upsert(self, points):
        if points: self.client.upsert(collection_name=self.collection, points=points, wait=True)
    def count(self): return int(self.client.count(self.collection, exact=True).count)
    def content_hashes(self):
        hashes = {}; offset = None
        while True:
            points, offset = self.client.scroll(self.collection, limit=256, offset=offset, with_payload=['content_hash'], with_vectors=False)
            hashes.update({int(point.id): (point.payload or {}).get('content_hash') for point in points})
            if offset is None: return hashes
    def delete(self, ids):
        ids = list(ids)
        for start in range(0, len(ids), 256):
            self.client.delete(self.collection, points_selector=models.PointIdsList(points=ids[start:start+256]), wait=True)
    def search(self, vector, limit):
        try: return self.client.query_points(collection_name=self.collection, query=vector, limit=limit, with_payload=True).points
        except AttributeError: return self.client.search(collection_name=self.collection, query_vector=vector, limit=limit, with_payload=True)
