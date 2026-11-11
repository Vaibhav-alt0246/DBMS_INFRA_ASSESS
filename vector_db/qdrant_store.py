from qdrant_client import QdrantClient, models

class IncidentStore:
    def __init__(self, path, collection, dimension, client=None):
        self.collection = collection; self.dimension = dimension
        self.client = client or QdrantClient(path=str(path))
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
    def search(self, vector, limit):
        try: return self.client.query_points(collection_name=self.collection, query=vector, limit=limit, with_payload=True).points
        except AttributeError: return self.client.search(collection_name=self.collection, query_vector=vector, limit=limit, with_payload=True)
