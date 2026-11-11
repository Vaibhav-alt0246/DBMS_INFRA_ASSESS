# InfraAssess — Database Foundation

InfraAssess is a database-backed system for assessing infrastructure condition and managing failures. It records locations, infrastructure components, inspections, incidents, technicians, planned work, completed maintenance, sensor readings, alerts, and an audit trail.

## Stack

- PostgreSQL: source of truth for structured data
- Next.js + TypeScript: planned frontend
- FastAPI + Python: planned backend
- Qdrant: planned semantic-search store, with embeddings linked to SQL incident IDs

Phase 1 contains only the PostgreSQL foundation. It intentionally has no application credentials, vector dependency, frontend, or backend.

## Files

- `docs/ERD.md` — attribute-level Mermaid ER diagram and cardinalities
- `docs/DATABASE_DESIGN.md` — entities, dependencies, integrity rules, normalization, and future triggers
- `database/schema.sql` — PostgreSQL DDL
- `database/seed.sql` — reproducible demonstration data
- `database/verification.sql` — checks and syllabus-oriented example queries

## Roadmap

1. Database foundation (this phase): relational model, constraints, indexes, seed data, and verification queries.
2. Database programming: views, functions, procedures, CTEs, window queries, and the planned triggers.
3. FastAPI service: validation, transactions, concurrency handling, and REST endpoints.
4. Next.js interface: dashboards, assessments, work orders, and incident history.
5. Semantic search: generate embeddings from incident/maintenance text and store them in Qdrant keyed by SQL incident IDs.
6. Optimization and evaluation: query plans, indexes, normalization review, and workload testing.

## Local validation

With PostgreSQL available:

```bash
createdb infraassess
psql -d infraassess -f database/schema.sql
psql -d infraassess -f database/seed.sql
psql -d infraassess -f database/verification.sql
```

The schema does not use destructive `DROP ... CASCADE` statements. Seed inserts use stable natural keys and `ON CONFLICT`, so rerunning the seed is safe.
