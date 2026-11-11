-- Phase 3 reporting views. Run after schema.sql, seed.sql, and triggers.sql.

CREATE OR REPLACE VIEW v_component_current_health AS
SELECT c.component_id, c.asset_tag, c.name, c.status, c.location_id, c.category_id,
       a.assessment_id, a.assessed_at, a.health_score, a.condition_status, a.findings
FROM component c
LEFT JOIN LATERAL (
    SELECT a.* FROM assessment a
    WHERE a.component_id = c.component_id
    ORDER BY a.assessed_at DESC, a.assessment_id DESC
    LIMIT 1
) a ON true;

CREATE OR REPLACE VIEW v_open_incidents AS
SELECT i.*
FROM incident i
WHERE i.status NOT IN ('RESOLVED', 'CLOSED');

CREATE OR REPLACE VIEW v_overdue_work_orders AS
SELECT w.*
FROM work_order w
WHERE w.status NOT IN ('COMPLETED', 'CANCELLED')
  AND coalesce(w.planned_end, w.planned_start) < current_date;

CREATE OR REPLACE VIEW v_component_failure_summary AS
WITH incidents AS (
    SELECT component_id, count(*) AS incident_count,
           count(*) FILTER (WHERE i.severity IN ('HIGH','CRITICAL')) AS serious_incident_count
    FROM incident_component ic JOIN incident i USING (incident_id)
    GROUP BY component_id
), maintenance AS (
    SELECT w.component_id, count(DISTINCT m.maintenance_id) AS maintenance_count,
           coalesce(sum(m.actual_cost), 0) AS actual_maintenance_cost
    FROM work_order w LEFT JOIN maintenance_record m USING (work_order_id)
    WHERE w.component_id IS NOT NULL
    GROUP BY w.component_id
), assessments AS (
    SELECT component_id, count(*) AS assessment_count
    FROM assessment GROUP BY component_id
)
SELECT c.component_id, c.asset_tag, c.name,
       coalesce(i.incident_count, 0) AS incident_count,
       coalesce(i.serious_incident_count, 0) AS serious_incident_count,
       coalesce(m.maintenance_count, 0) AS maintenance_count,
       coalesce(m.actual_maintenance_cost, 0) AS actual_maintenance_cost,
       coalesce(a.assessment_count, 0) AS assessment_count
FROM component c
LEFT JOIN incidents i USING (component_id)
LEFT JOIN maintenance m USING (component_id)
LEFT JOIN assessments a USING (component_id);
