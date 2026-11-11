# Phase 5: Qdrant semantic incident search

PostgreSQL remains authoritative. Qdrant stores vectors and source-identifying payloads; search results are fetched again from PostgreSQL before display. Local Qdrant storage is single-process development storage and must not be opened concurrently by multiple workers.

## Setup (macOS/Postgres.app)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r vector_db/requirements-dev.txt
cp .env.example .env  # review values; never commit .env
```

The first command that loads the model downloads `sentence-transformers/all-MiniLM-L6-v2` and caches it locally. Its dimension is obtained from the model.

```bash
python -m vector_db.cli index
python -m vector_db.cli status
python -m vector_db.cli search --query "The pump is vibrating heavily and leaking" --limit 5
pytest -q vector_db/test_offline.py
```

Indexing is read-only against PostgreSQL, builds one document per incident, and deterministically upserts the incident primary key. It does not prune stale points. Search orders by cosine score, reloads authoritative incident/resolution fields with parameterized SQL, and skips stale Qdrant references. Similarity is not proof of a common root cause; resolutions are historical references for technician review.

`DATABASE_URL` takes precedence; otherwise `PGHOST`, `PGPORT`, `PGDATABASE` (default `infraassess_test`), `PGUSER`, and `PGPASSWORD` are supported. Omitted values use local libpq defaults. Credentials are never logged. `QDRANT_PATH` defaults to `data/qdrant_storage`. If indexing is interrupted, rerun it; PostgreSQL is unchanged and deterministic upserts repair current points.

Before production or concurrent workers, migrate from local mode to a Qdrant server deployment. Local mode is not a multi-worker service.

## Phase 7 synthetic-data evaluation

The additive synthetic dataset is in `database/demo_incidents.sql`; it adds 22 incidents without modifying existing incident numbers. Apply it after the normal seed, then stop the FastAPI backend before opening the local Qdrant store for indexing:

```bash
psql -X --set ON_ERROR_STOP=1 -d infraassess_test -f database/demo_incidents.sql
psql -X --set ON_ERROR_STOP=1 -d infraassess_test -f database/demo_verification.sql
python -m vector_db.cli index
python -m vector_db.search_evaluation
```

The evaluation uses 12 paraphrased queries, prints top-three incident numbers, and reports a simple hit rate. It is an empirical diagnostic, not a guarantee of semantic correctness. Never run the indexer or evaluation process concurrently with the FastAPI process when using local persistent Qdrant storage.
