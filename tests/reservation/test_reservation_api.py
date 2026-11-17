from datetime import UTC, datetime, timedelta

from app import store
from app.schemas import VehicleStatus


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _body(vehicle_id: str = "V001", start_offset_h: int = 1, duration_h: int = 2) -> dict:
    now = datetime.now(UTC)
    return {
        "vehicle_id": vehicle_id,
        "student_id": "SV001",
        "start": _iso(now + timedelta(hours=start_offset_h)),
        "end": _iso(now + timedelta(hours=start_offset_h + duration_h)),
    }


# ------------------------------------------------------------
# Happy path
# ------------------------------------------------------------

def test_api_reserve_returns_201(client, seeded_store):
    r = client.post("/reserve", json=_body("V001"))
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == "B001"
    assert body["vehicle_id"] == "V001"
    assert body["status"] == "CONFIRMED"
    assert body["deadline"] is not None


# ------------------------------------------------------------
# Error paths
# ------------------------------------------------------------

def test_api_reserve_unknown_vehicle_returns_404(client, seeded_store):
    r = client.post("/reserve", json=_body("V999"))
    assert r.status_code == 404
    assert r.json()["detail"] == "VEHICLE_NOT_FOUND"


def test_api_reserve_ineligible_vehicle_returns_409(client, seeded_store):
    # V004 has pin 15 < MIN_RENTAL_PIN
    r = client.post("/reserve", json=_body("V004"))
    assert r.status_code == 409
    assert r.json()["detail"] == "VEHICLE_NOT_ELIGIBLE"


def test_api_reserve_overlap_returns_409(client, seeded_store):
    # First reservation succeeds
    r1 = client.post("/reserve", json=_body("V001"))
    assert r1.status_code == 201
    first = r1.json()

    # Keep V001 AVAILABLE so eligibility passes and conflict check triggers
    store.vehicles["V001"].status = VehicleStatus.AVAILABLE

    start = datetime.fromisoformat(first["start"]) + timedelta(minutes=30)
    end = datetime.fromisoformat(first["end"]) + timedelta(minutes=30)
    r2 = client.post(
        "/reserve",
        json={
            "vehicle_id": "V001",
            "student_id": "SV002",
            "start": _iso(start),
            "end": _iso(end),
        },
    )
    assert r2.status_code == 409
    assert r2.json()["detail"] == "VEHICLE_CONFLICT"


def test_api_reserve_invalid_time_returns_400(client, seeded_store):
    now = datetime.now(UTC)
    r = client.post(
        "/reserve",
        json={
            "vehicle_id": "V001",
            "student_id": "SV001",
            "start": _iso(now + timedelta(hours=3)),
            "end": _iso(now + timedelta(hours=1)),
        },
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "INVALID_TIME_RANGE"