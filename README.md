# InfraAssess — Project Handoff & Technical Guide

**Purpose:** Give a teammate enough context to understand the current InfraAssess implementation, run it locally, avoid damaging existing data, and continue development without rebuilding features that already exist.

**Project repository:** [DBMS_INFRA_ASSESS](https://github.com/Vaibhav-alt0246/DBMS_INFRA_ASSESS)
**Primary local path used by the original developer:** `/Users/vaby/DBMS_INFRA_ASSESS`
**Database used during development:** `infraassess_test`
**Project type:** Database Management Systems project — Infrastructure Condition Assessment & Intelligent Failure Management

> **Important handoff rule:** Treat the checked-out repository as the source of truth for exact table definitions, API schemas, environment variables, and commands. This document records the implementation and decisions established during development. It deliberately distinguishes implemented behaviour from items that still need verification. Do not infer missing schema details or change database structures based only on this document.

---

## 1. Project overview

InfraAssess is an infrastructure condition assessment and failure-management application. It is intended to help an operator maintain infrastructure/component records, record condition assessments and sensor readings, track incidents, manage maintenance work, and review alerts and historical activity.

The project combines a conventional relational database with a semantic-search layer:

- **PostgreSQL is the source of truth** for operational records, relationships, constraints, transactions, audit information, and maintenance workflows.
- **Qdrant is a supplementary vector index** used to retrieve semantically similar incidents from their text. It does not replace PostgreSQL.
- **Sentence Transformers** produces text embeddings using `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
- **FastAPI** exposes the backend API and connects the application to PostgreSQL and the semantic-search layer.
- **Next.js + TypeScript** provides the browser-based dashboard and resource-management interface.

The project is not intended to be just a collection of SQL scripts. The important deliverable is an integrated system in which database design, integrity rules, triggers, stored routines, transactions, vector search, backend APIs, and a usable frontend work together.

### Main user workflow

1. Maintain reference information such as locations, categories, components, and technicians.
2. Record assessments and sensor readings about infrastructure components.
3. Create and manage incidents when problems are found.
4. Review health-related alerts and the audit history of relevant changes.
5. Create and manage work orders and maintenance records.
6. Complete work orders through a controlled, database-backed workflow.
7. Search for similar past incidents using natural-language descriptions rather than relying only on exact keyword matches.
8. Review the operational picture through the dashboard.

---

## 2. Important project requirements and design decisions

These are the central requirements and must-haves that shaped the work so far.

### 2.1 Database requirements

- Use a properly related relational schema with primary keys, foreign keys, appropriate constraints, and indexes.
- Keep PostgreSQL as the authoritative store for business data.
- Demonstrate core DBMS concepts in the actual project: schema design, constraints, triggers, views, functions, stored procedures, advanced SQL, query analysis, transactions, and concurrency control.
- Preserve data integrity when incidents and work orders are created or updated.
- Record important changes in an audit trail.
- Generate alerts for critical component-health conditions and avoid creating duplicate active alerts for the same condition.
- Make work-order completion atomic: either all required completion changes are committed, or none are.
- Keep demo data additive. Do not delete or replace the original seeded records when adding further examples.

### 2.2 Application requirements

- Provide actual CRUD operations through the application, not just static mock screens.
- Support the key operational resources, including components, incidents, work orders, assessments, technicians, maintenance records, sensor readings, and alerts, as implemented in the repository.
- Provide a dashboard/overview and a way to inspect operational records.
- Provide semantic incident search through the backend and show the returned records in the UI.
- Make the work-order completion flow use the database procedure rather than duplicating business rules in the frontend.
- Display useful errors and loading/selected states. Buttons and navigation should be visually distinguishable and usable.

### 2.3 Semantic-search requirements

- Use vector search to retrieve incidents based on meaning, not only exact words.
- Keep the embedding model and vector dimensions consistent between indexing and query-time search.
- Store vectors in local persistent Qdrant storage for the current development setup.
- Return incident identifiers and similarity scores from Qdrant, then load the corresponding full incident details from PostgreSQL.
- Keep indexing repeatable and based on stable incident identity so records are not multiplied on every indexing run.
- Evaluate retrieval against queries with expected relevant incidents; do not declare search quality based solely on the fact that the endpoint returns HTTP 200.

### 2.4 Environment and implementation constraints

- The development workflow has been built around macOS and Postgres.app.
- **Do not introduce Docker** as a requirement for this project. The local Qdrant persistence approach is used instead.
- Keep the existing architecture unless a demonstrated requirement or defect justifies a change.
- The frontend should remain a light-theme interface. A teal accent palette was preferred; the existing dashboard styling uses a light surface and teal highlights.

---

## 3. Architecture at a glance

```text
                       Browser
                          |
                          v
                Next.js + TypeScript UI
                          |
                  HTTP requests / JSON
                          |
                          v
                    FastAPI backend
                     /          \
                    /            \
                   v              v
             PostgreSQL         Qdrant
           (source of truth)  (vector index)
                   ^              ^
                   |              |
                   |       Sentence Transformer
                   |      all-MiniLM-L6-v2
                   |          384 dimensions
                   |              ^
                   +--------------+
                   Incident text is read from PostgreSQL
                   and embedded/indexed into Qdrant.
```

### Responsibilities of each component

| Component | Responsibility | Important boundary |
|---|---|---|
| PostgreSQL | Operational data, relationships, constraints, triggers, views, stored routines, audit and transaction integrity | Authoritative data store; Qdrant must not become the source of truth |
| Qdrant local storage | Store incident embeddings and return semantically similar incident IDs/scores | Search index only; it can be rebuilt from PostgreSQL when necessary |
| Sentence Transformers | Convert incident/query text into 384-dimensional vectors | Indexing and search must use the same model/configuration |
| FastAPI | API layer, validation, database access, semantic-search orchestration, work-order completion route | Keep DB work transactional and log internal errors without exposing stack traces to users |
| Next.js | Dashboard, CRUD pages/forms, search interface and work-order completion UI | Render live API responses; do not use hardcoded sample results as the real data source |

### Semantic-search data flow

1. The indexer reads eligible incident data from PostgreSQL.
2. It constructs the text representation used for each incident.
3. The Sentence Transformer converts that text to a 384-dimensional embedding.
4. The embedding and stable incident identity are written/upserted into the Qdrant collection `infra_incidents`.
5. At search time, the query is embedded with the same model.
6. Qdrant returns nearest incident identities and scores.
7. The backend looks up the matching incident details in PostgreSQL.
8. FastAPI returns the ranked incident results to the frontend.

**Consistency rule:** PostgreSQL records and Qdrant points must be kept in sync after incident data changes. The vector store is an index, not a second independently edited incident database.

---

## 4. Technology stack and local environment

| Layer | Technology / configuration |
|---|---|
| Database | PostgreSQL (development was performed with Postgres.app; PostgreSQL 18.6 was previously reported) |
| Vector database | Qdrant local persistent mode |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector dimensions | 384 |
| Backend | Python, FastAPI, psycopg |
| Frontend | Next.js, React, TypeScript |
| Vector integration | `qdrant-client`, Sentence Transformers |
| Backend development server | Uvicorn, port `8000` |
| Frontend development server | Next.js, normally port `3000` |
| Project database | `infraassess_test` |
| Qdrant collection | `infra_incidents` |
| Qdrant persistence path | `data/qdrant_storage` (resolved relative to repository root by the Phase 7 path fix; absolute `QDRANT_PATH` values are preserved) |

The original developer's local working path was `/Users/vaby/DBMS_INFRA_ASSESS`. A teammate should use their own checkout path rather than assuming this absolute path exists on their machine.

### Important Qdrant local-mode warning

Qdrant local persistent storage is not meant to be opened concurrently by multiple independent processes. Before running an indexing, status, or maintenance CLI command against the same local storage directory:

1. Stop FastAPI with `Ctrl + C`.
2. Ensure no other indexer or Qdrant CLI process is using that storage path.
3. Run the indexing/maintenance command.
4. Wait for it to finish.
5. Start FastAPI again.

Do not run the indexer while the backend is using the same local Qdrant directory. Do not delete `data/qdrant_storage` or recreate the collection as a first troubleshooting step.

---

## 5. Database work completed

The database work was divided into phases to demonstrate DBMS concepts in a coherent application.

### Phase 1 — Relational database foundation

Implemented files include:

- `database/schema.sql`
- `database/seed.sql`
- `database/verification.sql`
- `docs/ERD.md`
- `docs/DATABASE_DESIGN.md`

Work completed:

- Designed the initial relational schema around 12 entities and their relationships.
- Added primary keys, foreign keys, constraints, and supporting indexes.
- Added seed data using conflict-aware insertion patterns where appropriate.
- Documented the ER model and database design.
- Created verification queries and constraint checks.
- The schema/seed/verification workflow was executed against a local PostgreSQL 18.6 installation in the earlier development work.

The exact canonical list of all 12 entities, field names, nullability rules, and relationship cardinalities must be read from the current `database/schema.sql` and the ERD. Do not recreate the ER model from memory or this handoff document.

Operational resources explicitly surfaced during application work include locations, categories, components, technicians, assessments, incidents, work orders, maintenance records, sensor readings, and maintenance alerts. Audit information is also exposed read-only through the application. The SQL schema is authoritative for the complete entity list.

### Phase 2 — Triggers and automated integrity rules

Implemented files include:

- `database/triggers.sql`
- `database/trigger_tests.sql`

Implemented behaviour:

1. **Updated timestamp maintenance:** component updates automatically refresh the relevant `updated_at` value.
2. **Audit logging:** changes to incidents and work orders are recorded in JSONB audit data.
3. **Critical-health alert generation:** an alert is generated when a component health score is at or below **70**.
4. **Active-alert duplicate suppression:** duplicate active alerts are prevented using the project's uniqueness/concurrency logic, including a partial unique index and an advisory transaction lock.
5. **Work-order completion validation:** completion requires a completion timestamp, non-empty completion notes, and at least one maintenance record.

The advisory-lock implementation had a function-signature issue during development and was corrected to use a valid single-`bigint` advisory-lock call. The trigger tests were run after the fixes.

Do not bypass these rules in application code. When changing the trigger logic, inspect and run the corresponding SQL tests and ensure the application still follows the same database rules.

### Phase 3 — Advanced SQL and stored routines

Implemented files include:

- `database/views.sql`
- `database/functions.sql`
- `database/procedures.sql`
- `database/advanced_queries.sql`
- `database/performance_tests.sql`

Implemented work includes:

- Views for latest health information, open incidents, and overdue work orders.
- Functions for health/maintenance-related calculations, including maintenance cost functionality.
- Stored procedure `sp_complete_work_order` for atomic work-order completion.
- Advanced query examples, including CTE/window-style and full-text-search work as documented in the SQL files.
- Query-performance investigation using `EXPLAIN` and `EXPLAIN ANALYZE`.

Read the SQL files for the exact signatures, parameters, return types, and query definitions before calling or modifying these routines.

### Phase 4 — Transactions and concurrency control

Implemented files include:

- `database/transaction_tests.sql`
- `docs/TRANSACTION_CONCURRENCY_LAB.md`

Work completed:

- Demonstrated `BEGIN`, `COMMIT`, and `ROLLBACK`.
- Verified rollback behaviour and atomic failure of `sp_complete_work_order`.
- Documented row locking with `FOR UPDATE`.
- Covered `NOWAIT`, `lock_timeout`, and `SKIP LOCKED`.
- Documented `READ COMMITTED` versus `REPEATABLE READ` behaviour.

Transaction tests were run and reported successful. During the manual two-session exercise, `NOWAIT` produced SQLSTATE `55P03`, and the isolation-level behaviour was discussed and observed. The earlier `SKIP LOCKED` exercise did not provide a fully conclusive demonstration of another session holding the row at the exact time of the query. If a viva/demo requires a live `SKIP LOCKED` proof, repeat that two-session experiment carefully and retain both sessions' outputs.

The temporary `transaction_concurrency_lab` table used during an experiment was dropped after the exercise. It is not part of the application's normal runtime schema.

---

## 6. Semantic-search implementation

### Phase 5 — Qdrant and embeddings

The vector-search implementation lives under `vector_db/`.

Known configuration:

- Collection: `infra_incidents`
- Vector size: `384`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Local storage: `data/qdrant_storage`

Work completed:

- Added a Python vector database package and Qdrant local persistence support.
- Added incident embedding/indexing logic.
- Added semantic query embedding and nearest-neighbour retrieval.
- Fixed an embedding conversion issue by using NumPy conversion correctly (`convert_to_numpy=True` was used to resolve the earlier `.tolist()` issue).
- Verified that indexing the original dataset produced three points and repeated indexing did not multiply the point count.
- Verified that search results were joined back to PostgreSQL using incident IDs.

Earlier baseline CLI output showed:

```text
indexed=3 failures=0 points=3
collection=infra_incidents dimension=384 points=3
```

That output describes the **original three-incident baseline**, not the later expanded dataset.

### Semantic-search behaviour verified before dataset expansion

Two different natural-language queries produced different top-ranked incidents.

**Query A:** `The pump is vibrating heavily and leaking`

| Rank | Incident | Score (historical baseline run) |
|---:|---|---:|
| 1 | `INC-2025-002` — Pump seal leakage | 0.4898508512 |
| 2 | `INC-2025-003` — Expansion joint noise | 0.1101115039 |
| 3 | `INC-2025-001` — North bearing deterioration | 0.0787469841 |

**Query B:** `Unsafe bearing condition and repeated assessment findings`

| Rank | Incident | Score (historical baseline run) |
|---:|---|---:|
| 1 | `INC-2025-001` — North bearing deterioration | 0.6203971649 |
| 2 | `INC-2025-003` — Expansion joint noise | 0.3903495089 |
| 3 | `INC-2025-002` — Pump seal leakage | 0.1726585122 |

These results established that the backend was producing query-dependent rankings rather than returning one fixed ordering. The dashboard was also tested with the second query and displayed the bearing incident first in the same order as the API response.

**Do not treat these old scores as current Phase 7 scores.** Scores can change when new incidents are added, the embedding text changes, or the index is rebuilt.

---

## 7. Backend and API work

The backend is under `backend/` and uses FastAPI with PostgreSQL access through psycopg.

Known areas include:

- `backend/app/main.py`
- Backend configuration, DB connection, and request/response schema modules under `backend/app/`.
- `backend/requirements.txt`
- Backend tests under `backend/tests/`

### Backend capabilities implemented

The API provides CRUD support for operational resources, including locations, categories, components, technicians, assessments, incidents, work orders, maintenance records, sensor readings, and maintenance alerts. It also exposes dashboard data, read-only audit-log information, semantic incident search, and a work-order completion operation.

The exact URL and request/response schema for each resource must be checked in the current FastAPI route definitions and Pydantic models. Do not invent endpoint paths or send arbitrary database record fields from the frontend.

### Semantic-search endpoint

Known endpoint:

```http
GET /api/search/incidents?query=<text>&limit=<number>
```

Example:

```bash
curl -iG http://localhost:8000/api/search/incidents \
  --data-urlencode 'query=The pump is vibrating heavily and leaking' \
  --data-urlencode 'limit=5'
```

The endpoint returns a JSON array with fields observed in the test response, including:

- `score`
- `incident_id`
- `incident_number`
- `title`
- `description`
- `severity`
- `status`
- `resolutions`

The API first retrieves ranked incident identities/scores from the vector index and then loads incident information from PostgreSQL.

### Work-order completion

The frontend completion form calls the backend route:

```http
POST /api/work-orders/{id}/complete
```

The completion workflow is backed by `sp_complete_work_order`. The operation records the relevant completion/maintenance information and updates the work order in one transaction. If the procedure or subsequent operation fails, the backend transaction should roll back rather than leaving a partially completed work order.

The UI collects the completion information supported by the current implementation, including technician, maintenance/action notes, actual cost, outcome, completion timestamp, and resolution notes. Check the Pydantic schema and stored-procedure signature for exact field names and types before modifying this contract.

### Error handling and Qdrant path fix

A Phase 7 investigation identified a real diagnostic weakness: the backend had caught semantic-search exceptions and replaced them with a generic 503 response without preserving the original exception in logs. Also, the default `QDRANT_PATH` was relative, so launching the backend from a different working directory could point to a different local store.

Changes reported in these files:

- `vector_db/config.py`
  - Resolves relative Qdrant paths from the repository root.
  - Preserves explicitly configured absolute paths.
- `backend/app/main.py`
  - Logs tracebacks for vector health-check and semantic-search failures, including collection/path context.
  - Returns a safer, more actionable message to the UI while retaining diagnostic detail in server logs.
- `vector_db/test_config.py`
  - Tests default path resolution and preservation of an absolute path.

This was a configuration hardening and observability fix. The original live exception was not reproduced in Codex's environment because FastAPI, psycopg, and qdrant-client were unavailable there. Later, the original developer ran the API locally and obtained HTTP 200 responses for both semantic queries. Therefore the API was verified locally after the path/logging change, but the earlier suspected path mismatch was not conclusively proven to have been the original cause of the first failure.

---

## 8. Frontend and user experience

The frontend lives under `frontend/` and is built with Next.js and TypeScript.

### Features implemented

- Dashboard/overview screen with summary cards and incident-related information.
- Semantic incident search UI.
- Resource-management interface foundation with list/search/detail and create/edit/delete flows for the resources implemented in the app.
- Work-order completion UI connected to the backend completion route.
- Read-only audit-log display.
- Light theme with a teal accent and sidebar/navigation styling.

### UX fixes already made

1. **Button clarity:** Primary, secondary, danger, navigation, table-row, disabled, hover, pressed, and focus states were improved so controls are easier to distinguish.
2. **Navigation state:** The selected navigation item has a persistent active state and uses `aria-current="page"`.
3. **Search loading:** The UI displays `Searching…` during the search request and prevents duplicate searches while one is in progress.
4. **Keyboard focus:** Visible focus styling and reduced-motion handling were added.
5. **API error display:** `frontend/app/error-format.ts` was added to format FastAPI/Pydantic validation errors instead of showing an unusable string such as `[object Object]`.
6. **Request payload safety:** `frontend/app/payload.ts` was added to build editable payloads using an explicit field whitelist. This avoids sending server-managed values such as IDs, timestamps, and extra fields back to strict API schemas during updates.
7. **Stale detail state investigation:** A component edit initially appeared stale in a detail panel. A direct PostgreSQL query confirmed that the stored component name had been updated. The temporary test component was then deleted through the UI and its deletion was verified in SQL; seeded data was preserved.

### Frontend validation previously reported

The following commands passed after the UX and payload/error-handling changes:

```bash
npm run typecheck
npm run build
git diff --check
```

A backend test run was also reported as passing at one point (`1 passed` with a Starlette deprecation warning). Phase 7 vector/config test output later reported `9 passed` in the Codex report. Earlier targeted tests reported `4 passed`. These are historical results from different points in development; rerun the current repository test suite before submitting a final version.

---

## 9. Phase 7 — Synthetic incident dataset expansion

Phase 7 was prepared to make semantic search more meaningful than a three-record demonstration.

### Files added/reported

- `database/demo_incidents.sql`
- `database/demo_verification.sql`
- `vector_db/search_evaluation.py`

The demo seed contains **22 additional synthetic incidents**. They are intended as demonstration/test records, not as real historical incidents. The scenarios cover a broader range of infrastructure problems. Review the SQL file for the exact seeded incident numbers, descriptions, severities, statuses, and foreign-key references.

Expected dataset after a successful seed:

| Dataset component | Expected number |
|---|---:|
| Original incidents | 3 |
| Additional synthetic incidents | 22 |
| **Total** | **25** |

The verification SQL is intended to check the inserted dataset and relevant relationships. The search-evaluation script contains approximately 10–12 natural-language queries with expected relevant incident identities and evaluates whether the expected incident appears in the top three search results.

### Status recorded at handoff

- Codex prepared the 22-record seed, verification SQL, and evaluation script.
- The Codex execution environment initially could not reach PostgreSQL, so the seed/index/evaluation could not be run there.
- The original developer subsequently reopened the local environment and stated that all 13 steps in the local restart/run procedure were completed and verified, including the Phase 7 workflow.
- The exact final output from `vector_db.cli index` and `vector_db.search_evaluation` was not included in the handoff conversation. Therefore the teammate should run the verification commands below and record the actual incident count, Qdrant point count, failures, and top-3 hit rate before claiming a measured evaluation result.

### Reconfirm Phase 7 status

With PostgreSQL running:

```bash
psql -X --set ON_ERROR_STOP=1 -h localhost -p 5432 \
  -d infraassess_test \
  -f database/demo_verification.sql
```

To check the incident count directly (confirm the table name in `schema.sql` if it differs):

```bash
psql -h localhost -p 5432 -d infraassess_test \
  -c 'SELECT COUNT(*) FROM incident;'
```

Before running the Qdrant CLI, stop FastAPI and ensure no other process uses the local Qdrant directory. Then:

```bash
.venv/bin/python -m vector_db.cli index
.venv/bin/python -m vector_db.search_evaluation
```

Do not assume that the expected count or hit rate was achieved; preserve and report the actual command output.

---

## 10. Repository guide — important files

The following paths are known from the implementation history. Use the current repository tree if a path has moved or been renamed.

| Path | Purpose |
|---|---|
| `database/schema.sql` | Core relational schema, relationships, constraints, indexes |
| `database/seed.sql` | Original/reference seed data |
| `database/verification.sql` | Phase 1 verification |
| `database/triggers.sql` | Database triggers and related integrity logic |
| `database/trigger_tests.sql` | Trigger tests |
| `database/views.sql` | Reporting/operational views |
| `database/functions.sql` | Database functions |
| `database/procedures.sql` | Stored procedures, including work-order completion |
| `database/advanced_queries.sql` | Advanced SQL examples |
| `database/performance_tests.sql` | Query-performance investigation |
| `database/transaction_tests.sql` | Transaction and rollback tests |
| `database/demo_incidents.sql` | Additional synthetic Phase 7 incidents |
| `database/demo_verification.sql` | Phase 7 demo-data verification |
| `docs/ERD.md` | Entity-relationship design |
| `docs/DATABASE_DESIGN.md` | Database design documentation |
| `docs/TRANSACTION_CONCURRENCY_LAB.md` | Transaction/concurrency lab notes |
| `vector_db/` | Qdrant configuration, embedding/indexing, search logic and tests |
| `vector_db/config.py` | Qdrant path/configuration handling |
| `vector_db/cli.py` | Vector index command-line entry point |
| `vector_db/search_evaluation.py` | Phase 7 search-quality evaluation |
| `vector_db/test_config.py` | Qdrant path configuration tests |
| `backend/app/main.py` | FastAPI application/routes and error logging |
| `backend/requirements.txt` | Backend Python dependencies |
| `backend/tests/` | Backend tests |
| `frontend/app/page.tsx` | Main frontend page/application flow |
| `frontend/app/styles.css` | Main frontend styling |
| `frontend/app/error-format.ts` | Formatting of API errors for display |
| `frontend/app/payload.ts` | Whitelisted editable request payload construction |
| `data/qdrant_storage/` | Local persistent Qdrant data; do not casually delete or overwrite |

---

## 11. Running the project locally from a clean terminal

This section describes the original macOS development workflow. A teammate should substitute their own local repository path as needed.

### 11.1 Start PostgreSQL

Start Postgres.app:

```bash
open -a Postgres
```

Make Postgres.app's command-line tools available in the current terminal (the exact installed version path may differ):

```bash
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"
```

Confirm the server is accepting connections:

```bash
pg_isready -h localhost -p 5432
```

Confirm the intended database exists and is the one being used:

```bash
psql -h localhost -p 5432 -d infraassess_test \
  -c "SELECT current_database(), current_user, version();"
```

Do not run seed scripts until the database name and server are confirmed.

### 11.2 Backend environment

From the repository root:

```bash
cd /path/to/DBMS_INFRA_ASSESS
source .venv/bin/activate
```

Set the Qdrant location consistently:

```bash
export QDRANT_PATH="$(pwd)/data/qdrant_storage"
```

Start FastAPI:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Keep this terminal open while using the application. The API health endpoint is:

```bash
curl -s http://localhost:8000/api/health
```

### 11.3 Frontend environment

Open another terminal:

```bash
cd /path/to/DBMS_INFRA_ASSESS/frontend
npm run dev
```

Open the local URL printed by Next.js, normally:

```text
http://localhost:3000
```

### 11.4 Test semantic search directly

With FastAPI running:

```bash
curl -iG http://localhost:8000/api/search/incidents \
  --data-urlencode 'query=The pump is vibrating heavily and leaking' \
  --data-urlencode 'limit=5'
```

Try a different query as a sanity check:

```bash
curl -iG http://localhost:8000/api/search/incidents \
  --data-urlencode 'query=Unsafe bearing condition and repeated assessment findings' \
  --data-urlencode 'limit=5'
```

For each query, check both the returned ranking and the corresponding dashboard ranking. The expected incident should move up when the query describes that incident's symptoms/condition.

### 11.5 Re-index after database changes

Only when incident content has changed and the index needs updating:

1. Stop FastAPI with `Ctrl + C`.
2. Make sure no other process uses `data/qdrant_storage`.
3. From the repository root, activate/use the project `.venv` and set `QDRANT_PATH`.
4. Run:

```bash
.venv/bin/python -m vector_db.cli index
```

5. Run the evaluation:

```bash
.venv/bin/python -m vector_db.search_evaluation
```

6. Restart FastAPI after the indexing process exits.

Do not run the indexer concurrently with the API process. Do not remove the Qdrant data directory merely to force a refresh; first establish why an upsert/index operation is insufficient.

---

## 12. Tests and checks to run before making a handoff or submission

Run tests from the repository root with the project's virtual environment activated.

### Vector/configuration tests

A previously used targeted command was:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  vector_db/test_config.py vector_db/test_embeddings.py
```

The earlier Codex report recorded 4 passing tests for this targeted set at one point. A later Phase 7 report recorded 9 passing Python tests across its test selection. Check the current test files and run the full relevant vector test suite; do not assume historical counts still match.

### Backend tests

```bash
.venv/bin/python -m pytest -q backend/tests
```

### Frontend checks

```bash
cd frontend
npm run typecheck
npm run build
```

Then return to the repository root and check for whitespace/conflict issues:

```bash
git diff --check
```

### Database verification

Run the relevant SQL verification/test scripts against the intended development database. Run Phase 7 verification after the demo seed. Do not run destructive cleanup or reset scripts against a shared database.

### Manual end-to-end checklist

- [ ] PostgreSQL is running and the API connects to the intended database.
- [ ] Dashboard loads from live API data.
- [ ] Component and other implemented CRUD flows work.
- [ ] Edit requests send only allowed editable fields.
- [ ] Delete operations respect foreign-key relationships and confirmation UI.
- [ ] Incident search returns different rankings for different query meanings.
- [ ] Dashboard search results match the API response for the same query.
- [ ] Search loading and error states are understandable.
- [ ] Audit history is visible as intended and remains read-only in the UI.
- [ ] Work-order completion uses the stored procedure and fails atomically when required data is missing.
- [ ] Critical-health alert rule and duplicate suppression still work.
- [ ] Qdrant point count matches the number of incidents intended to be indexed.
- [ ] Search evaluation results are recorded, including misses and top-3 hit rate.

---

## 13. Recommended next work

The following work is recommended for the teammate. Prioritize evidence and stability before adding more features.

### Priority 1 — Confirm the Phase 7 final state

- Run `database/demo_verification.sql` and record the real incident count.
- Confirm the original three incidents remain present and the 22 synthetic records are present exactly once.
- Run the Qdrant indexer with FastAPI stopped.
- Confirm the collection point count and indexing failure count.
- Run `vector_db.search_evaluation` and record the actual number of evaluation queries, top-3 hit count, top-3 hit rate, and individual misses.
- Confirm repeated indexing is idempotent and does not create duplicate vector points.

**Deliverable:** a short Phase 7 verification report with real terminal output and measured retrieval results.

### Priority 2 — Improve retrieval quality based on evaluation, not guesswork

- Inspect failed evaluation queries and the text being embedded for the expected incidents.
- Check whether important symptom and resolution text is present in the embedding document.
- Avoid blindly changing models or thresholds. First compare query wording, incident wording, and actual expected matches.
- Consider adding more varied paraphrases to the evaluation set.
- If text construction or metadata needs to change, update the indexer and its tests together, then rebuild/upsert the vector index in a controlled way.
- Keep the evaluation grounded in the current synthetic dataset and label the data as synthetic in demonstrations and reports.

**Deliverable:** a reproducible evaluation showing where semantic search works and where it still misses.

### Priority 3 — Complete end-to-end application regression testing

Test each CRUD resource surfaced by the frontend, particularly create/edit/delete and detail-panel refresh behaviour. Test backend validation errors, empty lists, loading states, and API failures. Verify that the active navigation state, button states, focus indicators, and search loading state still work after future frontend changes.

**Deliverable:** a concise manual/automated regression checklist and resolved defects.

### Priority 4 — Strengthen database workflow verification

Re-run the trigger, procedure, transaction, and advanced-query tests against the current database. If the project must demonstrate `SKIP LOCKED`, prepare a reproducible two-session test where one session holds the relevant row lock while the other runs the query. Preserve clear terminal evidence for both sessions.

**Deliverable:** verified DBMS feature demonstrations suitable for project review/viva.

### Priority 5 — Prepare final documentation and demonstration

Create or update:

- A current ERD and database-design explanation.
- Architecture/data-flow diagram.
- API route and request/response reference derived from the actual code.
- Setup instructions for a clean machine.
- Test/evaluation report with real results.
- A demo sequence showing CRUD, a health alert, a work order lifecycle, audit history, and two contrasting semantic-search queries.

**Deliverable:** a reproducible demo and a technical explanation that maps each major feature to its DBMS concept.

---

## 14. Important cautions for anyone continuing the project

1. **Do not treat Qdrant as the source of truth.** PostgreSQL owns incident records and business state.
2. **Do not run Qdrant local indexing while FastAPI is using the same local storage.** Stop one process before starting the other.
3. **Do not delete `data/qdrant_storage` casually.** It contains the existing local vector index.
4. **Do not reset or truncate the database to add demo incidents.** Phase 7 is intended to be additive.
5. **Do not invent table columns, foreign-key IDs, enum values, or procedure signatures.** Inspect `schema.sql`, seed data, and backend schemas first.
6. **Do not bypass database triggers or `sp_complete_work_order` in application code.** They encode integrity and business rules.
7. **Do not hardcode incident search results in the frontend.** The UI must display the live API result.
8. **Do not claim semantic quality from HTTP 200 alone.** Use query-dependent results and the evaluation script.
9. **Do not report synthetic incidents as real operational history.** Clearly identify them as demo/test data.
10. **Do not assume old test counts or similarity scores are current.** Re-run the relevant tests after changes and record current outputs.
11. **Do not introduce Docker without an explicit project decision.** The established development environment uses Postgres.app and local Qdrant persistence.
12. **Do not remove or replace existing functionality while adding a feature.** Check CRUD, work-order completion, audit logging, and search regression tests.

---

## 15. Suggested first task for the teammate

Before coding, the teammate should:

1. Clone/pull the current repository and inspect `git status` and recent commits.
2. Read this document alongside `README.md`, `docs/ERD.md`, `docs/DATABASE_DESIGN.md`, and `docs/TRANSACTION_CONCURRENCY_LAB.md`.
3. Inspect `database/schema.sql`, `database/demo_incidents.sql`, `database/demo_verification.sql`, `vector_db/config.py`, `vector_db/cli.py`, and `vector_db/search_evaluation.py`.
4. Run the Phase 7 verification SQL and capture actual database counts.
5. Check the Qdrant point count and run the evaluation safely, stopping FastAPI before indexing.
6. Report the measured state before proposing architectural changes.

A good first update from the teammate should contain:

- Current Git branch and commit.
- Actual database name and incident count.
- Count of synthetic demo incidents.
- Qdrant collection name, dimension, point count, and indexing failures.
- Search-evaluation query count and top-3 hit rate.
- Test commands run and pass/fail counts.
- Any defects reproduced with logs or steps.

---

## 16. Final handoff summary

InfraAssess already has a substantial implementation: a relational database foundation, trigger-driven integrity and audit behaviour, reporting views and stored routines, advanced SQL/performance work, transaction/concurrency documentation and tests, Qdrant-based semantic incident retrieval, a FastAPI backend, and a Next.js/TypeScript dashboard with CRUD and work-order completion workflows.

The original three-incident semantic-search baseline was tested end to end and showed query-dependent ranking. Phase 7 prepared 22 additional synthetic incidents and a retrieval-evaluation script. The original developer subsequently reported completing and verifying the 13-step local run procedure. The next teammate should confirm the exact current PostgreSQL count, Qdrant point count, and evaluation metrics from the repository/environment before reporting final Phase 7 performance.

**The guiding principle for future work:** extend the working system in small, verifiable increments; preserve PostgreSQL integrity; keep Qdrant synchronized as a derived search index; and prove each new behaviour with repeatable tests or observable end-to-end results.
