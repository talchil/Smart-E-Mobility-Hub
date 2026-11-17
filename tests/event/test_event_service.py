import pytest
from app import store
from app.services import event_service
from app.schemas import EventRequest, EventType, VehicleStatus

def test_event_idempotency_nif_01(seeded_store):
    """
    VERIFY NIF-01: Ensure that processing the same event_id twice
    does not mutate the state the second time.
    """
    req = EventRequest(
        event_id="EVT-100", 
        type=EventType.TELEMETRY, 
        resource_id="V001", 
        payload={"battery": 80}
    )
    
    # First processing: state should change
    res1 = event_service.process_event(req)
    assert store.vehicles["V001"].pin == 80
    assert res1.status == "applied"
    
    # Simulate a manual state change in the system
    store.vehicles["V001"].pin = 50
    
    # Second processing (Duplicate event arrives from IoT):
    res2 = event_service.process_event(req)
    
    # It must return the cached result but MUST NOT change the battery back to 80
    assert res1.event_id == res2.event_id
    assert store.vehicles["V001"].pin == 50, "NIF-01 Violated: Duplicate event mutated state!"


def test_telemetry_event(seeded_store):
    """Test telemetry updates for battery and location."""
    req = EventRequest(
        event_id="EVT-101", 
        type=EventType.TELEMETRY, 
        resource_id="V001", 
        payload={"battery": 45, "zone": "Zone X"}
    )
    event_service.process_event(req)
    
    assert store.vehicles["V001"].pin == 45
    assert store.vehicles["V001"].zone == "Zone X"


def test_charging_lifecycle_and_constraints_nif_05(seeded_store):
    """
    VERIFY NIF-05: Strict state transitions.
    Vehicle enters -> Starts charging -> CANNOT exit while charging -> Completes -> Exits.
    """
    # 1. Enter station S1
    req_entry = EventRequest(event_id="EVT-102", type=EventType.PARKING_ENTRY, resource_id="V002", payload={"station_id": "S1"})
    event_service.process_event(req_entry)
    assert store.vehicles["V002"].station_id == "S1"

    # 2. Start charging
    req_charge = EventRequest(event_id="EVT-103", type=EventType.CHARGING_START, resource_id="V002")
    event_service.process_event(req_charge)
    assert store.vehicles["V002"].status == VehicleStatus.CHARGING

    # 3. Try to exit while charging (Should fail)
    req_exit_early = EventRequest(event_id="EVT-104", type=EventType.PARKING_EXIT, resource_id="V002")
    with pytest.raises(ValueError, match="CANNOT_EXIT_WHILE_CHARGING"):
        event_service.process_event(req_exit_early)

    # 4. Complete charging
    req_complete = EventRequest(event_id="EVT-105", type=EventType.CHARGING_COMPLETION, resource_id="V002", payload={"final_battery": 100})
    event_service.process_event(req_complete)
    assert store.vehicles["V002"].status == VehicleStatus.AVAILABLE
    assert store.vehicles["V002"].pin == 100

    # 5. Now exit successfully
    req_exit_valid = EventRequest(event_id="EVT-106", type=EventType.PARKING_EXIT, resource_id="V002")
    event_service.process_event(req_exit_valid)
    assert store.vehicles["V002"].station_id is None