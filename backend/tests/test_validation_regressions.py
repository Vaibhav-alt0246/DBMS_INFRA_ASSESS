from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas import CompletionIn

@pytest.mark.parametrize('resource,body', [
    ('components', {'location_id': 0}),
    ('components', {'category_id': -1}),
    ('components', {'location_id': 2**63}),
    ('components', {'name': '   '}),
    ('components', {'name': 'x' * 151}),
    ('components', {'status': 'BROKEN'}),
    ('incidents', {'severity': 'URGENT'}),
    ('incidents', {'reported_at': '2026-11-11T10:30:00'}),
    ('work-orders', {'estimated_cost': 'Infinity'}),
    ('work-orders', {'estimated_cost': 'NaN'}),
    ('work-orders', {'estimated_cost': '10000000000.00'}),
    ('maintenance-records', {'actual_cost': '1.234'}),
    ('sensor-readings', {'reading_value': 'NaN'}),
    ('sensor-readings', {'reading_value': '1.12345'}),
    ('maintenance-alerts', {'status': 'DELETED'}),
])
def test_invalid_updates_fail_before_database_access(resource, body):
    assert TestClient(app).patch(f'/api/{resource}/1', json=body).status_code == 422

def test_money_is_kept_as_exact_decimal():
    value = CompletionIn(technician_id=1, action_taken='Repair', actual_cost='9999999999.99', outcome='SUCCESSFUL', completed_at='2026-11-11T10:30:00Z', completion_notes='Done')
    assert value.actual_cost == Decimal('9999999999.99')
    assert isinstance(value.model_dump()['actual_cost'], Decimal)
