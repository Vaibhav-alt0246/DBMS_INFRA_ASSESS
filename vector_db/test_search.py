from types import SimpleNamespace
import pytest
from vector_db import search

def test_search_preserves_vector_ranking_and_skips_missing_records(monkeypatch):
    class Embedder:
        def embed(self, texts):
            assert texts == ['pump leaking']
            return [[1.0, 0.0]]
    class Store:
        def search(self, vector, limit):
            assert vector == [1.0, 0.0] and limit == 3
            return [SimpleNamespace(id=3, score=0.9), SimpleNamespace(id=9, score=0.8), SimpleNamespace(id=1, score=0.7)]
    monkeypatch.setattr(search, 'fetch_incidents_by_ids', lambda conn, ids: {1: {'incident_id': 1}, 3: {'incident_id': 3}})
    assert search.search_incidents(None, Store(), Embedder(), ' pump   leaking ', 3) == [
        {'score': 0.9, 'incident_id': 3}, {'score': 0.7, 'incident_id': 1},
    ]

@pytest.mark.parametrize('query,limit', [(' ', 3), ('pump', 0), ('pump', 101)])
def test_invalid_search_inputs(query, limit):
    with pytest.raises(ValueError): search.search_incidents(None, None, None, query, limit)
