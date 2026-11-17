from datetime import UTC, datetime, timedelta

from app import store
from app.schemas import (
    ChargingSlot,
    ChargingStatus,
    Station,
    Vehicle,
    VehicleStatus,
)
from app.services.dashboard_service import get_dashboard


# ------------------------------------------------------------
# Aggregates
# ------------------------------------------------------------

def test_dashboard_totals_no_filter(seeded_store):
    d = get_dashboard()
    assert d.total_vehicles == 10
    assert d.in_use == 1                       # V005
    assert d.available == 6                    # AVAILABLE and pin >= 20
    assert len(d.stations) == 4
    assert d.alerts == []


def test_dashboard_available_excludes_low_battery(seeded_store):
    """V004 (pin 15) and V008 (pin 10) are AVAILABLE but not eligible."""
    d = get_dashboard()
    # 8 AVAILABLE - 2 low battery = 6
    assert d.available == 6


def test_dashboard_avg_pin(seeded_store):
    d = get_dashboard()
    expected = sum(v.pin for v in store.vehicles.values()) / 10
    assert d.avg_pin == round(expected, 2)


# ------------------------------------------------------------
# Zone filter
# ------------------------------------------------------------

def test_dashboard_zone_filter(seeded_store):
    d = get_dashboard(zone="A")
    assert d.total_vehicles == 5
    assert {s.id for s in d.stations} == {"S1", "S2"}


def test_dashboard_unknown_zone_returns_empty(seeded_store):
    d = get_dashboard(zone="Z")
    assert d.total_vehicles == 0
    assert d.available == 0
    assert d.in_use == 0
    assert d.avg_pin == 0.0
    assert d.stations == []


# ------------------------------------------------------------
# slots_used - only currently active slots
# ------------------------------------------------------------

def _add_slot(slot_id, station_id, vehicle_id, start, end, status):
    store.charging_slots[slot_id] = ChargingSlot(
        id=slot_id,
        station_id=station_id,
        vehicle_id=vehicle_id,
        start=start,
        end=end,
        status=status,
    )


def test_dashboard_slots_used_counts_active_now(seeded_store):
    now = datetime.now(UTC)
    _add_slot(
        "CX1", "S1", "V001",
        now - timedelta(minutes=10), now + timedelta(minutes=20),
        ChargingStatus.CHARGING,
    )
    _add_slot(
        "CX2", "S1", "V002",
        now - timedelta(minutes=5), now + timedelta(minutes=25),
        ChargingStatus.CONFIRMED,
    )
    d = get_dashboard()
    s1 = next(s for s in d.stations if s.id == "S1")
    assert s1.slots_used == 2


def test_dashboard_slots_used_ignores_future_slots(seeded_store):
    now = datetime.now(UTC)
    _add_slot(
        "CX1", "S1", "V001",
        now + timedelta(hours=1), now + timedelta(hours=2),
        ChargingStatus.CONFIRMED,
    )
    d = get_dashboard()
    s1 = next(s for s in d.stations if s.id == "S1")
    assert s1.slots_used == 0


def test_dashboard_slots_used_ignores_pending(seeded_store):
    now = datetime.now(UTC)
    _add_slot(
        "CX1", "S1", "V001",
        now - timedelta(minutes=1), now + timedelta(minutes=29),
        ChargingStatus.PENDING,
    )
    d = get_dashboard()
    s1 = next(s for s in d.stations if s.id == "S1")
    assert s1.slots_used == 0


def test_dashboard_slots_used_ignores_past_slots(seeded_store):
    now = datetime.now(UTC)
    _add_slot(
        "CX1", "S1", "V001",
        now - timedelta(hours=2), now - timedelta(hours=1),
        ChargingStatus.COMPLETED,
    )
    d = get_dashboard()
    s1 = next(s for s in d.stations if s.id == "S1")
    assert s1.slots_used == 0