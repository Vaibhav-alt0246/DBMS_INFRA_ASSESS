# Project verification — 2026-11-11

Reviewed the README, backend, frontend, vector package, schema, seeds, routines, triggers, SQL checks and design documentation. The starting checkout was commit `ebff45a` with no tracked changes.

## Defects addressed

- Reference-resource POST routes previously used plain dictionaries but called `.model_dump()`, causing location/category creation to fail. They now use validated request models.
- Generated CRUD handlers exposed `_key` as a query parameter, allowing requests to redirect operations to another registered table. Resource selection is now bound inside route closures.
- PATCH previously required full create payloads, reset default-valued fields, discarded explicit nulls and generated invalid SQL for empty updates. It now validates partial changes, preserves nullable clears and rejects empty mutations.
- Database workflow failures now map to appropriate 409/422 responses instead of generic server errors; unexpected database exceptions are logged.
- Blank semantic queries are rejected before loading models. Concurrent local Qdrant requests are serialized, stores close on failure, and the embedding provider is cached.
- Changed and deleted incidents previously left stale vectors. Incremental hashing now refreshes changed documents and prunes deleted IDs before API search. Embedding-count mismatches stop synchronization before pruning.
- Frontend resource switching could retain another resource's state. Management panels now remount by resource, and saved selections are cleared.
- Alert creation previously submitted an incomplete payload. Generated alerts now expose status editing, with no create/delete controls.
- Missing work-order incident/planned-end fields and incident resolution time are exposed. Decimal inputs, nullable clears, active-technician defaults and local timestamp editing are corrected.
- Pagination makes records beyond the first page accessible. Mobile navigation remains visible. Audit JSON is rendered as readable text.
- Generic API mutations cannot complete an open work order without the dedicated procedure-backed operation.
- `.env` is now loaded, test dependencies/commands are declared, and a fresh-database SQL installer documents the required seed/trigger order.
- Next.js and React were updated after the dependency audit identified advisories affecting the old release. See the [official migration guide](https://nextjs.org/docs/app/guides/upgrading/version-16) and [maintainer security advisory](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw). The lockfile records the installed versions.

## Second audit: optimization and additional regressions

- Overlapping list searches and overview refresh/search requests could let old responses replace current results. Reads now abort superseded requests, check request identity before state changes and cancel on unmount.
- Selecting a different record while editing left the previous editor open. Selection now exits that editor. Record identity uses explicit primary-key names instead of depending on JSON property order.
- Refreshing a list could still leave its selected detail stale. Successful reads now refresh the selection from that same response or clear it if the record is no longer present. A stateful browser test verifies editing, list refresh and selected-detail synchronization together.
- Deleting the final item on a later page left an empty page. The UI now moves to the previous page and prevents duplicate deletes while a deletion is pending.
- Timestamp controls hid seconds/milliseconds. They now display and accept millisecond precision; unchanged API timestamps bypass JavaScript Date conversion to preserve PostgreSQL microseconds.
- Invalid numeric form values could become JSON null or rounded identifiers. Non-finite numbers and invalid/unsafe IDs are rejected in the payload builder.
- API inputs now validate status/outcome enums, nonblank text, positive bigint IDs, column lengths, timezone-aware timestamps and decimal precision. Monetary values remain Decimal through request validation and SQL parameter binding.
- Work-order PATCH previously checked completion state through another connection. It now checks and updates under one row lock/transaction, rejects reopening terminal orders and preserves workflow-specific 409/422 errors. Completion locks the target before reading its procedure identifier.
- Connection attempts now have a configurable five-second default timeout; unavailable database reads receive the same JSON 503 contract as writes. Health checks report a busy vector index without waiting behind model/index operations.
- Indexing formerly constructed every changed vector/point at once. It now embeds/upserts 64 at a time, computes document text/hashes once per pass, retrieves only hash payloads and deletes stale IDs in batches of 256. Pruning still waits for all upserts to succeed; a failed later batch is repairable on retry.

### Synthetic allocation measurement

Command: `python -m scripts.benchmark_indexing`, using 2,048 synthetic 384-dimensional vectors.

| Batch size | Largest upsert | Peak traced Python allocation |
|---|---:|---:|
| 2,048 (all at once) | 2,048 | 32.67 MiB |
| 64 (current default) | 64 | 1.14 MiB |

This measures transient Python allocations during vector/index construction. Source documents are pre-created, embeddings are synthetic, and the store discards points after upsert. It excludes source retrieval, real model inference, native allocations and persistent Qdrant I/O; it is not a total-application memory or end-to-end latency measurement.

## Measured checks

Python regression tests exercise API contracts using isolated doubles and real temporary/in-memory Qdrant, without downloading a model or modifying PostgreSQL.

| Check | Observed result |
|---|---|
| `python -m pytest -q backend/tests vector_db --basetemp .pytest_tmp` | 54 passed; one upstream Starlette/httpx deprecation warning |
| `npm test` | Payload and API-error regression scripts passed |
| `npm run typecheck` | Passed |
| `npm run build` | Passed on Next.js 16.4.6 / React 19.3.1 |
| Production-build Playwright suite (`npm run test:e2e`; final test-only rerun via `npm exec -- playwright test`) | 10 passed using mocked API responses: request races, edit/refresh synchronization, timestamp precision, deletion pagination, duplicate-save protection, validation errors, mobile navigation and keyboard focus |
| `npm audit --omit=dev` | Zero known vulnerabilities reported |
| `python -m pip check` | No broken requirements |
| `git diff --check` | Passed |

The workspace-owned pytest temporary directory avoids an existing Windows temporary-directory permission problem. These checks do not substitute for the live database/evaluation checks below.

## Live verification still required

No PostgreSQL service accepted connections on `localhost:5432` during this audit. No live database credentials or existing Qdrant data were present in the checkout. Therefore the following results are **not measured**:

- Current database identity, incident count and synthetic incident count.
- Live trigger, stored-procedure, transaction and concurrency results.
- A coordinated two-session `SKIP LOCKED` demonstration while another session holds the target row lock.
- Current persistent Qdrant point count and indexing failures against PostgreSQL.
- Actual embedding-based top-3 hit rate over the 12 evaluation queries.
- Live browser CRUD/search/completion against PostgreSQL.

The intended synthetic baseline remains 3 original plus 22 demo incidents. That is an expected seed result, not an observed database count. No existing database was reset or seeded during this audit. Follow `SETUP.md` once PostgreSQL is available, and record real output before claiming end-to-end completion.
