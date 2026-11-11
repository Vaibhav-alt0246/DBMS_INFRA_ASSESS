-- InfraAssess Phase 2 trigger logic. Run after schema.sql and seed.sql.
-- Safe to rerun: functions are replaced and triggers/indexes are recreated idempotently.

ALTER TABLE work_order ADD COLUMN IF NOT EXISTS completed_at timestamptz;

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_maintenance_alert
    ON maintenance_alert (component_id, alert_type)
    WHERE status IN ('OPEN', 'ACKNOWLEDGED');

CREATE OR REPLACE FUNCTION fn_component_set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at := clock_timestamp(); RETURN NEW; END;
$$;

CREATE OR REPLACE FUNCTION fn_audit_incident()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log(entity_type, entity_id, action, new_values, changed_by)
        VALUES ('incident', NEW.incident_id, TG_OP, to_jsonb(NEW), current_setting('app.user', true));
    ELSIF ROW(OLD.*) IS DISTINCT FROM ROW(NEW.*) THEN
        INSERT INTO audit_log(entity_type, entity_id, action, old_values, new_values, changed_by)
        VALUES ('incident', NEW.incident_id, TG_OP, to_jsonb(OLD), to_jsonb(NEW), current_setting('app.user', true));
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fn_audit_work_order()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log(entity_type, entity_id, action, new_values, changed_by)
        VALUES ('work_order', NEW.work_order_id, TG_OP, to_jsonb(NEW), current_setting('app.user', true));
    ELSIF ROW(OLD.*) IS DISTINCT FROM ROW(NEW.*) THEN
        INSERT INTO audit_log(entity_type, entity_id, action, old_values, new_values, changed_by)
        VALUES ('work_order', NEW.work_order_id, TG_OP, to_jsonb(OLD), to_jsonb(NEW), current_setting('app.user', true));
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fn_assessment_create_alert()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.health_score <= 70 THEN
        PERFORM pg_advisory_xact_lock(
            hashtextextended(NEW.component_id::text || ':CRITICAL_HEALTH', 0)
        );
        INSERT INTO maintenance_alert(component_id, assessment_id, alert_type, status, message)
        SELECT NEW.component_id, NEW.assessment_id, 'CRITICAL_HEALTH', 'OPEN',
               'Health score crossed the critical threshold; review corrective work order.'
        WHERE NOT EXISTS (
            SELECT 1 FROM maintenance_alert
            WHERE component_id = NEW.component_id
              AND alert_type = 'CRITICAL_HEALTH'
              AND status IN ('OPEN', 'ACKNOWLEDGED')
        );
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fn_validate_work_order_completion()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = 'COMPLETED' THEN
        IF NEW.completed_at IS NULL THEN
            RAISE EXCEPTION 'Work order % requires completed_at', NEW.work_order_number USING ERRCODE = '23514';
        END IF;
        IF NEW.completion_notes IS NULL OR btrim(NEW.completion_notes) = '' THEN
            RAISE EXCEPTION 'Work order % requires completion_notes', NEW.work_order_number USING ERRCODE = '23514';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM maintenance_record WHERE work_order_id = NEW.work_order_id) THEN
            RAISE EXCEPTION 'Work order % requires a maintenance_record', NEW.work_order_number USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_component_set_updated_at ON component;
CREATE TRIGGER trg_component_set_updated_at BEFORE UPDATE ON component
FOR EACH ROW EXECUTE FUNCTION fn_component_set_updated_at();

DROP TRIGGER IF EXISTS trg_incident_audit ON incident;
CREATE TRIGGER trg_incident_audit AFTER INSERT OR UPDATE ON incident
FOR EACH ROW EXECUTE FUNCTION fn_audit_incident();

DROP TRIGGER IF EXISTS trg_work_order_audit ON work_order;
CREATE TRIGGER trg_work_order_audit AFTER INSERT OR UPDATE ON work_order
FOR EACH ROW EXECUTE FUNCTION fn_audit_work_order();

DROP TRIGGER IF EXISTS trg_assessment_create_alert ON assessment;
CREATE TRIGGER trg_assessment_create_alert AFTER INSERT OR UPDATE OF component_id, health_score ON assessment
FOR EACH ROW EXECUTE FUNCTION fn_assessment_create_alert();

DROP TRIGGER IF EXISTS trg_work_order_validate_completion ON work_order;
CREATE TRIGGER trg_work_order_validate_completion BEFORE INSERT OR UPDATE OF status, completed_at, completion_notes ON work_order
FOR EACH ROW EXECUTE FUNCTION fn_validate_work_order_completion();
