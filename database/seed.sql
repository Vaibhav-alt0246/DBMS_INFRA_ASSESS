BEGIN;

INSERT INTO location (location_code,name,address,region) VALUES
 ('LOC-NORTH','North River Bridge','12 River Road','North'),
 ('LOC-CENTRAL','Central Water Plant','8 Utility Avenue','Central'),
 ('LOC-EAST','East Transit Depot','44 Depot Lane','East')
ON CONFLICT (location_code) DO NOTHING;

INSERT INTO component_category (category_code,name,description) VALUES
 ('BRIDGE','Bridge Structure','Load-bearing bridge assets'),
 ('PUMP','Water Pump','Pumps and pumping equipment'),
 ('ELECTRICAL','Electrical Panel','Power distribution equipment')
ON CONFLICT (category_code) DO NOTHING;

INSERT INTO technician (employee_code,full_name,email,specialty) VALUES
 ('TECH-001','Asha Menon','asha.menon@example.org','Structural inspection'),
 ('TECH-002','Ravi Shah','ravi.shah@example.org','Mechanical maintenance'),
 ('TECH-003','Mina Das','mina.das@example.org','Electrical systems')
ON CONFLICT (employee_code) DO NOTHING;

INSERT INTO component (asset_tag,location_id,category_id,name,status,installed_on)
SELECT v.asset_tag,l.location_id,c.category_id,v.name,v.status,v.installed_on::date
FROM (VALUES
 ('AST-BR-001','LOC-NORTH','BRIDGE','North span bearing','DEGRADED','2012-05-10'),
 ('AST-BR-002','LOC-NORTH','BRIDGE','North span expansion joint','OPERATIONAL','2012-05-10'),
 ('AST-PU-001','LOC-CENTRAL','PUMP','Raw water pump A','DEGRADED','2018-03-22'),
 ('AST-EL-001','LOC-EAST','ELECTRICAL','Depot main panel','OPERATIONAL','2020-11-01')
) AS v(asset_tag,location_code,category_code,name,status,installed_on)
JOIN location l USING (location_code)
JOIN component_category c USING (category_code)
ON CONFLICT (asset_tag) DO NOTHING;

INSERT INTO assessment (component_id,technician_id,assessed_at,health_score,condition_status,findings)
SELECT c.component_id,t.technician_id,v.assessed_at::timestamptz,v.health_score,v.condition_status,v.findings
FROM (VALUES
 ('AST-BR-001','TECH-001','2025-01-15 09:00+05:30',62.00,'POOR','Bearing corrosion and visible surface cracking.'),
 ('AST-BR-001','TECH-001','2025-07-15 09:00+05:30',55.00,'CRITICAL','Cracking has progressed; load monitoring recommended.'),
 ('AST-BR-002','TECH-001','2025-07-15 10:00+05:30',88.00,'GOOD','Expansion movement within expected range.'),
 ('AST-PU-001','TECH-002','2025-06-20 11:00+05:30',68.00,'POOR','Vibration and seal leakage observed.'),
 ('AST-EL-001','TECH-003','2025-06-22 14:00+05:30',94.00,'GOOD','Thermal scan shows no abnormal hotspots.')
) AS v(asset_tag,employee_code,assessed_at,health_score,condition_status,findings)
JOIN component c USING (asset_tag) JOIN technician t USING (employee_code)
WHERE NOT EXISTS (SELECT 1 FROM assessment a WHERE a.component_id=c.component_id AND a.assessed_at=v.assessed_at::timestamptz);

INSERT INTO incident (incident_number,reported_at,severity,status,title,description,resolved_at) VALUES
 ('INC-2025-001','2025-07-16 08:30+05:30','HIGH','OPEN','North bearing deterioration','Repeated assessment findings indicate unsafe bearing condition.',NULL),
 ('INC-2025-002','2025-06-21 12:00+05:30','MEDIUM','RESOLVED','Pump seal leakage','Raw water pump A leaked at the drive-end seal.','2025-06-25 16:00+05:30'),
 ('INC-2025-003','2025-02-03 10:00+05:30','LOW','CLOSED','Expansion joint noise','Noise reported during heavy traffic; inspection found no structural failure.','2025-02-05 15:00+05:30')
ON CONFLICT (incident_number) DO NOTHING;

