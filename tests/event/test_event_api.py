from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_process_event_api_success(seeded_store):
    """Test successful telemetry event ingestion (200 OK)."""
    payload = {
        "event_id": "API-EVT-001",
        "type": "telemetry",
        "resource_id": "V001",
        "payload": {
            "battery": 85,
            "zone": "Zone A"
        }
    }
    response = client.post("/events", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["event_id"] == "API-EVT-001"
    assert data["status"] == "applied"

def test_process_event_api_invalid_resource(seeded_store):
    """Test event targeting a non-existent vehicle (400 Bad Request)."""
    payload = {
        "event_id": "API-EVT-002",
        "type": "telemetry",
        "resource_id": "V999_GHOST",
        "payload": {"battery": 100}
    }
    response = client.post("/events", json=payload)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "INVALID_RESOURCE_ID"

def test_process_event_api_invalid_type(seeded_store):
    """Test event with unsupported/invalid type (422 Unprocessable Entity)."""
    payload = {
        "event_id": "API-EVT-003",
        "type": "flying_mode", # Not defined in EventType Enum
        "resource_id": "V001",
        "payload": {}
    }
    response = client.post("/events", json=payload)
    
    # FastAPI/Pydantic automatically rejects invalid Enums with 422
    assert response.status_code == 422