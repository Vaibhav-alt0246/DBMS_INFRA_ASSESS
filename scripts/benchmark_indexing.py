"""Compare indexing allocations with synthetic vectors; no database/model access.

Run from the repository root: python -m scripts.benchmark_indexing
Measures Python allocations and batch construction, not model inference or Qdrant I/O.
"""
import gc
import json
import time
import tracemalloc
from unittest.mock import patch

from vector_db.indexer import index_incidents
from vector_db.postgres import IncidentDocument


class SyntheticEmbedder:
    def embed(self, texts):
        return [[(i + 1) / (dimension + 1) for dimension in range(384)] for i in range(len(texts))]


class DiscardingStore:
    def __init__(self): self.largest_batch = 0
    def ensure_collection(self): pass
    def content_hashes(self): return {}
    def upsert(self, points): self.largest_batch = max(self.largest_batch, len(points))
    def delete(self, ids): pass


def main():
    docs = [IncidentDocument(i, f'INC-{i}', 'Pump leak', 'Synthetic benchmark', None, 'HIGH', 'OPEN', '', '') for i in range(1, 2049)]
    results = []
    for size in (len(docs), 64):
        gc.collect()
        store = DiscardingStore()
        with patch('vector_db.indexer.fetch_incidents', return_value=docs):
            tracemalloc.start()
            started = time.perf_counter()
            indexed, failures = index_incidents(None, store, SyntheticEmbedder(), batch_size=size)
            elapsed = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        results.append({'incidents': indexed, 'failures': failures, 'batch_size': size,
                        'largest_upsert': store.largest_batch, 'peak_python_mib': round(peak / 1024**2, 2),
                        'elapsed_seconds': round(elapsed, 3)})
    print(json.dumps(results, indent=2))


if __name__ == '__main__': main()
