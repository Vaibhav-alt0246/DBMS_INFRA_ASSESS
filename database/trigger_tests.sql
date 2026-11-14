-- Run after schema.sql, seed.sql, and triggers.sql:
-- psql -X --set ON_ERROR_STOP=1 -d infraassess_test -f database/trigger_tests.sql
-- All changes are inside one transaction and rolled back at the end.
BEGIN;

-- 1. Component updated_at changes on a legitimate update.
DO $$
DECLARE v_id bigint; v_before timestamptz; v_after timestamptz;
BEGIN
    SELECT component_id, updated_at INTO STRICT v_id, v_before FROM component ORDER BY component_id LIMIT 1;
    PERFORM pg_sleep(0.01);
    UPDATE component SET name = name WHERE component_id = v_id;
    SELECT updated_at INTO v_after FROM component WHERE component_id = v_id;
    IF v_after <= v_before THEN RAISE EXCEPTION 'updated_at did not advance'; END IF;
    RAISE NOTICE 'PASS: component updated_at refreshed';
END $$;

-- 2. Incident INSERT and UPDATE produce correct audit rows.
DO $$
DECLARE v_id bigint; v_insert audit_log%ROWTYPE; v_update audit_log%ROWTYPE;
BEGIN
    INSERT INTO incident (incident_number, reported_at, severity, status, title, description)
    VALUES ('INC-TRIGGER-TEST', clock_timestamp(), 'LOW', 'OPEN', 'Trigger test', 'Inserted for trigger test')
    RETURNING incident_id INTO v_id;
    SELECT * INTO STRICT v_insert FROM audit_log WHERE entity_type='incident' AND entity_id=v_id AND action='INSERT';
    IF v_insert.new_values->>'incident_number' <> 'INC-TRIGGER-TEST' OR v_insert.old_values IS NOT NULL THEN
        RAISE EXCEPTION 'incident INSERT audit payload is incorrect';
    END IF;
    UPDATE incident SET title = 'Trigger test updated' WHERE incident_id = v_id;
    SELECT * INTO STRICT v_update FROM audit_log WHERE entity_type='incident' AND entity_id=v_id AND action='UPDATE';
    IF v_update.old_values->>'title' <> 'Trigger test' OR v_update.new_values->>'title' <> 'Trigger test updated' THEN
        RAISE EXCEPTION 'incident UPDATE audit payload is incorrect';
    END IF;
    RAISE NOTICE 'PASS: incident INSERT/UPDATE audit records';
END $$;

-- 3. Work-order INSERT and UPDATE produce correct audit rows.
DO $$
DECLARE v_id bigint; v_insert audit_log%ROWTYPE; v_update audit_log%ROWTYPE; v_component bigint; v_tech bigint;
BEGIN
    SELECT component_id INTO STRICT v_component FROM component ORDER BY component_id LIMIT 1;
    SELECT technician_id INTO STRICT v_tech FROM technician ORDER BY technician_id LIMIT 1;
    INSERT INTO work_order (work_order_number, component_id, technician_id, work_type, status, planned_start, estimated_cost)
    VALUES ('WO-TRIGGER-TEST', v_component, v_tech, 'PREVENTIVE', 'PLANNED', current_date, 1)
    RETURNING work_order_id INTO v_id;
    SELECT * INTO STRICT v_insert FROM audit_log WHERE entity_type='work_order' AND entity_id=v_id AND action='INSERT';
    IF v_insert.new_values->>'work_order_number' <> 'WO-TRIGGER-TEST' THEN RAISE EXCEPTION 'work-order INSERT audit is incorrect'; END IF;
    UPDATE work_order SET status = 'ASSIGNED' WHERE work_order_id = v_id;
    SELECT * INTO STRICT v_update FROM audit_log WHERE entity_type='work_order' AND entity_id=v_id AND action='UPDATE';
    IF v_update.old_values->>'status' <> 'PLANNED' OR v_update.new_values->>'status' <> 'ASSIGNED' THEN RAISE EXCEPTION 'work-order UPDATE audit is incorrect'; END IF;
    RAISE NOTICE 'PASS: work-order INSERT/UPDATE audit records';
END $$;

