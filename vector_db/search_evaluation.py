"""Evaluate seeded semantic search without changing PostgreSQL or Qdrant."""
import psycopg
from .config import Settings
from .embeddings import SentenceTransformerProvider
from .qdrant_store import IncidentStore
from .search import search_incidents

EVALUATION_QUERIES = [
    ("pump shaking with a leaking mechanical seal", {"INC-DEMO-001", "INC-2025-002"}),
    ("booster cannot hold discharge pressure and loses flow", {"INC-DEMO-002"}),
    ("hot worn bearing on the bridge span", {"INC-DEMO-003", "INC-DEMO-005"}),
    ("traffic causes a metallic expansion joint rattle", {"INC-DEMO-004", "INC-2025-003"}),
    ("cracks and corrosion on a bridge bearing", {"INC-DEMO-005", "INC-2025-001"}),
    ("pothole and settled pavement after rain", {"INC-DEMO-006"}),
    ("storm water drain is blocked with silt", {"INC-DEMO-007"}),
    ("buried pipe leak causing wet soil and low pressure", {"INC-DEMO-008"}),
    ("thermal alarm and overheated electrical phase", {"INC-DEMO-010", "INC-DEMO-022"}),
    ("control room cooling compressor grinding and stopped", {"INC-DEMO-012"}),
    ("sensor readings disagree with the reference gauge", {"INC-DEMO-009", "INC-DEMO-014"}),
    ("pump motor trips during startup with fluctuating current", {"INC-DEMO-019"}),
]

def main():
    settings = Settings.from_env()
    embedder = SentenceTransformerProvider(settings.model_name)
    store = IncidentStore(settings.qdrant_path, settings.collection, embedder.dimension)
    try:
        hits = 0
        with psycopg.connect(**settings.psycopg_kwargs()) as connection:
            for query, expected in EVALUATION_QUERIES:
                results = search_incidents(connection, store, embedder, query, 3)
                numbers = [row['incident_number'] for row in results]
                hit = bool(expected.intersection(numbers)); hits += int(hit)
                print(f"{'PASS' if hit else 'MISS'} | {query} | top3={numbers} | expected_any={sorted(expected)}")
        print(f"top3_hit_rate={hits}/{len(EVALUATION_QUERIES)} ({hits / len(EVALUATION_QUERIES):.1%})")
        if hits != len(EVALUATION_QUERIES):
            raise SystemExit('Semantic relevance regression: expected all seeded top-3 queries to hit')
    finally:
        store.close()

if __name__ == '__main__': main()
