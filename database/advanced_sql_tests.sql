-- Phase 3 tests. Run after views.sql, functions.sql, procedures.sql, and triggers.sql.
-- All writes are rolled back.
BEGIN;

DO $$ DECLARE v_id bigint; v_before timestamptz; v_after timestamptz; BEGIN
    SELECT component_id, assessed_at INTO STRICT v_id, v_before FROM v_component_current_health WHERE asset_tag='AST-BR-001';
    SELECT assessed_at INTO v_after FROM assessment WHERE component_id=v_id ORDER BY assessed_at DESC LIMIT 1;
    IF v_before <> v_after THEN RAISE EXCEPTION 'current-health view is inconsistent'; END IF;
    IF (SELECT count(*) FROM v_component_current_health) <> (SELECT count(*) FROM component) THEN RAISE EXCEPTION 'view duplicates components'; END IF;
    RAISE NOTICE 'PASS: view consistency';
END $$;

DO $$ BEGIN
    IF fn_component_latest_health((SELECT component_id FROM component WHERE asset_tag='AST-BR-001')) IS NULL THEN RAISE EXCEPTION 'latest health unexpectedly NULL'; END IF;
    IF fn_component_latest_health((SELECT component_id FROM component WHERE asset_tag='AST-EL-001')) <> 94 THEN RAISE EXCEPTION 'latest health incorrect'; END IF;
    IF fn_component_latest_health((SELECT max(component_id)+1 FROM component)) IS NOT NULL THEN RAISE EXCEPTION 'nonexistent component did not fail'; END IF;
EXCEPTION WHEN SQLSTATE '22023' THEN RAISE NOTICE 'PASS: health function nonexistent-ID rejection'; END $$;

DO $$ DECLARE v_cost numeric; BEGIN
    SELECT fn_component_maintenance_cost(component_id) INTO v_cost FROM component WHERE asset_tag='AST-PU-001';
    IF v_cost <> 2180 THEN RAISE EXCEPTION 'maintenance cost incorrect: %', v_cost; END IF;
    RAISE NOTICE 'PASS: maintenance cost aggregation';
END $$;

DO $$ DECLARE v_id bigint; v_tech bigint; BEGIN
    SELECT technician_id INTO STRICT v_tech FROM technician ORDER BY technician_id LIMIT 1;
    CALL sp_complete_work_order('WO-2025-001', v_tech, 'Phase 3 test repair', 10, 'SUCCESSFUL', clock_timestamp(), 'Completed by procedure');
    SELECT work_order_id INTO STRICT v_id FROM work_order WHERE work_order_number='WO-2025-001';
    IF NOT EXISTS (SELECT 1 FROM work_order WHERE work_order_id=v_id AND status='COMPLETED') THEN RAISE EXCEPTION 'procedure did not complete work order'; END IF;
    RAISE NOTICE 'PASS: completion procedure';
END $$;

DO $$ DECLARE v_tech bigint; BEGIN
    SELECT technician_id INTO STRICT v_tech FROM technician ORDER BY technician_id LIMIT 1;
    BEGIN
        CALL sp_complete_work_order('WO-2025-003', v_tech, 'Invalid negative-cost repair', -1, 'SUCCESSFUL', clock_timestamp(), 'Should fail');
        RAISE EXCEPTION 'invalid procedure call unexpectedly succeeded';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: invalid completion procedure rejected';
    END;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM incident
        WHERE to_tsvector('english', title || ' ' || description) @@ websearch_to_tsquery('english', 'bearing deterioration')
    ) THEN RAISE EXCEPTION 'full-text search did not find seeded incident'; END IF;
    IF EXISTS (SELECT 1 FROM v_component_failure_summary s JOIN component c USING (component_id) WHERE c.asset_tag='AST-PU-001' AND s.actual_maintenance_cost <> 2180) THEN
        RAISE EXCEPTION 'maintenance cost is inflated';
    END IF;
    RAISE NOTICE 'PASS: full-text and aggregate checks';
END $$;

ROLLBACK;
