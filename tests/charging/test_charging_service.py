from datetime import UTC, datetime, timedelta
import pytest
from app import store
from app.schemas import ChargingStatus, ScheduleChargingRequest
from app.services.charging_service import (
    ERR_BATTERY_FULL,
    ERR_CHARGING_DUPLICATE_ACTIVE,
    ERR_INVALID_TIME_RANGE,
    ERR_STATION_NOT_FOUND,
    ERR_VEHICLE_NOT_FOUND,
    list_requests,
    run_scheduling_cycle,
    schedule_charging,
)


def _req(
    vehicle_id: str = "V001",
    station_id: str = "S1",
    offset_h: int = 1,
    duration_min: int = 30,
    usage_deadline: datetime | None = None,
) -> ScheduleChargingRequest:
    now = datetime.now(UTC)
    return ScheduleChargingRequest(
        vehicle_id=vehicle_id,
        station_id=station_id,
        start=now + timedelta(hours=offset_h),
        duration_min=duration_min,
        usage_deadline=usage_deadline,
    )


# ------------------------------------------------------------
# schedule_charging - happy path
# ------------------------------------------------------------

def test_schedule_creates_pending_request(seeded_store):
    out = schedule_charging(_req("V001", "S1"))
    assert out.id == "C001"
    assert out.status == ChargingStatus.PENDING
    assert store.charging_slots["C001"].vehicle_id == "V001"
    assert store.charging_slots["C001"].station_id == "S1"


# ------------------------------------------------------------
# schedule_charging - validation errors
# ------------------------------------------------------------

def test_schedule_unknown_vehicle_raises(seeded_store):
    with pytest.raises(ValueError) as exc:
        schedule_charging(_req(vehicle_id="V999"))
    assert str(exc.value) == ERR_VEHICLE_NOT_FOUND


def test_schedule_unknown_station_raises(seeded_store):
    with pytest.raises(ValueError) as exc:
        schedule_charging(_req(station_id="S999"))
    assert str(exc.value) == ERR_STATION_NOT_FOUND


def test_schedule_battery_full_raises(seeded_store):
    store.vehicles["V001"].pin = 100
    with pytest.raises(ValueError) as exc:
        schedule_charging(_req("V001"))
    assert str(exc.value) == ERR_BATTERY_FULL


def test_schedule_past_start_raises(seeded_store):
    now = datetime.now(UTC)
    req = ScheduleChargingRequest(
        vehicle_id="V001",
        station_id="S1",
        start=now - timedelta(hours=1),
        duration_min=30,
    )
    with pytest.raises(ValueError) as exc:
        schedule_charging(req)
    assert str(exc.value) == ERR_INVALID_TIME_RANGE


def test_schedule_duplicate_active_raises(seeded_store):
    schedule_charging(_req("V001", "S1"))
    with pytest.raises(ValueError) as exc:
        schedule_charging(_req("V001", "S2"))
    assert str(exc.value) == ERR_CHARGING_DUPLICATE_ACTIVE


def test_schedule_same_vehicle_blocked_regardless_of_time(seeded_store):
    schedule_charging(_req("V001", "S1", offset_h=1, duration_min=30))

    now = datetime.now(UTC)
    later = ScheduleChargingRequest(
        vehicle_id="V001",
        station_id="S2",
        start=now + timedelta(hours=5),   # no overlap at all
        duration_min=30,
    )
    with pytest.raises(ValueError) as exc:
        schedule_charging(later)
    assert str(exc.value) == ERR_CHARGING_DUPLICATE_ACTIVE


# ------------------------------------------------------------
# run_scheduling_cycle - capacity
# ------------------------------------------------------------

def test_cycle_confirms_when_capacity_available(seeded_store):
    c = schedule_charging(_req("V001", "S1"))
    assert store.charging_slots[c.id].status == ChargingStatus.PENDING

    confirmed = run_scheduling_cycle()
    assert len(confirmed) == 1
    assert confirmed[0].id == c.id
    assert store.charging_slots[c.id].status == ChargingStatus.CONFIRMED


def test_cycle_keeps_pending_when_station_full(seeded_store):
    # S4 has slots_total=2; create 3 overlapping requests
    start_offset = 1
    schedule_charging(_req("V001", "S4", offset_h=start_offset))
    schedule_charging(_req("V002", "S4", offset_h=start_offset))
    schedule_charging(_req("V003", "S4", offset_h=start_offset))

    run_scheduling_cycle()

    statuses = sorted(
        (c.id, c.status.value) for c in store.charging_slots.values()
    )
    confirmed = [s for _, s in statuses if s == "CONFIRMED"]
    pending = [s for _, s in statuses if s == "PENDING"]
    assert len(confirmed) == 2
    assert len(pending) == 1


def test_cycle_priority_lower_battery_first(seeded_store):
    # S4 slots_total=2, 3 requests with different battery levels
    # V001=85, V002=60, V003=45
    schedule_charging(_req("V001", "S4", offset_h=1))
    schedule_charging(_req("V002", "S4", offset_h=1))
    schedule_charging(_req("V003", "S4", offset_h=1))

    run_scheduling_cycle()

    # Two lowest-battery requests should be CONFIRMED
    by_vehicle = {c.vehicle_id: c.status for c in store.charging_slots.values()}
    assert by_vehicle["V003"] == ChargingStatus.CONFIRMED  # pin 45
    assert by_vehicle["V002"] == ChargingStatus.CONFIRMED  # pin 60
    assert by_vehicle["V001"] == ChargingStatus.PENDING    # pin 85


def test_cycle_confirms_freed_slot_on_next_run(seeded_store):
    schedule_charging(_req("V001", "S4", offset_h=1))
    schedule_charging(_req("V002", "S4", offset_h=1))
    schedule_charging(_req("V003", "S4", offset_h=1))
    run_scheduling_cycle()

    # Free one slot by marking a confirmed one as COMPLETED
    for c in store.charging_slots.values():
        if c.status == ChargingStatus.CONFIRMED:
            c.status = ChargingStatus.COMPLETED
            break

    confirmed = run_scheduling_cycle()
    assert len(confirmed) == 1
    assert store.charging_slots[confirmed[0].id].status == ChargingStatus.CONFIRMED


# ------------------------------------------------------------
# list_requests
# ------------------------------------------------------------

def test_list_requests_returns_all(seeded_store):
    schedule_charging(_req("V001", "S1"))
    schedule_charging(_req("V002", "S2"))
    result = list_requests()
    assert len(result) == 2
    assert {c.id for c in result} == {"C001", "C002"}