-- Run after schema.sql and seed.sql. Each query has an expected interpretation.

-- Row counts should be: locations 3, categories 3, components 4, technicians 3,
-- assessments 5, incidents 3, incident links 3, work orders 3, maintenance records 1,
-- readings 4, alerts 3, and audit logs 0 for the current seed.
WITH expected(table_name) AS (
    VALUES
        ('location'), ('component_category'), ('component'), ('technician'),
        ('assessment'), ('incident'), ('incident_component'), ('work_order'),
        ('maintenance_record'), ('sensor_reading'), ('maintenance_alert'), ('audit_log')
), actual(table_name, row_count) AS (
    SELECT 'location', count(*) FROM location UNION ALL
    SELECT 'component_category', count(*) FROM component_category UNION ALL
    SELECT 'component', count(*) FROM component UNION ALL
    SELECT 'technician', count(*) FROM technician UNION ALL
    SELECT 'assessment', count(*) FROM assessment UNION ALL
    SELECT 'incident', count(*) FROM incident UNION ALL
    SELECT 'incident_component', count(*) FROM incident_component UNION ALL
    SELECT 'work_order', count(*) FROM work_order UNION ALL
    SELECT 'maintenance_record', count(*) FROM maintenance_record UNION ALL
    SELECT 'sensor_reading', count(*) FROM sensor_reading UNION ALL
    SELECT 'maintenance_alert', count(*) FROM maintenance_alert UNION ALL
    SELECT 'audit_log', count(*) FROM audit_log
)
SELECT e.table_name, coalesce(a.row_count, 0) AS row_count
FROM expected e LEFT JOIN actual a USING (table_name)
ORDER BY e.table_name;

-- The explicit expected list above ensures a zero-count table is still displayed.

-- Join: open incidents and every affected component.
SELECT i.incident_number, i.severity, c.asset_tag, c.name, ic.impact_type
FROM incident i JOIN incident_component ic USING (incident_id) JOIN component c USING (component_id)
WHERE i.status IN ('OPEN','INVESTIGATING') ORDER BY i.incident_number, ic.impact_type;

-- Aggregation: component history, latest score, and maintenance spend.
WITH assessment_summary AS (
    SELECT component_id, count(*) AS assessments, round(avg(health_score),2) AS average_health
    FROM assessment GROUP BY component_id
), maintenance_summary AS (
    SELECT w.component_id, coalesce(sum(m.actual_cost),0) AS actual_maintenance_cost
    FROM work_order w LEFT JOIN maintenance_record m USING (work_order_id)
    GROUP BY w.component_id
)
SELECT c.asset_tag, coalesce(a.assessments,0) AS assessments,
       a.average_health, coalesce(ms.actual_maintenance_cost,0) AS actual_maintenance_cost
FROM component c LEFT JOIN assessment_summary a USING (component_id)
LEFT JOIN maintenance_summary ms USING (component_id)
ORDER BY c.asset_tag;

-- Correlated subquery: components whose latest score is below 70.
SELECT c.asset_tag, a.health_score, a.assessed_at
FROM component c JOIN assessment a USING (component_id)
WHERE a.assessed_at = (SELECT max(a2.assessed_at) FROM assessment a2 WHERE a2.component_id=a.component_id)
  AND a.health_score < 70;

-- Window function: rank each component's assessments newest first.
SELECT c.asset_tag, a.assessed_at, a.health_score,
       row_number() OVER (PARTITION BY c.component_id ORDER BY a.assessed_at DESC) AS recency_rank
FROM component c JOIN assessment a USING (component_id);

-- Constraint sanity checks: both results should be zero.
SELECT count(*) AS invalid_scores FROM assessment WHERE health_score NOT BETWEEN 0 AND 100;
SELECT count(*) AS broken_incident_links FROM incident_component ic
LEFT JOIN incident i USING (incident_id) LEFT JOIN component c USING (component_id)
WHERE i.incident_id IS NULL OR c.component_id IS NULL;
