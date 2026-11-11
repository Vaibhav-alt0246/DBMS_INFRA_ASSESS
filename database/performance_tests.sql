-- Phase 3 performance experiments. Read-only; no data changes are performed.
-- Run after views.sql and indexes exist.

-- Inspect indexes relevant to component history and incident filtering.
SELECT tablename, indexname, indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename IN ('component','assessment','incident_component','work_order')
ORDER BY tablename, indexname;

-- Compare planner estimates for an indexed component-history lookup.
EXPLAIN (COSTS, VERBOSE)
SELECT * FROM assessment WHERE component_id = 1 ORDER BY assessed_at DESC;

-- Execute with actual timing/buffer data on the local PostgreSQL instance.
EXPLAIN (ANALYZE, BUFFERS, COSTS, VERBOSE)
SELECT * FROM assessment WHERE component_id = 1 ORDER BY assessed_at DESC;

-- Indexed status/date filter and join plan.
EXPLAIN (ANALYZE, BUFFERS, COSTS, VERBOSE)
SELECT w.work_order_number, c.asset_tag
FROM work_order w JOIN component c USING (component_id)
WHERE w.status IN ('PLANNED','ASSIGNED','IN_PROGRESS') AND w.planned_start < current_date;

-- Interpret plans rather than assume improvement: look for Index Scan/Bitmap Heap Scan,
-- estimated versus actual rows, join type, and shared buffer usage. Small seed tables
-- may legitimately use sequential scans.
