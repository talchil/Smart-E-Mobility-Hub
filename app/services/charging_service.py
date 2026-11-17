from datetime import UTC, datetime, timedelta

from app import store
from app.schemas import (
    ChargingOut,
    ChargingSlot,
    ChargingStatus,
    ScheduleChargingRequest,
    VehicleStatus,
)

# Error codes
ERR_VEHICLE_NOT_FOUND = "VEHICLE_NOT_FOUND"
ERR_STATION_NOT_FOUND = "STATION_NOT_FOUND"
ERR_BATTERY_FULL = "BATTERY_FULL"
ERR_INVALID_TIME_RANGE = "INVALID_TIME_RANGE"
ERR_CHARGING_DUPLICATE_ACTIVE = "CHARGING_DUPLICATE_ACTIVE"
ERR_CHARGING_VEHICLE_OVERLAP = "CHARGING_VEHICLE_OVERLAP"

# Statuses that occupy a station's charging capacity
_ACTIVE_STATUSES = (ChargingStatus.CONFIRMED, ChargingStatus.CHARGING)


def _next_slot_id() -> str:
    return f"C{len(store.charging_slots) + 1:03d}"


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


def _to_out(c: ChargingSlot) -> ChargingOut:
    return ChargingOut(
        id=c.id,
        station_id=c.station_id,
        vehicle_id=c.vehicle_id,
        status=c.status,
        start=c.start,
        end=c.end,
        created_at=c.created_at,
    )


def _active_slots_at_station(station_id: str, start, end) -> int:
    """Count active charging slots at a station overlapping [start, end)."""
    count = 0
    for c in store.charging_slots.values():
        if c.station_id != station_id:
            continue
        if c.status not in _ACTIVE_STATUSES:
            continue
        if _overlaps(start, end, c.start, c.end):
            count += 1
    return count


def _has_active_request_for_vehicle(vehicle_id: str) -> bool:
    """A vehicle may have at most one PENDING/CONFIRMED/CHARGING request."""
    for c in store.charging_slots.values():
        if c.vehicle_id != vehicle_id:
            continue
        if c.status in (ChargingStatus.PENDING, ChargingStatus.CONFIRMED, ChargingStatus.CHARGING):
            return True
    return False


def _has_overlapping_request_for_vehicle(vehicle_id: str, start, end) -> bool:
    for c in store.charging_slots.values():
        if c.vehicle_id != vehicle_id:
            continue
        if c.status not in (ChargingStatus.PENDING, ChargingStatus.CONFIRMED, ChargingStatus.CHARGING):
            continue
        if _overlaps(start, end, c.start, c.end):
            return True
    return False


# ------------------------------------------------------------
# schedule_charging
# ------------------------------------------------------------

def schedule_charging(req: ScheduleChargingRequest) -> ChargingOut:
    """Create a PENDING charging request.

    Validation:
    - vehicle exists
    - station exists
    - battery is 0..99 (100 = full, nothing to charge)
    - start is in the future; end = start + duration_min
    - no other PENDING/CONFIRMED/CHARGING request for the same vehicle
    - no overlapping active request for the same vehicle

    The request is always created as PENDING. run_scheduling_cycle()
    later confirms it if capacity allows.

    Raises:
        ValueError: with one of the ERR_* codes above.
    """
    with store.lock:
        vehicle = store.vehicles.get(req.vehicle_id)
        if vehicle is None:
            raise ValueError(ERR_VEHICLE_NOT_FOUND)

        station = store.stations.get(req.station_id)
        if station is None:
            raise ValueError(ERR_STATION_NOT_FOUND)

        # Battery 0..99 (100 means fully charged)
        if not 0 <= vehicle.pin <= 99:
            raise ValueError(ERR_BATTERY_FULL)

        start = req.start
        end = start + timedelta(minutes=req.duration_min)
        now = datetime.now(UTC)

        if start >= end or start < now:
            raise ValueError(ERR_INVALID_TIME_RANGE)

        if _has_active_request_for_vehicle(req.vehicle_id):
            raise ValueError(ERR_CHARGING_DUPLICATE_ACTIVE)
        if _has_overlapping_request_for_vehicle(req.vehicle_id, start, end):
            raise ValueError(ERR_CHARGING_VEHICLE_OVERLAP)

        slot = ChargingSlot(
            id=_next_slot_id(),
            station_id=req.station_id,
            vehicle_id=req.vehicle_id,
            start=start,
            end=end,
            status=ChargingStatus.PENDING,
            created_at=now,
            usage_deadline=req.usage_deadline,
        )
        store.charging_slots[slot.id] = slot
        return _to_out(slot)


# ------------------------------------------------------------
# run_scheduling_cycle
# ------------------------------------------------------------

def _priority_key(c: ChargingSlot) -> tuple:
    """ordering:
    1. usage deadline (none last)
    2. lower battery first
    3. earlier submission time
    4. earlier id
    """
    deadline = c.usage_deadline or datetime.max.replace(tzinfo=UTC)
    vehicle = store.vehicles.get(c.vehicle_id)
    pin = vehicle.pin if vehicle else 999
    return (deadline, pin, c.created_at, c.id)


def run_scheduling_cycle() -> list[ChargingOut]:
    """Confirm PENDING requests that fit station capacity.

    Orders all PENDING requests by NIF-04 priority, then for each one
    checks whether the station has spare capacity in [start, end). If
    yes -> CONFIRMED, otherwise stays PENDING for the next cycle.

    Returns:
        The list of requests confirmed in this cycle.
    """
    confirmed: list[ChargingOut] = []
    with store.lock:
        pending = [c for c in store.charging_slots.values() if c.status == ChargingStatus.PENDING]
        pending.sort(key=_priority_key)

        for c in pending:
            station = store.stations.get(c.station_id)
            if station is None:
                continue
            used = _active_slots_at_station(c.station_id, c.start, c.end)
            if used >= station.slots_total:
                continue
            c.status = ChargingStatus.CONFIRMED
            confirmed.append(_to_out(c))
    return confirmed


# ------------------------------------------------------------
# list_requests
# ------------------------------------------------------------

def list_requests() -> list[ChargingOut]:
    """Return all charging requests (for demo / queue inspection)."""
    with store.lock:
        return [_to_out(c) for c in store.charging_slots.values()]