INSERT INTO incident_component (incident_id,component_id,impact_type,notes)
SELECT i.incident_id,c.component_id,v.impact_type,v.notes FROM (VALUES
 ('INC-2025-001','AST-BR-001','PRIMARY','Bearing is the directly affected asset.'),
 ('INC-2025-001','AST-BR-002','SECONDARY','Adjacent joint requires observation.'),
 ('INC-2025-002','AST-PU-001','PRIMARY','Seal leakage confirmed.')
) v(incident_number,asset_tag,impact_type,notes)
JOIN incident i USING (incident_number) JOIN component c USING (asset_tag)
ON CONFLICT DO NOTHING;

INSERT INTO work_order (work_order_number,incident_id,component_id,technician_id,work_type,status,planned_start,planned_end,completed_at,estimated_cost,completion_notes)
SELECT v.work_order_number,i.incident_id,c.component_id,t.technician_id,v.work_type,v.status,v.planned_start::date,v.planned_end::date,v.completed_at::timestamptz,v.estimated_cost,v.completion_notes
FROM (VALUES
 ('WO-2025-001','INC-2025-001','AST-BR-001','TECH-001','CORRECTIVE','ASSIGNED','2025-08-01','2025-08-05',NULL,18500.00,NULL),
 ('WO-2025-002','INC-2025-002','AST-PU-001','TECH-002','CORRECTIVE','COMPLETED','2025-06-23','2025-06-25','2025-06-25 16:00+05:30',2400.00,'Seal replaced and pump tested successfully.'),
 ('WO-2025-003',NULL,'AST-EL-001','TECH-003','PREVENTIVE','PLANNED','2025-09-10','2025-09-10',NULL,650.00,NULL)
) v(work_order_number,incident_number,asset_tag,employee_code,work_type,status,planned_start,planned_end,completed_at,estimated_cost,completion_notes)
LEFT JOIN incident i USING (incident_number) JOIN component c USING (asset_tag) JOIN technician t USING (employee_code)
ON CONFLICT (work_order_number) DO NOTHING;

INSERT INTO maintenance_record (work_order_id,technician_id,performed_at,action_taken,actual_cost,outcome)
SELECT w.work_order_id,t.technician_id,v.performed_at::timestamptz,v.action_taken,v.actual_cost,v.outcome
FROM (VALUES ('WO-2025-002','TECH-002','2025-06-25 15:00+05:30','Replaced mechanical seal and aligned coupling.',2180.00,'SUCCESSFUL')) v(work_order_number,employee_code,performed_at,action_taken,actual_cost,outcome)
JOIN work_order w USING (work_order_number) JOIN technician t USING (employee_code)
WHERE NOT EXISTS (SELECT 1 FROM maintenance_record m WHERE m.work_order_id=w.work_order_id);

INSERT INTO sensor_reading (component_id,recorded_at,sensor_type,reading_value,unit)
SELECT c.component_id,v.recorded_at::timestamptz,v.sensor_type,v.reading_value,v.unit FROM (VALUES
 ('AST-PU-001','2025-06-20 10:00+05:30','VIBRATION',7.20,'mm/s'),
 ('AST-PU-001','2025-06-21 10:00+05:30','VIBRATION',8.10,'mm/s'),
 ('AST-BR-001','2025-07-15 08:00+05:30','STRAIN',42.50,'μεstrain'),
 ('AST-EL-001','2025-06-22 13:00+05:30','TEMPERATURE',38.20,'C')
) v(asset_tag,recorded_at,sensor_type,reading_value,unit) JOIN component c USING (asset_tag)
WHERE NOT EXISTS (SELECT 1 FROM sensor_reading s WHERE s.component_id=c.component_id AND s.recorded_at=v.recorded_at::timestamptz AND s.sensor_type=v.sensor_type);

INSERT INTO maintenance_alert (component_id,assessment_id,alert_type,status,message)
SELECT c.component_id,a.assessment_id,'CRITICAL_HEALTH','OPEN','Health score crossed the critical threshold; review corrective work order.'
FROM assessment a JOIN component c ON c.component_id=a.component_id
WHERE a.health_score <= 70
  AND a.assessed_at='2025-07-15 09:00+05:30'
ON CONFLICT (component_id,assessment_id,alert_type) DO NOTHING;

COMMIT;
