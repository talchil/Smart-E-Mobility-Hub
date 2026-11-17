from datetime import UTC, datetime, timedelta
from app import store


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _reserve_via_api(client, vehicle_id: str = "V001") -> str:
    """Helper: reserve through the API and return the booking id."""
    now = datetime.now(UTC)
    r = client.post(
        "/reserve",
        json={
            "vehicle_id": vehicle_id,
            "student_id": "SV001",
            "start": _iso(now + timedelta(hours=1)),
            "end": _iso(now + timedelta(hours=3)),
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


# ------------------------------------------------------------
# Pickup
# ------------------------------------------------------------

def test_api_pickup_success_returns_200(client, seeded_store):
    bid = _reserve_via_api(client)
    r = client.post("/pickup", json={"booking_id": bid})
    assert r.status_code == 200
    assert r.json()["status"] == "PICKED_UP"


def test_api_pickup_unknown_booking_returns_404(client, seeded_store):
    r = client.post("/pickup", json={"booking_id": "B999"})
    assert r.status_code == 404
    assert r.json()["detail"] == "BOOKING_NOT_FOUND"


def test_api_pickup_already_picked_up_returns_409(client, seeded_store):
    bid = _reserve_via_api(client)
    client.post("/pickup", json={"booking_id": bid})
    r = client.post("/pickup", json={"booking_id": bid})
    assert r.status_code == 409
    assert r.json()["detail"] == "BOOKING_ALREADY_PICKED_UP"


def test_api_pickup_expired_returns_409(client, seeded_store):
    bid = _reserve_via_api(client)
    store.bookings[bid].deadline = datetime.now(UTC) - timedelta(minutes=1)
    r = client.post("/pickup", json={"booking_id": bid})
    assert r.status_code == 409
    assert r.json()["detail"] == "BOOKING_EXPIRED"


def test_api_pickup_battery_too_low_returns_409(client, seeded_store):
    bid = _reserve_via_api(client)
    store.vehicles["V001"].pin = 5
    r = client.post("/pickup", json={"booking_id": bid})
    assert r.status_code == 409
    assert r.json()["detail"] == "VEHICLE_BATTERY_TOO_LOW"


# ------------------------------------------------------------
# Return
# ------------------------------------------------------------

def test_api_return_success_returns_200(client, seeded_store):
    bid = _reserve_via_api(client)
    client.post("/pickup", json={"booking_id": bid})

    r = client.post(
        "/return",
        json={"booking_id": bid, "station_id": "S3", "final_pin": 55},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "COMPLETED"


def test_api_return_not_active_returns_409(client, seeded_store):
    bid = _reserve_via_api(client)  # CONFIRMED, not picked up
    r = client.post(
        "/return",
        json={"booking_id": bid, "station_id": "S3", "final_pin": 50},
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "BOOKING_NOT_ACTIVE"


def test_api_return_unknown_station_returns_404(client, seeded_store):
    bid = _reserve_via_api(client)
    client.post("/pickup", json={"booking_id": bid})
    r = client.post(
        "/return",
        json={"booking_id": bid, "station_id": "S999", "final_pin": 50},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "STATION_NOT_FOUND"


def test_api_full_lifecycle(client, seeded_store):
    bid = _reserve_via_api(client)
    r1 = client.post("/pickup", json={"booking_id": bid})
    assert r1.status_code == 200
    r2 = client.post(
        "/return",
        json={"booking_id": bid, "station_id": "S4", "final_pin": 40},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "COMPLETED"