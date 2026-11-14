-- Phase 7 additive synthetic demonstration incidents.
-- These are not real historical events. Run after database/seed.sql.
-- Safe to rerun: incident_number is a stable natural key and existing rows are untouched.
BEGIN;

INSERT INTO incident (incident_number, reported_at, severity, status, title, description, resolved_at) VALUES
 ('INC-DEMO-001','2025-03-01 08:10+05:30','MEDIUM','RESOLVED','Raw-water pump vibration and seal seepage','Pump A developed increasing vibration with a small drive-end seal leak during morning operation. The likely cause was coupling misalignment and seal wear.','2025-03-04 16:00+05:30'),
 ('INC-DEMO-002','2025-03-03 11:20+05:30','HIGH','INVESTIGATING','Booster pump pressure loss','The distribution booster could not maintain discharge pressure and cycled repeatedly. Operators reported intermittent flow loss and suspected an obstructed suction strainer.',NULL),
 ('INC-DEMO-003','2025-03-05 09:00+05:30','HIGH','OPEN','Bridge bearing overheating','Thermal inspection found an unusually hot bearing at the north bridge span, with grease discoloration and early wear marks. Immediate load observation was recommended.',NULL),
 ('INC-DEMO-004','2025-03-07 15:40+05:30','LOW','CLOSED','Expansion joint rattling under traffic','A metallic rattle was heard at the bridge expansion joint during heavy vehicles. Follow-up inspection found loose fasteners but no structural cracking.','2025-03-09 12:00+05:30'),
 ('INC-DEMO-005','2025-03-10 07:35+05:30','CRITICAL','OPEN','Bridge bearing surface cracking','A repeat inspection identified wider surface cracks and corrosion on the north span bearing. The component was flagged for corrective replacement and restricted loading review.',NULL),
 ('INC-DEMO-006','2025-03-12 10:15+05:30','MEDIUM','RESOLVED','Depot pavement pothole and settlement','A deep pothole and localized pavement settlement formed near the depot entrance after rainfall. The repair crew patched the surface and restored drainage.','2025-03-15 17:00+05:30'),
 ('INC-DEMO-007','2025-03-14 13:05+05:30','HIGH','OPEN','Storm drain blockage at depot','Standing water accumulated beside the east depot after a storm. Inspection found silt and debris blocking the nearest drainage inlet.',NULL),
 ('INC-DEMO-008','2025-03-16 08:50+05:30','HIGH','INVESTIGATING','Buried water-main leakage','Water pressure fell across the central plant yard and wet soil appeared near the service road. The suspected cause was a leaking buried water-main joint.',NULL),
 ('INC-DEMO-009','2025-03-18 16:25+05:30','MEDIUM','RESOLVED','Abnormal plant flow telemetry','Flow telemetry diverged from the mechanical gauge for several hours. Sensor recalibration corrected the reading and no physical leak was found.','2025-03-19 11:00+05:30'),
 ('INC-DEMO-010','2025-03-20 09:30+05:30','CRITICAL','OPEN','Transformer overheating alarm','The electrical panel area reported repeated thermal alarms and a hot connection during peak load. Inspection suspected a loose termination and overloaded phase.',NULL),
 ('INC-DEMO-011','2025-03-22 12:10+05:30','MEDIUM','RESOLVED','Depot power fluctuation','Lights and control equipment experienced short voltage fluctuations at the transit depot. Tightening a feeder connection stabilized the supply.','2025-03-23 15:30+05:30'),
 ('INC-DEMO-012','2025-03-24 06:45+05:30','HIGH','OPEN','HVAC compressor failure','The control room HVAC stopped cooling and the compressor made a grinding noise before shutdown. Refrigerant pressure and compressor bearings require inspection.',NULL),
 ('INC-DEMO-013','2025-03-26 14:00+05:30','MEDIUM','INVESTIGATING','Equipment fan abnormal vibration','A mechanical equipment fan showed a new vibration peak and rattling sound. The working hypothesis is fan imbalance or a worn motor bearing.',NULL),
 ('INC-DEMO-014','2025-03-28 10:35+05:30','LOW','CLOSED','Inspection sensor drift','A handheld inspection sensor gradually reported higher values than the reference instrument. Calibration drift was confirmed and the sensor was recalibrated.','2025-03-29 10:00+05:30'),
 ('INC-DEMO-015','2025-03-30 17:20+05:30','MEDIUM','OPEN','Inconsistent structural telemetry','Remote strain telemetry showed intermittent spikes that were not reproduced during a manual inspection. The sensor mount and wiring are being checked.',NULL),
 ('INC-DEMO-016','2025-04-02 08:30+05:30','HIGH','OPEN','Corrosion on pump casing','Pitting corrosion and flaking coating were observed on the raw-water pump casing. Continued exposure may reduce wall thickness if protective coating is not restored.',NULL),
 ('INC-DEMO-017','2025-04-04 11:45+05:30','MEDIUM','RESOLVED','Preventive bearing wear finding','Scheduled maintenance found early bearing wear before a functional failure. Lubrication and bearing replacement were completed during the planned outage.','2025-04-06 16:20+05:30'),
 ('INC-DEMO-018','2025-04-07 09:15+05:30','LOW','CLOSED','Roadside drainage erosion','Erosion was visible beside the access road after repeated runoff. The shoulder was rebuilt and gravel was compacted around the drainage path.','2025-04-10 13:00+05:30'),
 ('INC-DEMO-019','2025-04-09 15:00+05:30','HIGH','INVESTIGATING','Pump motor intermittent trip','The plant pump motor tripped twice during startup while current readings fluctuated. Electrical insulation and overload protection are under review.',NULL),
 ('INC-DEMO-020','2025-04-11 07:55+05:30','MEDIUM','RESOLVED','Low flow after valve adjustment','Flow dropped after a maintenance valve adjustment and recovered when the valve position was corrected. No component damage was found.','2025-04-12 12:30+05:30'),
 ('INC-DEMO-021','2025-04-14 13:40+05:30','HIGH','OPEN','Bridge deck structural cracking','New longitudinal cracking was reported on the bridge deck near the north span. A structural inspection and traffic-load assessment were requested.',NULL),
 ('INC-DEMO-022','2025-04-16 18:05+05:30','MEDIUM','OPEN','Electrical panel thermal imbalance','A thermal scan found one panel phase substantially warmer than the others. The suspected contributors are contact resistance and unbalanced load.',NULL)
