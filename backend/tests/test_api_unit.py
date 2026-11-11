from fastapi.testclient import TestClient
from backend.app.main import app

def test_routes_exist():
    paths={route.path for route in app.routes}
    assert '/api/health' in paths and '/api/search/incidents' in paths and '/api/work-orders/{item_id}/complete' in paths
