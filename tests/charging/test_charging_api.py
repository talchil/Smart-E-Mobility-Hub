from datetime import UTC, datetime, timedelta
from app import store
from app.schemas import ChargingStatus


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _body(
    vehicle_id: str = "V001",
    station_id: str = "S1",
    offset_h: int = 1,
    duration_min: int = 30,
) -> dict:
    now = datetime.now(UTC)
    return {
        "vehicle_id": vehicle_id,
        "station_id": station_id,
        "start": _iso(now + timedelta(hours=offset_h)),
        "duration_min": duration_min,
    }


# ------------------------------------------------------------
# POST /charging/schedule
# ------------------------------------------------------------

def test_api_schedule_returns_201_confirmed_when_capacity(client, seeded_store):
    r = client.post("/charging/schedule", json=_body("V001", "S1"))
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == "C001"
    assert body["status"] == "CONFIRMED"   # router ran a cycle internally


def test_api_schedule_returns_201_pending_when_full(client, seeded_store):
    # S4 has 2 slots; fill them first
    client.post("/charging/schedule", json=_body("V001", "S4"))
    client.post("/charging/schedule", json=_body("V002", "S4"))

    r = client.post("/charging/schedule", json=_body("V003", "S4"))
    assert r.status_code == 201
    assert r.json()["status"] == "PENDING"


def test_api_schedule_battery_full_returns_400(client, seeded_store):
    store.vehicles["V001"].pin = 100
    r = client.post("/charging/schedule", json=_body("V001"))
    assert r.status_code == 400
    assert r.json()["detail"] == "BATTERY_FULL"


def test_api_schedule_unknown_vehicle_returns_404(client, seeded_store):
    r = client.post("/charging/schedule", json=_body("V999"))
    assert r.status_code == 404
    assert r.json()["detail"] == "VEHICLE_NOT_FOUND"


def test_api_schedule_duplicate_active_returns_409(client, seeded_store):
    client.post("/charging/schedule", json=_body("V001", "S1"))
    r = client.post("/charging/schedule", json=_body("V001", "S2"))
    assert r.status_code == 409
    assert r.json()["detail"] == "CHARGING_DUPLICATE_ACTIVE"


# ------------------------------------------------------------
# POST /charging/run-cycle
# ------------------------------------------------------------

def test_api_run_cycle_confirms_pending(client, seeded_store):
    # Fill S4 (2 slots) then add a third -> PENDING
    client.post("/charging/schedule", json=_body("V001", "S4"))
    client.post("/charging/schedule", json=_body("V002", "S4"))
    r3 = client.post("/charging/schedule", json=_body("V003", "S4"))
    assert r3.json()["status"] == "PENDING"

    # Free one slot manually
    for c in store.charging_slots.values():
        if c.status == ChargingStatus.CONFIRMED:
            c.status = ChargingStatus.COMPLETED
            break

    r = client.post("/charging/run-cycle")
    assert r.status_code == 200
    confirmed = r.json()
    assert len(confirmed) == 1
    assert confirmed[0]["status"] == "CONFIRMED"


def test_api_run_cycle_empty_when_nothing_to_confirm(client, seeded_store):
    r = client.post("/charging/run-cycle")
    assert r.status_code == 200
    assert r.json() == []


# ------------------------------------------------------------
# GET /charging/requests
# ------------------------------------------------------------

def test_api_list_requests(client, seeded_store):
    client.post("/charging/schedule", json=_body("V001", "S1"))
    client.post("/charging/schedule", json=_body("V002", "S2"))

    r = client.get("/charging/requests")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert ids == {"C001", "C002"}