ON CONFLICT (incident_number) DO NOTHING;

-- Link synthetic events to existing components so searches can include asset context.
INSERT INTO incident_component (incident_id, component_id, impact_type, notes)
SELECT i.incident_id, c.component_id, v.impact_type, v.notes
FROM (VALUES
 ('INC-DEMO-001','AST-PU-001','PRIMARY','Pump A is the affected asset.'),
 ('INC-DEMO-002','AST-PU-001','PRIMARY','Booster pressure problem represented by the pump asset.'),
 ('INC-DEMO-003','AST-BR-001','PRIMARY','North span bearing.'),
 ('INC-DEMO-004','AST-BR-002','PRIMARY','Expansion joint.'),
 ('INC-DEMO-005','AST-BR-001','PRIMARY','North span bearing.'),
 ('INC-DEMO-006','AST-EL-001','POTENTIAL','Depot reference component for demonstration context.'),
 ('INC-DEMO-007','AST-EL-001','POTENTIAL','Depot reference component for demonstration context.'),
 ('INC-DEMO-008','AST-PU-001','PRIMARY','Central plant pump context.'),
 ('INC-DEMO-009','AST-PU-001','PRIMARY','Flow instrumentation context.'),
 ('INC-DEMO-010','AST-EL-001','PRIMARY','Electrical panel.'),
 ('INC-DEMO-011','AST-EL-001','PRIMARY','Depot electrical panel.'),
 ('INC-DEMO-012','AST-EL-001','POTENTIAL','Control-room equipment context.'),
 ('INC-DEMO-013','AST-PU-001','POTENTIAL','Mechanical equipment context.'),
 ('INC-DEMO-014','AST-EL-001','POTENTIAL','Inspection instrumentation context.'),
 ('INC-DEMO-015','AST-BR-001','POTENTIAL','Structural telemetry context.'),
 ('INC-DEMO-016','AST-PU-001','PRIMARY','Raw-water pump casing.'),
 ('INC-DEMO-017','AST-BR-001','POTENTIAL','Bearing maintenance context.'),
 ('INC-DEMO-018','AST-BR-002','POTENTIAL','Access and joint context.'),
 ('INC-DEMO-019','AST-PU-001','PRIMARY','Pump motor.'),
 ('INC-DEMO-020','AST-PU-001','PRIMARY','Pump flow.'),
 ('INC-DEMO-021','AST-BR-002','PRIMARY','North bridge deck context.'),
 ('INC-DEMO-022','AST-EL-001','PRIMARY','Electrical panel.')
) v(incident_number, asset_tag, impact_type, notes)
JOIN incident i USING (incident_number)
JOIN component c USING (asset_tag)
ON CONFLICT DO NOTHING;

COMMIT;
