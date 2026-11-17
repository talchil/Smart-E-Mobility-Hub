from app import store
from app.schemas import MIN_RENTAL_PIN, VehicleOut


def search(
    zone: str | None = None,
    station_id: str | None = None,
    vehicle_type: str | None = None,
    min_battery: int = 0,
) -> list[VehicleOut]:
    """
    Returns:
        A list of VehicleOut sorted by battery desc, then id asc.
    """
    # Defensive guard: the router already validates 0-100 via Query,
    # but the service may also be called directly from tests.
    if not 0 <= min_battery <= 100:
        raise ValueError("min_battery must be between 0 and 100")

    with store.lock:
        candidates = list(store.vehicles.values())

    results: list[VehicleOut] = []
    for v in candidates:
        # Only rentable vehicles
        if v.status.value != "AVAILABLE":
            continue
        # Must pass both thresholds
        if v.pin < MIN_RENTAL_PIN or v.pin < min_battery:
            continue
        # Optional filters
        if zone is not None and v.zone != zone:
            continue
        if station_id is not None and v.station_id != station_id:
            continue
        if vehicle_type is not None and v.vehicle_type != vehicle_type:
            continue

        results.append(
            VehicleOut(
                id=v.id,
                zone=v.zone,
                vehicle_type=v.vehicle_type,
                pin=v.pin,
                status=v.status,
                station_id=v.station_id,
                lat=v.lat,
                lng=v.lng,
            )
        )

    results.sort(key=lambda x: (-x.pin, x.id))
    return results