import pytest
from pydantic import ValidationError
from backend.app.schemas import CompletionIn

def test_completion_contract_contains_procedure_inputs():
    payload = CompletionIn(
        technician_id=1,
        action_taken='Replaced seal',
        actual_cost=2180,
        outcome='SUCCESSFUL',
        completed_at='2026-10-29T12:00:00Z',
        completion_notes='Repair completed and tested',
    )
    assert payload.model_dump()['technician_id'] == 1
    assert payload.model_dump()['actual_cost'] == 2180

def test_completion_contract_rejects_negative_cost():
    with pytest.raises(ValidationError):
        CompletionIn(
            technician_id=1,
            action_taken='Invalid repair',
            actual_cost=-1,
            outcome='SUCCESSFUL',
            completed_at='2026-10-29T12:00:00Z',
            completion_notes='Should fail',
        )
