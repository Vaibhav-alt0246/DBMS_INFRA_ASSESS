-- Phase 4 transaction tests. Run after schema.sql, seed.sql, triggers.sql,
-- and procedures.sql. Use ON_ERROR_STOP so unexpected SQL errors stop the run.
-- All changes to project rows are rolled back.

\set ON_ERROR_STOP on

-- COMMIT demonstration with an isolated temporary table.
CREATE TEMP TABLE transaction_lab_rows (id integer PRIMARY KEY, note text) ON COMMIT PRESERVE ROWS;
BEGIN;
INSERT INTO transaction_lab_rows VALUES (1, 'committed row');
COMMIT;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM transaction_lab_rows WHERE id=1) THEN
        RAISE EXCEPTION 'COMMIT test failed: committed row is missing';
    END IF;
    RAISE NOTICE 'PASS: COMMIT persisted isolated test data';
END $$;

-- ROLLBACK demonstration and verification.
BEGIN;
INSERT INTO transaction_lab_rows VALUES (2, 'rolled back row');
ROLLBACK;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM transaction_lab_rows WHERE id=2) THEN
        RAISE EXCEPTION 'ROLLBACK test failed: rolled-back row remains';
    END IF;
    RAISE NOTICE 'PASS: ROLLBACK removed isolated test data';
END $$;

-- Atomic failure: the procedure's invalid maintenance insert must not leave
-- either a maintenance row or a completed work order behind.
DO $$
DECLARE v_before_status varchar(15); v_before_count bigint; v_tech bigint;
BEGIN
    SELECT status INTO STRICT v_before_status FROM work_order WHERE work_order_number='WO-2025-003';
    SELECT count(*) INTO v_before_count FROM maintenance_record m JOIN work_order w USING (work_order_id)
    WHERE w.work_order_number='WO-2025-003';
    SELECT technician_id INTO STRICT v_tech FROM technician ORDER BY technician_id LIMIT 1;
    BEGIN
        CALL sp_complete_work_order('WO-2025-003', v_tech, 'Expected failing transaction', -1, 'SUCCESSFUL', clock_timestamp(), 'Should roll back');
        RAISE EXCEPTION 'atomicity test failed: invalid procedure call succeeded';
    EXCEPTION WHEN check_violation THEN
        NULL; -- expected actual_cost CHECK violation; its subtransaction is rolled back
    END;
    IF (SELECT status FROM work_order WHERE work_order_number='WO-2025-003') <> v_before_status
       OR (SELECT count(*) FROM maintenance_record m JOIN work_order w USING (work_order_id)
           WHERE w.work_order_number='WO-2025-003') <> v_before_count THEN
        RAISE EXCEPTION 'atomicity test failed: partial procedure state remains';
    END IF;
    RAISE NOTICE 'PASS: failed procedure left no partial state';
END $$;

-- Transactional consistency: complete a seeded open work order, verify both
-- records in one transaction, then roll back and verify the seed is unchanged.
BEGIN;
DO $$ DECLARE v_tech bigint; v_id bigint; BEGIN
    SELECT technician_id INTO STRICT v_tech FROM technician ORDER BY technician_id LIMIT 1;
    CALL sp_complete_work_order('WO-2025-001', v_tech, 'Temporary transaction test repair', 10, 'SUCCESSFUL', clock_timestamp(), 'Temporary completion');
    SELECT work_order_id INTO STRICT v_id FROM work_order WHERE work_order_number='WO-2025-001';
    IF NOT EXISTS (SELECT 1 FROM work_order WHERE work_order_id=v_id AND status='COMPLETED')
       OR NOT EXISTS (SELECT 1 FROM maintenance_record WHERE work_order_id=v_id AND action_taken='Temporary transaction test repair') THEN
        RAISE EXCEPTION 'procedure transaction consistency test failed';
    END IF;
END $$;
ROLLBACK;
DO $$ BEGIN
    IF (SELECT status FROM work_order WHERE work_order_number='WO-2025-001') <> 'ASSIGNED'
       OR EXISTS (SELECT 1 FROM maintenance_record m JOIN work_order w USING (work_order_id)
                  WHERE w.work_order_number='WO-2025-001' AND m.action_taken='Temporary transaction test repair') THEN
        RAISE EXCEPTION 'procedure rollback failed: seeded work order changed';
    END IF;
    RAISE NOTICE 'PASS: work-order completion was transactionally rolled back';
END $$;

DROP TABLE transaction_lab_rows;
