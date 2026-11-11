-- Runnable Phase 3 examples. Run after views.sql, functions.sql, and procedures.sql.

-- Latest row per component, using the reporting view.
SELECT * FROM v_component_current_health ORDER BY asset_tag;

-- Nested query: components with health below the average latest health.
SELECT asset_tag, health_score FROM v_component_current_health
WHERE health_score < (SELECT avg(health_score) FROM v_component_current_health WHERE health_score IS NOT NULL);

-- Correlated query: components with at least two assessments.
SELECT c.asset_tag FROM component c
WHERE (SELECT count(*) FROM assessment a WHERE a.component_id=c.component_id) >= 2;

-- Inner and left joins, preserving components without incidents.
SELECT c.asset_tag, count(ic.incident_id) AS incident_count
FROM component c LEFT JOIN incident_component ic USING (component_id)
GROUP BY c.component_id, c.asset_tag ORDER BY c.asset_tag;

-- Set operation: components appearing in an incident or a work order.
SELECT component_id FROM incident_component
UNION
SELECT component_id FROM work_order WHERE component_id IS NOT NULL;

-- HAVING: repeated or expensive component histories.
SELECT component_id, count(*) AS assessment_count
FROM assessment GROUP BY component_id HAVING count(*) > 1;

-- NULL handling: missing assessments are labelled, not treated as zero health.
SELECT asset_tag, coalesce(health_score::text, 'NOT ASSESSED') AS health_display
FROM v_component_current_health;

-- CTE recurring-failure and maintenance-cost report.
WITH repeated_failures AS (
    SELECT component_id, count(*) AS failures
    FROM incident_component GROUP BY component_id HAVING count(*) >= 2
), costs AS (
    SELECT component_id, actual_maintenance_cost FROM v_component_failure_summary
)
SELECT c.asset_tag, rf.failures, coalesce(costs.actual_maintenance_cost,0) AS cost
FROM repeated_failures rf JOIN component c USING (component_id) JOIN costs USING (component_id);

-- Window functions: ROW_NUMBER, RANK, and running cost by component.
SELECT c.asset_tag, a.assessed_at, a.health_score,
       row_number() OVER (PARTITION BY a.component_id ORDER BY a.assessed_at DESC) AS recency,
       rank() OVER (PARTITION BY a.component_id ORDER BY a.health_score) AS health_rank,
       avg(a.health_score) OVER (PARTITION BY a.component_id ORDER BY a.assessed_at
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_health_average
FROM assessment a JOIN component c USING (component_id);

-- Full-text search over incident title and description. Parameter example:
-- replace 'bearing deterioration' with a user-supplied search phrase.
SELECT incident_number, title, ts_rank(
    to_tsvector('english', title || ' ' || description),
    websearch_to_tsquery('english', 'bearing deterioration')
) AS relevance
FROM incident
WHERE to_tsvector('english', title || ' ' || description) @@
      websearch_to_tsquery('english', 'bearing deterioration')
ORDER BY relevance DESC;
