from datetime import UTC, datetime, timedelta

from app import store
from app.schemas import (
    HOLDING_PERIOD_MIN,
    MIN_RENTAL_PIN,
    Booking,
    BookingOut,
    BookingStatus,
    ReserveRequest,
    PickupRequest,
    ReturnRequest,
    VehicleStatus,
)

# Error codes raised by this service
ERR_VEHICLE_NOT_FOUND = "VEHICLE_NOT_FOUND"
ERR_VEHICLE_NOT_ELIGIBLE = "VEHICLE_NOT_ELIGIBLE"
ERR_VEHICLE_CONFLICT = "VEHICLE_CONFLICT"
ERR_INVALID_TIME_RANGE = "INVALID_TIME_RANGE"
# Additional error codes for UC-03 / UC-04
ERR_BOOKING_NOT_FOUND = "BOOKING_NOT_FOUND"
ERR_BOOKING_ALREADY_PICKED_UP = "BOOKING_ALREADY_PICKED_UP"
ERR_BOOKING_NOT_PICKABLE = "BOOKING_NOT_PICKABLE"
ERR_BOOKING_EXPIRED = "BOOKING_EXPIRED"
ERR_VEHICLE_NOT_RESERVED = "VEHICLE_NOT_RESERVED"
ERR_VEHICLE_BATTERY_TOO_LOW = "VEHICLE_BATTERY_TOO_LOW"
ERR_BOOKING_NOT_ACTIVE = "BOOKING_NOT_ACTIVE"
ERR_STATION_NOT_FOUND = "STATION_NOT_FOUND"


def _next_booking_id() -> str:
    """Generate a sequential booking id (B001, B002, ...)."""
    return f"B{len(store.bookings) + 1:03d}"


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    """Half-open interval overlap check: [a_start, a_end) vs [b_start, b_end)."""
    return a_start < b_end and b_start < a_end


def _to_out(b: Booking) -> BookingOut:
    return BookingOut(
        id=b.id,
        vehicle_id=b.vehicle_id,
        student_id=b.student_id,
        status=b.status,
        start=b.start,
        end=b.end,
        deadline=b.deadline,
    )


def reserve(req: ReserveRequest) -> BookingOut:
    with store.lock:
        vehicle = store.vehicles.get(req.vehicle_id)
        if vehicle is None:
            raise ValueError(ERR_VEHICLE_NOT_FOUND)

        # Time range validation
        if req.start >= req.end:
            raise ValueError(ERR_INVALID_TIME_RANGE)

        # Eligibility recheck (UC-02 step 2 / 5)
        if vehicle.status != VehicleStatus.AVAILABLE:
            raise ValueError(ERR_VEHICLE_NOT_ELIGIBLE)
        if vehicle.pin < MIN_RENTAL_PIN:
            raise ValueError(ERR_VEHICLE_NOT_ELIGIBLE)

        # Conflict check against active bookings on the same vehicle
        for b in store.bookings.values():
            if b.vehicle_id != req.vehicle_id:
                continue
            if b.status not in (BookingStatus.CONFIRMED, BookingStatus.PICKED_UP):
                continue
            if _overlaps(req.start, req.end, b.start, b.end):
                raise ValueError(ERR_VEHICLE_CONFLICT)

        # Create booking
        now = datetime.now(UTC)
        booking = Booking(
            id=_next_booking_id(),
            vehicle_id=req.vehicle_id,
            student_id=req.student_id,
            start=req.start,
            end=req.end,
            status=BookingStatus.CONFIRMED,
            created_at=now,
            deadline=now + timedelta(minutes=HOLDING_PERIOD_MIN),
        )
        store.bookings[booking.id] = booking

        # Mark the vehicle as RESERVED
        vehicle.status = VehicleStatus.RESERVED
        vehicle.last_updated = now

        return _to_out(booking)
    

# ------------------------------------------------------------
# UC-03 Pick Up
# ------------------------------------------------------------

def pickup(req: PickupRequest) -> BookingOut:
    with store.lock:
        booking = store.bookings.get(req.booking_id)
        if booking is None:
            raise ValueError(ERR_BOOKING_NOT_FOUND)

        # Status gate
        if booking.status == BookingStatus.PICKED_UP:
            raise ValueError(ERR_BOOKING_ALREADY_PICKED_UP)
        if booking.status != BookingStatus.CONFIRMED:
            raise ValueError(ERR_BOOKING_NOT_PICKABLE)

        # Deadline check (expiry on access)
        now = datetime.now(UTC)
        if booking.deadline is not None and now >= booking.deadline:
            booking.status = BookingStatus.EXPIRED
            vehicle = store.vehicles.get(booking.vehicle_id)
            if vehicle is not None and vehicle.status == VehicleStatus.RESERVED:
                vehicle.status = VehicleStatus.AVAILABLE
                vehicle.last_updated = now
            raise ValueError(ERR_BOOKING_EXPIRED)

        # Vehicle checks
        vehicle = store.vehicles.get(booking.vehicle_id)
        if vehicle is None or vehicle.status != VehicleStatus.RESERVED:
            raise ValueError(ERR_VEHICLE_NOT_RESERVED)
        if vehicle.pin < MIN_RENTAL_PIN:
            raise ValueError(ERR_VEHICLE_BATTERY_TOO_LOW)

        # Atomic transition
        booking.status = BookingStatus.PICKED_UP
        vehicle.status = VehicleStatus.IN_USE
        vehicle.last_updated = now

        return _to_out(booking)


# ------------------------------------------------------------
# UC-04 Return
# ------------------------------------------------------------

def return_vehicle(req: ReturnRequest) -> BookingOut:
    with store.lock:
        booking = store.bookings.get(req.booking_id)
        if booking is None:
            raise ValueError(ERR_BOOKING_NOT_FOUND)

        if booking.status != BookingStatus.PICKED_UP:
            raise ValueError(ERR_BOOKING_NOT_ACTIVE)

        station = store.stations.get(req.station_id)
        if station is None:
            raise ValueError(ERR_STATION_NOT_FOUND)

        vehicle = store.vehicles.get(booking.vehicle_id)
        if vehicle is None:
            raise ValueError(ERR_VEHICLE_NOT_RESERVED)

        # Atomic transition
        now = datetime.now(UTC)
        booking.status = BookingStatus.COMPLETED
        vehicle.status = VehicleStatus.AVAILABLE
        vehicle.station_id = req.station_id
        vehicle.zone = station.zone
        vehicle.lat = station.lat
        vehicle.lng = station.lng
        vehicle.pin = req.final_pin
        vehicle.last_updated = now

        return _to_out(booking)