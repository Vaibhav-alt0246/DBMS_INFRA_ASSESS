-- Phase 3 functions. Run after schema.sql and before procedures.sql.

CREATE OR REPLACE FUNCTION fn_component_latest_health(p_component_id bigint)
RETURNS numeric LANGUAGE plpgsql STABLE AS $$
DECLARE v_score numeric;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM component WHERE component_id = p_component_id) THEN
        RAISE EXCEPTION 'Component % does not exist', p_component_id USING ERRCODE = '22023';
    END IF;
    SELECT health_score INTO v_score FROM assessment
    WHERE component_id = p_component_id
    ORDER BY assessed_at DESC, assessment_id DESC LIMIT 1;
    RETURN v_score; -- NULL means the component exists but has no assessment.
END;
$$;

CREATE OR REPLACE FUNCTION fn_component_maintenance_cost(p_component_id bigint)
RETURNS numeric(12,2) LANGUAGE plpgsql STABLE AS $$
DECLARE v_cost numeric(12,2);
BEGIN
    IF NOT EXISTS (SELECT 1 FROM component WHERE component_id = p_component_id) THEN
        RAISE EXCEPTION 'Component % does not exist', p_component_id USING ERRCODE = '22023';
    END IF;
    SELECT coalesce(sum(m.actual_cost), 0)::numeric(12,2) INTO v_cost
    FROM work_order w LEFT JOIN maintenance_record m USING (work_order_id)
    WHERE w.component_id = p_component_id;
    RETURN v_cost;
END;
$$;
