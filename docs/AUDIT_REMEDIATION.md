# Audit remediation — 2026-11-14

This register addresses `InfraAssess_Full_Audit_2026-11-14.md` against the repository source. The audit document was treated as findings, not as an instruction source. Existing data is upgraded using an additive migration; the original installer remains for empty databases.

| Findings | Implemented changes |
|---|---|
| A01, A06–A08 | Fail-closed per-user bearer authentication; viewer/operator/admin permissions; request rate limits and access logs; authenticated transaction-local actor; INSERT/UPDATE/DELETE auditing across business tables; append-only audit history. |
| A02, A17 | Atomic incident creation with component IDs; validated link/unlink API; searchable form/detail selectors; missing expansion-joint seed association. |
| A03–A05, A15–A16 | Seed backfill and latest-observation health reconciliation; automatic recovery; configured asset-specific sensor thresholds; overdue-order reconciliation from triggers and a scheduled worker. |
| A09–A14 | Incident/work-order timestamp checks; corrected synthetic incident; immutable terminal orders and maintenance history; active-technician checks; cancelled-order maintenance rejection. |
| A18–A20 | Email format validation; accurate scanned/embedded/upserted/removed/failure index counters; 26-row lookahead for 25-row pages. |
| B01–B03 | Searchable relationship selectors, dashboard report pages/API, affected assets and safe text highlighting in search results. |
| B04 | Alert ownership, related remediation work orders, required resolution verification notes and recorded verification time. Conditions still active are reopened by reconciliation. |
| B05–B06 | Validated sort, status/severity/component/location/date API filters, UI sort/status/severity/date controls, totals, and decimal strings in API responses/form/completion requests. |
| C01–C06 | Index synchronization moved out of searches into a scheduled worker; Qdrant server mode avoids local-store ownership and process-wide serialization; SQL fallback; model-specific collection namespaces/hashes; offline model-cache support. |
| C07–C12 | Separate liveness/readiness contracts, same-origin frontend proxy, explicit multiple-origin CORS configuration, versioned additive migration, pinned Python dependency lock, container deployment and backup/restore tooling and instructions. |

## Measured locally

- Windows, Python 3.13, Node 22, disposable PostgreSQL 17.11 on loopback port 55432.
- Fresh `database/install.sql`: passed, including critical pump alert backfill.
- Transactional migration rerun: passed.
- `constraint_tests.sql`, `trigger_tests.sql`, `advanced_sql_tests.sql`, `transaction_tests.sql`: passed. Live execution revealed an incorrect old SQLSTATE expectation in the foreign-key tests; it was corrected.
- Python: **76 passed**, including live CRUD/delete auditing for every editable API resource, actor attribution, atomic incident/link rollback, lifecycle/technician guards, sensor recovery, filtered queries/injection rejection, and a real two-connection completion race.
- Frontend payload tests, typecheck and production build: passed.
- Playwright: **11 passed**, comprising 10 mocked regressions and one unmocked browser/API/PostgreSQL workflow covering asset and incident creation, linking, maintenance completion, alerts, reports and search. Browser tests found duplicate filter controls and missing selector accessibility labels; both were corrected.
- Real embeddings: 25 incidents indexed; 12/12 seeded top-three relevance queries passed.
- Separate offline process with `EMBEDDING_OFFLINE=1` and `HF_HUB_OFFLINE=1`: cached model load, persisted Qdrant count and search passed; unchanged corpus reported `scanned=25 embedded=0 upserted=0 removed=0 failures=0`.
- PostgreSQL custom-format backup restored successfully into a separate database; incident, audit and migration counts verified.

## Operational boundaries

Local results do not prove an arbitrary hosted deployment, macOS/Linux model download, or production load capacity. CI now defines Linux database/browser/search checks and Windows/macOS Python checks; inspect the actual run results before claiming those environments passed. Docker deployment configuration requires a Docker-capable host and its own smoke test. No production database or hosted deployment was modified by this remediation.

The worker scans the source corpus on its schedule; it is not a change-data-capture queue. In-process rate limits are supplemented by an ingress rate limiter when using multiple API workers. Sensor thresholds require operator-approved asset limits. Historical audit records lacking identity remain historical unknowns; new mutations have attribution. Configure real credentials, TLS, least-privilege database roles, backup retention and sensor limits using [OPERATIONS.md](OPERATIONS.md) before exposing a deployment.
