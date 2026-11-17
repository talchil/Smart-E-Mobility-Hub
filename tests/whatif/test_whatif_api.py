from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_whatif_station_full_api(seeded_store):
    """Test successful API call for the station_full scenario (200 OK)."""
    payload = {
        "scenario": "station_full",
        "params": {
            "station_id": "S1",
            "capacity": 2,
            "incoming_returns": 10
        }
    }
    response = client.post("/what-if", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["scenario"] == "station_full"
    assert "baseline" in data
    assert "scenario_result" in data
    assert "delta" in data
    assert data["scenario_result"]["capacity"] == 2

def test_whatif_demand_surge_api(seeded_store):
    """Test successful API call for the demand_surge scenario (200 OK)."""
    payload = {
        "scenario": "demand_surge",
        "params": {
            "zone": "Zone B",
            "surge_requests": 15
        }
    }
    response = client.post("/what-if", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["scenario"] == "demand_surge"
    assert data["scenario_result"]["surge_requests"] == 15

def test_whatif_invalid_station_id(seeded_store):
    """Test API call with station_full scenario but invalid station ID (400 Bad Request)."""
    payload = {
        "scenario": "station_full",
        "params": {
            "station_id": "S999_GHOST_STATION",
            "capacity": 0
        }
    }
    response = client.post("/what-if", json=payload)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "INVALID_STATION_ID"

def test_whatif_validation_error():
    """Test API call with missing required fields (422 Unprocessable Entity)."""
    # Missing the required 'scenario' field in the payload
    payload = {
        "params": {"station_id": "S1"}
    }
    response = client.post("/what-if", json=payload)
    
    assert response.status_code == 422