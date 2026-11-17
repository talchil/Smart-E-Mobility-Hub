from datetime import UTC, datetime
from app import store
from app.schemas import (
    MIN_RENTAL_PIN,
    ChargingStatus,
    DashboardOut,
    StationOut,
    VehicleStatus,
)

_ACTIVE_CHARGING_STATUSES = (ChargingStatus.CONFIRMED, ChargingStatus.CHARGING)


def _slots_used_at(station_id: str, now: datetime) -> int:
    """Count charging slots at a station that are active right now."""
    count = 0
    for c in store.charging_slots.values():
        if c.station_id != station_id:
            continue
        if c.status not in _ACTIVE_CHARGING_STATUSES:
            continue
        if c.start <= now < c.end:
            count += 1
    return count


def get_dashboard(zone: str | None = None) -> DashboardOut:
    with store.lock:
        now = datetime.now(UTC)

        vehicles = list(store.vehicles.values())
        stations = list(store.stations.values())

        if zone is not None:
            vehicles = [v for v in vehicles if v.zone == zone]
            stations = [s for s in stations if s.zone == zone]

        total = len(vehicles)
        available = sum(
            1
            for v in vehicles
            if v.status == VehicleStatus.AVAILABLE and v.pin >= MIN_RENTAL_PIN
        )
        in_use = sum(1 for v in vehicles if v.status == VehicleStatus.IN_USE)
        avg_pin = (sum(v.pin for v in vehicles) / total) if total > 0 else 0.0

        station_out = [
            StationOut(
                id=s.id,
                zone=s.zone,
                name=s.name,
                capacity=s.capacity,
                slots_total=s.slots_total,
                slots_used=_slots_used_at(s.id, now),
            )
            for s in stations
        ]

    return DashboardOut(
        total_vehicles=total,
        available=available,
        in_use=in_use,
        avg_pin=round(avg_pin, 2),
        stations=station_out,
        alerts=[],  
    )