-- 4-6. Alert creation, active duplicate suppression, and re-alert after resolution.
DO $$
DECLARE v_component bigint; v_tech bigint; v_first bigint; v_count integer; v_second bigint;
BEGIN
    SELECT component_id INTO STRICT v_component FROM component WHERE asset_tag='AST-EL-001';
    SELECT technician_id INTO STRICT v_tech FROM technician ORDER BY technician_id LIMIT 1;
    INSERT INTO assessment(component_id, technician_id, assessed_at, health_score, condition_status, findings)
    VALUES (v_component, v_tech, clock_timestamp(), 50, 'CRITICAL', 'Trigger alert test') RETURNING assessment_id INTO v_first;
    SELECT count(*) INTO v_count FROM maintenance_alert WHERE component_id=v_component AND alert_type='CRITICAL_HEALTH' AND status IN ('OPEN','ACKNOWLEDGED');
    IF v_count <> 1 THEN RAISE EXCEPTION 'low-health assessment did not create exactly one active alert'; END IF;
    INSERT INTO assessment(component_id, technician_id, assessed_at, health_score, condition_status, findings)
    VALUES (v_component, v_tech, clock_timestamp(), 40, 'CRITICAL', 'Duplicate alert test');
    SELECT count(*) INTO v_count FROM maintenance_alert WHERE component_id=v_component AND alert_type='CRITICAL_HEALTH' AND status IN ('OPEN','ACKNOWLEDGED');
    IF v_count <> 1 THEN RAISE EXCEPTION 'repeated low-health assessment created a duplicate active alert'; END IF;
    UPDATE maintenance_alert SET status='RESOLVED', verification_notes='Operator checked asset' WHERE component_id=v_component AND alert_type='CRITICAL_HEALTH' AND status='OPEN';
    INSERT INTO assessment(component_id, technician_id, assessed_at, health_score, condition_status, findings)
    VALUES (v_component, v_tech, clock_timestamp(), 45, 'CRITICAL', 'Re-alert test') RETURNING assessment_id INTO v_second;
    IF v_second = v_first THEN RAISE EXCEPTION 'new assessment did not create a new alert after resolution'; END IF;
    SELECT count(*) INTO v_count FROM maintenance_alert WHERE component_id=v_component AND alert_type='CRITICAL_HEALTH' AND status='OPEN';
    IF v_count <> 1 THEN RAISE EXCEPTION 'resolved alert did not permit a new active alert'; END IF;
    RAISE NOTICE 'PASS: low-health alert lifecycle';
END $$;

-- 7. Completion without a maintenance record is rejected with the trigger error.
DO $$
DECLARE v_id bigint; v_component bigint; v_tech bigint;
BEGIN
    SELECT component_id INTO STRICT v_component FROM component ORDER BY component_id LIMIT 1;
    SELECT technician_id INTO STRICT v_tech FROM technician ORDER BY technician_id LIMIT 1;
    INSERT INTO work_order(work_order_number, component_id, technician_id, work_type, status, planned_start, estimated_cost)
    VALUES ('WO-COMPLETION-INVALID', v_component, v_tech, 'CORRECTIVE', 'PLANNED', current_date, 1) RETURNING work_order_id INTO v_id;
    BEGIN
        UPDATE work_order SET status='COMPLETED', completed_at=clock_timestamp(), completion_notes='No repair row' WHERE work_order_id=v_id;
        RAISE EXCEPTION 'invalid completion unexpectedly succeeded';
    EXCEPTION WHEN SQLSTATE '23514' THEN
        RAISE NOTICE 'PASS: completion without maintenance record rejected';
    END;
END $$;

-- 8. A maintenance record followed by completion succeeds.
DO $$
DECLARE v_id bigint; v_component bigint; v_tech bigint;
BEGIN
    SELECT component_id INTO STRICT v_component FROM component ORDER BY component_id LIMIT 1;
    SELECT technician_id INTO STRICT v_tech FROM technician ORDER BY technician_id LIMIT 1;
    INSERT INTO work_order(work_order_number, component_id, technician_id, work_type, status, planned_start, estimated_cost)
    VALUES ('WO-COMPLETION-VALID', v_component, v_tech, 'CORRECTIVE', 'PLANNED', current_date, 1) RETURNING work_order_id INTO v_id;
    INSERT INTO maintenance_record(work_order_id, technician_id, performed_at, action_taken, actual_cost, outcome)
    VALUES (v_id, v_tech, clock_timestamp(), 'Completed trigger test repair', 1, 'SUCCESSFUL');
    UPDATE work_order SET status='COMPLETED', completed_at=clock_timestamp(), completion_notes='Repair recorded' WHERE work_order_id=v_id;
    IF NOT EXISTS (SELECT 1 FROM work_order WHERE work_order_id=v_id AND status='COMPLETED') THEN
        RAISE EXCEPTION 'valid completion did not persist';
    END IF;
    RAISE NOTICE 'PASS: valid completion workflow';
END $$;

ROLLBACK;
