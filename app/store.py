import threading
from app.schemas import Booking, ChargingSlot, Station, Vehicle


# Collections
vehicles: dict[str, Vehicle] = {}
stations: dict[str, Station] = {}
bookings: dict[str, Booking] = {}
charging_slots: dict[str, ChargingSlot] = {}
# UC-14)
processed_events: dict[str, dict] = {}

lock = threading.RLock()


# Helpers
def reset() -> None:
    """Clear every collection. Used by seed reload and tests."""
    with lock:
        vehicles.clear()
        stations.clear()
        bookings.clear()
        charging_slots.clear()
        processed_events.clear()  # Clear log event khi reset test


def snapshot() -> dict:
    """Return shallow copies of all collections."""
    with lock:
        return {
            "vehicles": dict(vehicles),
            "stations": dict(stations),
            "bookings": dict(bookings),
            "charging_slots": dict(charging_slots),
            "processed_events": dict(processed_events),  # Thêm dòng này
        }


# Reentrant so a service can call another service under the same lock
# without deadlocking.
lock = threading.RLock()


# Helpers
def reset() -> None:
    """Clear every collection. Used by seed reload and tests."""
    with lock:
        vehicles.clear()
        stations.clear()
        bookings.clear()
        charging_slots.clear()


def snapshot() -> dict:
    """Return shallow copies of all collections."""
    with lock:
        return {
            "vehicles": dict(vehicles),
            "stations": dict(stations),
            "bookings": dict(bookings),
            "charging_slots": dict(charging_slots),
        }