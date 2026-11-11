-- Phase 3 procedures. Run after functions.sql and triggers.sql.

CREATE OR REPLACE PROCEDURE sp_complete_work_order(
    p_work_order_number varchar,
    p_technician_id bigint,
    p_action_taken text,
    p_actual_cost numeric(12,2),
    p_outcome varchar(20),
    p_completed_at timestamptz,
    p_completion_notes text
)
LANGUAGE plpgsql
AS $$
DECLARE v_work_order_id bigint; v_status varchar(15);
BEGIN
    SELECT work_order_id, status INTO STRICT v_work_order_id, v_status
    FROM work_order WHERE work_order_number = p_work_order_number FOR UPDATE;
    IF v_status IN ('COMPLETED', 'CANCELLED') THEN
        RAISE EXCEPTION 'Work order % cannot transition from status %', p_work_order_number, v_status USING ERRCODE = '55000';
    END IF;
    INSERT INTO maintenance_record(work_order_id, technician_id, performed_at, action_taken, actual_cost, outcome)
    VALUES (v_work_order_id, p_technician_id, coalesce(p_completed_at, clock_timestamp()), p_action_taken, p_actual_cost, p_outcome);
    UPDATE work_order
    SET status='COMPLETED', completed_at=p_completed_at, completion_notes=p_completion_notes
    WHERE work_order_id=v_work_order_id;
END;
$$;
