from datetime import date, datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class LooseRecord(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ComponentIn(LooseRecord):
    asset_tag: str = Field(min_length=1, max_length=40); location_id: int; category_id: int; name: str
    status: str = 'OPERATIONAL'; installed_on: date | None = None
class TechnicianIn(LooseRecord):
    employee_code: str; full_name: str; email: str; specialty: str; active: bool = True
class IncidentIn(LooseRecord):
    incident_number: str; reported_at: datetime; severity: str; status: str = 'OPEN'; title: str; description: str; resolved_at: datetime | None = None
class AssessmentIn(LooseRecord):
    component_id: int; technician_id: int; assessed_at: datetime; health_score: float = Field(ge=0, le=100); condition_status: str; findings: str
class WorkOrderIn(LooseRecord):
    work_order_number: str; incident_id: int | None = None; component_id: int | None = None; technician_id: int | None = None; work_type: str; status: str = 'PLANNED'; planned_start: date; planned_end: date | None = None; completed_at: datetime | None = None; estimated_cost: float = Field(default=0, ge=0); completion_notes: str | None = None
class MaintenanceIn(LooseRecord):
    work_order_id: int; technician_id: int; performed_at: datetime; action_taken: str; actual_cost: float = Field(ge=0); outcome: str
class SensorIn(LooseRecord):
    component_id: int; recorded_at: datetime; sensor_type: str; reading_value: float = Field(ge=0); unit: str
class AlertUpdate(LooseRecord):
    status: str
class CompletionIn(LooseRecord):
    technician_id: int; action_taken: str; actual_cost: float = Field(ge=0); outcome: str; completed_at: datetime; completion_notes: str
