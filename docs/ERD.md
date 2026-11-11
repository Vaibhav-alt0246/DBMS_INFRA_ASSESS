# InfraAssess ERD

```mermaid
erDiagram
    Location ||--o{ Component : contains
    ComponentCategory ||--o{ Component : classifies
    Component ||--o{ Assessment : receives
    Component ||--o{ IncidentComponent : affected_by
    Incident ||--o{ IncidentComponent : affects
    Technician ||--o{ Assessment : performs
    Technician ||--o{ WorkOrder : assigned_to
    Incident o|--o{ WorkOrder : motivates
    Component o|--o{ WorkOrder : targets
    WorkOrder ||--o{ MaintenanceRecord : documents
    Technician ||--o{ MaintenanceRecord : performs
    Component ||--o{ SensorReading : produces
    Component ||--o{ MaintenanceAlert : triggers

    Location { bigint location_id PK; varchar location_code UK; varchar name; varchar address; varchar region; }
    ComponentCategory { bigint category_id PK; varchar category_code UK; varchar name UK; text description; }
    Component { bigint component_id PK; varchar asset_tag UK; bigint location_id FK; bigint category_id FK; varchar name; varchar status; date installed_on; }
    Technician { bigint technician_id PK; varchar employee_code UK; varchar full_name; varchar email UK; varchar specialty; boolean active; }
    Assessment { bigint assessment_id PK; bigint component_id FK; bigint technician_id FK; timestamptz assessed_at; numeric health_score; varchar condition_status; text findings; }
    Incident { bigint incident_id PK; varchar incident_number UK; timestamptz reported_at; varchar severity; varchar status; varchar title; text description; }
    IncidentComponent { bigint incident_id PK,FK; bigint component_id PK,FK; varchar impact_type; text notes; }
    WorkOrder { bigint work_order_id PK; varchar work_order_number UK; bigint incident_id FK; bigint component_id FK; bigint technician_id FK; varchar work_type; varchar status; date planned_start; numeric estimated_cost; }
    MaintenanceRecord { bigint maintenance_id PK; bigint work_order_id FK; bigint technician_id FK; timestamptz performed_at; text action_taken; numeric actual_cost; }
    SensorReading { bigint reading_id PK; bigint component_id FK; timestamptz recorded_at; varchar sensor_type; numeric reading_value; varchar unit; }
    MaintenanceAlert { bigint alert_id PK; bigint component_id FK; bigint assessment_id FK; varchar alert_type; varchar status; timestamptz created_at; }
    AuditLog { bigint audit_id PK; varchar entity_type; bigint entity_id; varchar action; jsonb old_values; jsonb new_values; timestamptz changed_at; }
```

`Location`, `ComponentCategory`, and `Technician` are parent/reference entities. A component belongs to exactly one location and category; each can have zero or many related child rows. An assessment belongs to one component and is performed by one technician. Incidents and components are many-to-many through `IncidentComponent`, whose composite key prevents duplicate links.

Work orders may be linked to an incident and/or component and are planning records. A work order can have many maintenance records, which are the actual completed activities. Sensor readings belong to components. Alerts can point to the assessment that caused them. `AuditLog` is intentionally polymorphic: its generic `entity_id` cannot enforce a foreign key to every possible entity type, so application/trigger code must validate its entity type and ID.
