import pytest
qdrant = pytest.importorskip('qdrant_client')
from qdrant_client import QdrantClient, models
from .qdrant_store import IncidentStore

def test_upsert_and_persistence(tmp_path):
    path = tmp_path / 'qdrant'; client = QdrantClient(path=str(path)); store = IncidentStore(path, 'test', 2, client=client); store.ensure_collection()
    point = models.PointStruct(id=1, vector=[1.0, 0.0], payload={'incident_id': 1}); store.upsert([point]); store.upsert([point])
    assert store.count() == 1; assert store.search([1.0, 0.0], 1)[0].id == 1; store.close()
    reopened = QdrantClient(path=str(path)); assert reopened.count('test', exact=True).count == 1; reopened.close()

def test_collection_rejects_incompatible_dimension(tmp_path):
    path = tmp_path / 'qdrant'; client = QdrantClient(path=str(path)); store = IncidentStore(path, 'test', 2, client=client); store.ensure_collection()
    with pytest.raises(ValueError): IncidentStore(path, 'test', 3, client=client).ensure_collection()
    store.close()
