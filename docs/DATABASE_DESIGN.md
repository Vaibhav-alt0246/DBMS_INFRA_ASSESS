# Database design

## Entities and keys

Each table has a surrogate `bigint` primary key except `IncidentComponent`, whose composite primary key is `(incident_id, component_id)`. Stable business identifiers (`location_code`, `asset_tag`, `employee_code`, `incident_number`, and `work_order_number`) are unique. Foreign keys express the ownership and history relationships described in the ERD.

`Assessment` is an immutable-in-practice observation history rather than a current-status column on `Component`. `WorkOrder` represents planned work and stores `completed_at` when finished; `MaintenanceRecord` represents what was actually performed and can carry the actual cost. This distinction avoids confusing planned and completed maintenance.

## Functional dependencies and normalization

Representative dependencies include `location_id -> location_code, name, address, region`, `component_id -> asset_tag, location_id, category_id, name, status, installed_on`, and `assessment_id -> component_id, technician_id, assessed_at, health_score, condition_status, findings`. In the junction table, `(incident_id, component_id)` determines `impact_type` and `notes`.

Attributes are atomic (1NF). Junction facts are separated from either parent, and non-key attributes depend on the whole key (2NF). Category, location, technician, and component facts are separated so there are no transitive dependencies within the main relations (3NF). The primary-key and alternate-key constraints make these relations close to BCNF for the represented facts. Repeated assessments, readings, incidents, and maintenance records are rows, not repeating columns.

## Integrity rules

- Scores are between 0 and 100; costs and sensor values follow appropriate non-negative checks.
- Status, severity, condition, work type, and alert values are restricted with `CHECK` constraints.
- Historical records use `RESTRICT`/`NO ACTION` deletion behavior. Incidents and components cannot be silently removed while history exists; the junction row is removed only when its parent is explicitly removed in a controlled operation.
- Required relationships and timestamps are non-null. A work order must have a target component or incident, and a maintenance record must reference a work order.
- Indexes support foreign-key joins and common filters such as component history, open incidents, active work orders, and recent readings.

## Phase 2 trigger behavior

1. A `BEFORE UPDATE` trigger updates `Component.updated_at`.
2. `AFTER INSERT/UPDATE` triggers record changed incident and work-order rows in `AuditLog`, storing old and new JSON values.
3. An assessment trigger creates one active critical-health alert per component and alert type when the score is 70 or below. A partial unique index and transaction advisory lock prevent concurrent duplicate active alerts while allowing a new alert after resolution.
4. A work-order completion trigger requires `completed_at`, completion notes, and an actual maintenance record before allowing `COMPLETED`.

## Phase 3 database programming

Reporting views isolate the latest assessment and pre-aggregate incident and maintenance metrics to avoid join multiplication. Functions return a component's latest health score and actual maintenance cost; an existing component with no assessments returns `NULL` for latest health, while an unknown component raises an exception. The `sp_complete_work_order` procedure records a maintenance row and completes a work order atomically through the Phase 2 completion trigger. Advanced query and performance examples are in `database/advanced_queries.sql` and `database/performance_tests.sql`.

## Phase 4 transactions and concurrency

`database/transaction_tests.sql` verifies `COMMIT`, `ROLLBACK`, atomic procedure failure, and rollback of a valid work-order completion. The two-session locking, timeout, `SKIP LOCKED`, and isolation-level lab is documented in `docs/TRANSACTION_CONCURRENCY_LAB.md`. The lab uses only a disposable demonstration table and never requires destructive operations on project tables.

Simple domain rules remain declarative constraints; triggers should not duplicate them. AuditLog's generic `entity_id` is not a universal foreign key and must be validated by trigger/application code.
