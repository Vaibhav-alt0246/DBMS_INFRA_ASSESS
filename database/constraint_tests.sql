-- InfraAssess Phase 1 constraint tests.
-- Run only after schema.sql and seed.sql against the test database:
--   psql -X --set ON_ERROR_STOP=1 -d infraassess_test -f database/constraint_tests.sql
--
-- Each test uses an anonymous DO block. An expected violation is caught inside
-- the block and rolled back by PostgreSQL's exception subtransaction. If the
-- operation unexpectedly succeeds, the block raises an uncaught error. Any
-- unrelated SQL error is also uncaught.

-- 1. Assessment health_score must be between 0 and 100 (SQLSTATE 23514).
DO $$
DECLARE
    v_component_id bigint;
    v_technician_id bigint;
BEGIN
    SELECT component_id INTO STRICT v_component_id FROM component ORDER BY component_id LIMIT 1;
    SELECT technician_id INTO STRICT v_technician_id FROM technician ORDER BY technician_id LIMIT 1;

    BEGIN
        INSERT INTO assessment (component_id, technician_id, assessed_at, health_score, condition_status, findings)
        VALUES (v_component_id, v_technician_id, clock_timestamp(), -1, 'CRITICAL', 'Expected constraint test row.');
        RAISE EXCEPTION 'Unexpected success: negative assessment health_score was accepted';
    EXCEPTION WHEN SQLSTATE '23514' THEN
        RAISE NOTICE 'PASS: negative assessment health_score rejected with SQLSTATE 23514';
    END;
END $$;

-- 2. MaintenanceRecord actual_cost must be non-negative (SQLSTATE 23514).
DO $$
DECLARE
    v_work_order_id bigint;
    v_technician_id bigint;
BEGIN
    SELECT work_order_id INTO STRICT v_work_order_id FROM work_order ORDER BY work_order_id LIMIT 1;
    SELECT technician_id INTO STRICT v_technician_id FROM technician ORDER BY technician_id LIMIT 1;

    BEGIN
        INSERT INTO maintenance_record (work_order_id, technician_id, performed_at, action_taken, actual_cost, outcome)
        VALUES (v_work_order_id, v_technician_id, clock_timestamp(), 'Expected constraint test row.', -0.01, 'PARTIAL');
        RAISE EXCEPTION 'Unexpected success: negative maintenance actual_cost was accepted';
    EXCEPTION WHEN SQLSTATE '23514' THEN
        RAISE NOTICE 'PASS: negative maintenance actual_cost rejected with SQLSTATE 23514';
    END;
END $$;

-- 3. A nonexistent component_id must be rejected by the assessment FK (SQLSTATE 23503).
DO $$
DECLARE
    v_technician_id bigint;
    v_existing_component_id bigint;
BEGIN
    SELECT technician_id INTO STRICT v_technician_id FROM technician ORDER BY technician_id LIMIT 1;
    SELECT component_id INTO STRICT v_existing_component_id FROM component ORDER BY component_id DESC LIMIT 1;

    BEGIN
        INSERT INTO assessment (component_id, technician_id, assessed_at, health_score, condition_status, findings)
        VALUES (v_existing_component_id + 1000000, v_technician_id, clock_timestamp(), 50, 'POOR', 'Expected constraint test row.');
        RAISE EXCEPTION 'Unexpected success: invalid assessment component_id was accepted';
    EXCEPTION WHEN SQLSTATE '23503' THEN
        RAISE NOTICE 'PASS: invalid assessment component_id rejected with SQLSTATE 23503';
    END;
END $$;

-- 4. A component with historical assessments cannot be deleted (SQLSTATE 23503).
DO $$
DECLARE
    v_component_id bigint;
    v_constraint_name text;
    v_returned_sqlstate text;
BEGIN
    SELECT component_id INTO STRICT v_component_id FROM assessment ORDER BY assessment_id LIMIT 1;

    BEGIN
        DELETE FROM component WHERE component_id = v_component_id;
        RAISE EXCEPTION 'Unexpected success: component with historical records was deleted';
    -- PostgreSQL reports foreign_key_violation for this RESTRICT dependency.
    EXCEPTION WHEN foreign_key_violation OR restrict_violation THEN
        GET STACKED DIAGNOSTICS
            v_constraint_name = CONSTRAINT_NAME,
            v_returned_sqlstate = RETURNED_SQLSTATE;
        IF v_returned_sqlstate NOT IN ('23503', '23001') THEN
            RAISE EXCEPTION 'Unexpected SQLSTATE while deleting component: %', v_returned_sqlstate;
        END IF;
        IF v_constraint_name IS DISTINCT FROM 'assessment_component_id_fkey' THEN
            RAISE EXCEPTION 'Unexpected foreign-key rejection while deleting component: constraint %', v_constraint_name;
        END IF;
        RAISE NOTICE 'PASS: component deletion rejected by assessment_component_id_fkey (SQLSTATE %)', v_returned_sqlstate;
    END;
END $$;

-- 5. An incident with dependent IncidentComponent/WorkOrder rows cannot be deleted.
DO $$
DECLARE
    v_incident_id bigint;
    v_constraint_name text;
    v_returned_sqlstate text;
BEGIN
    SELECT incident_id INTO STRICT v_incident_id FROM incident_component ORDER BY incident_id LIMIT 1;

    BEGIN
        DELETE FROM incident WHERE incident_id = v_incident_id;
        RAISE EXCEPTION 'Unexpected success: incident with dependent records was deleted';
    EXCEPTION WHEN foreign_key_violation OR restrict_violation THEN
        GET STACKED DIAGNOSTICS
            v_constraint_name = CONSTRAINT_NAME,
            v_returned_sqlstate = RETURNED_SQLSTATE;
        IF v_returned_sqlstate NOT IN ('23503', '23001') THEN
            RAISE EXCEPTION 'Unexpected SQLSTATE while deleting incident: %', v_returned_sqlstate;
        END IF;
        IF v_constraint_name IS DISTINCT FROM 'incident_component_incident_id_fkey' THEN
            RAISE EXCEPTION 'Unexpected foreign-key rejection while deleting incident: constraint %', v_constraint_name;
        END IF;
        RAISE NOTICE 'PASS: incident deletion rejected by incident_component_incident_id_fkey (SQLSTATE %)', v_returned_sqlstate;
    END;
END $$;
