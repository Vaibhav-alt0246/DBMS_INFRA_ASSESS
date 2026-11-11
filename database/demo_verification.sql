-- Phase 7 checks after demo_incidents.sql. Expected incident count: 25
SELECT count(*) AS incident_count FROM incident;
SELECT count(*) AS synthetic_incident_count FROM incident WHERE incident_number LIKE 'INC-DEMO-%';
SELECT count(*) AS duplicate_incident_numbers FROM (SELECT incident_number FROM incident GROUP BY incident_number HAVING count(*) > 1) d;
SELECT count(*) AS broken_demo_component_links
FROM incident_component ic JOIN incident i USING (incident_id)
LEFT JOIN component c USING (component_id)
WHERE i.incident_number LIKE 'INC-DEMO-%' AND c.component_id IS NULL;
