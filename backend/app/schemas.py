from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, create_model, model_validator

RecordId = Annotated[int, Field(gt=0, le=9223372036854775807)]
RequiredText = Annotated[str, Field(min_length=1)]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Outcome = Literal['SUCCESSFUL', 'PARTIAL', 'UNSUCCESSFUL']

class LooseRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)

class LocationIn(LooseRecord):
    location_code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=250)
    region: str = Field(min_length=1, max_length=80)

class CategoryIn(LooseRecord):
    category_code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None

class ComponentIn(LooseRecord):
    asset_tag: RequiredText = Field(max_length=40)
    location_id: RecordId
    category_id: RecordId
    name: RequiredText = Field(max_length=150)
    status: Literal['OPERATIONAL','DEGRADED','OUT_OF_SERVICE','RETIRED'] = 'OPERATIONAL'
    installed_on: date | None = None
class TechnicianIn(LooseRecord):
    employee_code: RequiredText = Field(max_length=30)
    full_name: RequiredText = Field(max_length=120)
    email: RequiredText = Field(max_length=160, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    specialty: RequiredText = Field(max_length=100)
    active: bool = True
class IncidentIn(LooseRecord):
    component_ids: list[RecordId] = Field(default_factory=list, max_length=100)
    incident_number: RequiredText = Field(max_length=30)
    reported_at: AwareDatetime
    severity: Literal['LOW','MEDIUM','HIGH','CRITICAL']
    status: Literal['OPEN','INVESTIGATING','RESOLVED','CLOSED'] = 'OPEN'
    title: RequiredText = Field(max_length=180)
    description: RequiredText
    resolved_at: AwareDatetime | None = None
    @model_validator(mode='after')
    def lifecycle(self):
        if (self.status in ('RESOLVED', 'CLOSED')) != (self.resolved_at is not None):
            raise ValueError('Resolved/closed incidents require resolved_at; open incidents must not have it.')
        if self.resolved_at and self.resolved_at < self.reported_at:
            raise ValueError('resolved_at must be after reported_at')
        return self
class AssessmentIn(LooseRecord):
    component_id: RecordId
    technician_id: RecordId
    assessed_at: AwareDatetime
    health_score: float = Field(ge=0, le=100)
    condition_status: Literal['GOOD','FAIR','POOR','CRITICAL']
    findings: RequiredText
class WorkOrderIn(LooseRecord):
    work_order_number: RequiredText = Field(max_length=30)
    incident_id: RecordId | None = None
    component_id: RecordId | None = None
    technician_id: RecordId | None = None
    work_type: Literal['CORRECTIVE','PREVENTIVE']
    status: Literal['PLANNED','ASSIGNED','IN_PROGRESS','COMPLETED','CANCELLED'] = 'PLANNED'
    planned_start: date
    planned_end: date | None = None
    completed_at: AwareDatetime | None = None
    estimated_cost: Money = Decimal('0')
    completion_notes: str | None = None
    @model_validator(mode='after')
    def lifecycle(self):
        if (self.status == 'COMPLETED') != (self.completed_at is not None):
            raise ValueError('Only completed orders may have completed_at, and it is required for completion.')
        return self
class MaintenanceIn(LooseRecord):
    work_order_id: RecordId
    technician_id: RecordId
    performed_at: AwareDatetime
    action_taken: RequiredText
    actual_cost: Money
    outcome: Outcome
class SensorIn(LooseRecord):
    component_id: RecordId
    recorded_at: AwareDatetime
    sensor_type: RequiredText = Field(max_length=40)
    reading_value: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    unit: RequiredText = Field(max_length=20)
class AlertUpdate(LooseRecord):
    status: Literal['OPEN','ACKNOWLEDGED','RESOLVED']
    owner_id: RecordId | None = None
    remediation_work_order_id: RecordId | None = None
    verification_notes: str | None = None
class CompletionIn(LooseRecord):
    technician_id: RecordId
    action_taken: RequiredText
    actual_cost: Money
    outcome: Outcome
    completed_at: AwareDatetime
    completion_notes: RequiredText

def patch_model(model):
    """Omit unchanged fields while retaining each field's type and constraints.

    A default of None makes a field omittable; it does not permit an explicit
    null unless the original schema permits null.
    """
    return create_model(
        model.__name__ + 'Patch', __base__=LooseRecord,
        **{name: (Annotated[field.annotation, *field.metadata] if field.metadata else field.annotation,
                  Field(default=None)) for name, field in model.model_fields.items()},
    )

class IncidentLink(LooseRecord):
    impact_type: Literal['PRIMARY', 'SECONDARY', 'POTENTIAL'] = 'PRIMARY'
    notes: str | None = None

class SensorThresholdIn(LooseRecord):
    component_id: RecordId
    sensor_type: RequiredText = Field(max_length=40)
    unit: RequiredText = Field(max_length=20)
    min_value: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
    max_value: Decimal | None = Field(default=None, max_digits=14, decimal_places=4)
