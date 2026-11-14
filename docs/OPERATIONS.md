# Operations after the 2026-11-14 audit

## Access and deployment

API access fails closed until `INFRAASSESS_CREDENTIALS` contains a JSON object mapping SHA-256 bearer-token digests to `{ "name": "operator-name", "role": "operator" }`. Generate a unique random token per human using `python -c "import secrets; print(secrets.token_urlsafe(32))"`, compute its SHA-256 locally, and distribute the token privately. Never commit tokens or the live environment file. Rotate by replacing the digest; revoke by removing it. Browser tokens last for the tab session and are cleared on sign-out. Use HTTPS at your reverse proxy.

Roles: viewers can read operational resources; operators can create/update records, link assets, complete work, and manage remediation; admins additionally delete/unlink, configure thresholds, and read audit history. Audit records use the authenticated name via transaction-local PostgreSQL settings. Direct SQL records use the database login. The application does not accept a user-name header. The in-process rate limit defaults to 300 requests/user/minute; configure an ingress rate limit for aggregate enforcement across workers.

Use `docker compose -f deploy/compose.yaml up --build` with `POSTGRES_PASSWORD` and `INFRAASSESS_CREDENTIALS` supplied by your deployment secret manager. The web port binds to loopback; put your TLS reverse proxy in front. PostgreSQL and Qdrant are internal services. Provision a least-privilege API database login for hosted deployments; the compose owner account is intended for isolated evaluation. Give the API DML access to business tables and INSERT-only access to audit_log, without DDL/TRUNCATE or superuser privileges. Back up before upgrading. `/api/live` is liveness; `/api/ready` returns 503 when PostgreSQL is unavailable. `/api/health` is a descriptive diagnostic retained for compatibility, not a readiness probe.

The browser uses a same-origin `/api` proxy. `API_INTERNAL_URL` configures its backend destination at build time; `NEXT_PUBLIC_API_BASE_URL` can explicitly override it. For a separate frontend domain, set a comma-separated `FRONTEND_ORIGINS` allowlist. CORS does not replace authentication.

## Alerts and business rules

`python -m scripts.worker` reconciles alerts and synchronizes vectors every 60 seconds (configurable with `SYNC_INTERVAL_SECONDS`). Run one worker. Triggers also reconcile after assessment, work-order, incident-link, threshold, or sensor changes. Calendar rollover requires the worker. Health alerts use the latest non-future observation and recover automatically. Historical edits cannot supersede a newer observation. Sensor thresholds are explicitly configured per component, sensor type, and unit; there are no assumed universal engineering limits. Configure them in the admin console. Overdue alerts include work orders linked indirectly through incidents.

Assign an alert owner and a remediation work order, record verification notes, and resolve it after checking the asset. Source conditions remain authoritative: the worker reopens an alert when a critical condition still exists. Terminal work orders are immutable; future corrective work belongs in a new work order. Inactive technicians remain valid historical references, but cannot receive new assignments or maintenance entries. Incident status and resolution time must be changed together.

## Search

The API never synchronizes the corpus on a user query. The separate worker does bounded embedding batches and prunes deleted documents. Qdrant server mode (`QDRANT_URL`) supports multiple API processes; local persistence is only for a single owner process, so stop the local API before standalone indexing. Use server mode for simultaneous worker/API operation. Model IDs namespace collections and enter document hashes. Set `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, and optionally `QDRANT_COLLECTION` consistently on worker/API/CLI. A model switch requires a fresh indexing pass. Pre-cache weights with `python -m vector_db.cli index`, then set `EMBEDDING_OFFLINE=1` and verify a restart. Model/Qdrant failures fall back to PostgreSQL full-text search with `search_mode=lexical` in results.

## Migration and rollback

Fresh databases: `psql -X -v ON_ERROR_STOP=1 -f database/install.sql`.
Existing databases: back up, stop writers, then `psql -X -1 -v ON_ERROR_STOP=1 -f database/migrations/001_audit_remediation.sql`. The migration is additive, records its version, corrects only the identified synthetic incident, and aborts on other inconsistent lifecycle rows. Investigate those rows rather than guessing missing timestamps. Do not rerun the legacy `triggers.sql` after this migration. For rollback, restore the pre-upgrade archive into a new database, verify it, deploy the prior application revision, and switch the connection. Do not drop new columns or audit records in place.

## Backup and restore

With PostgreSQL client tools on PATH and credentials in PG* variables:

```
python scripts/backup_restore.py backup infraassess-YYYY-MM-DD.dump --database infraassess
createdb infraassess_restore
python scripts/backup_restore.py restore infraassess-YYYY-MM-DD.dump --database infraassess_restore
```

Use encrypted off-host storage, a daily retention policy appropriate for your organization, and periodic restore drills. A successful dump alone is not proof of recoverability. Validate row counts, latest audit entries, constraints, and API reads on the restored database. Qdrant is derived data: rebuild it from restored PostgreSQL. Back up credential configuration separately in the secret manager.

## Reproducibility

`requirements-lock.txt` pins the complete Python 3.13 environment verified on Windows. CI exercises the same pins on Linux; other Python/platform combinations need their own validation. `frontend/package-lock.json` fixes npm dependencies. CI installs a fresh PostgreSQL database, runs SQL suites, Python tests, the production frontend build, and mocked browser regression tests. Live integration tests run when `TEST_DATABASE_URL` points to a disposable installed database. Never point that variable at production.
