from datetime import UTC, datetime, timedelta

import pytest

from app import store
from app.schemas import (
    BookingStatus,
    PickupRequest,
    ReserveRequest,
    ReturnRequest,
    VehicleStatus,
)
from app.services.reservation_service import (
    ERR_BOOKING_ALREADY_PICKED_UP,
    ERR_BOOKING_EXPIRED,
    ERR_BOOKING_NOT_ACTIVE,
    ERR_BOOKING_NOT_FOUND,
    ERR_BOOKING_NOT_PICKABLE,
    ERR_STATION_NOT_FOUND,
    ERR_VEHICLE_BATTERY_TOO_LOW,
    ERR_VEHICLE_NOT_RESERVED,
    pickup,
    reserve,
    return_vehicle,
)


def _reserve(vehicle_id: str = "V001") -> str:
    """Helper: reserve V001 and return the booking id."""
    now = datetime.now(UTC)
    b = reserve(
        ReserveRequest(
            vehicle_id=vehicle_id,
            student_id="SV001",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=3),
        )
    )
    return b.id


# ------------------------------------------------------------
# UC-03 Pickup
# ------------------------------------------------------------

def test_pickup_success(seeded_store):
    bid = _reserve("V001")
    out = pickup(PickupRequest(booking_id=bid))

    assert out.id == bid
    assert out.status == BookingStatus.PICKED_UP
    assert store.vehicles["V001"].status == VehicleStatus.IN_USE


def test_pickup_unknown_booking_raises_not_found(seeded_store):
    with pytest.raises(ValueError) as exc:
        pickup(PickupRequest(booking_id="B999"))
    assert str(exc.value) == ERR_BOOKING_NOT_FOUND


def test_pickup_already_picked_up_raises(seeded_store):
    bid = _reserve("V001")
    pickup(PickupRequest(booking_id=bid))
    with pytest.raises(ValueError) as exc:
        pickup(PickupRequest(booking_id=bid))
    assert str(exc.value) == ERR_BOOKING_ALREADY_PICKED_UP


def test_pickup_cancelled_booking_raises_not_pickable(seeded_store):
    bid = _reserve("V001")
    store.bookings[bid].status = BookingStatus.CANCELLED
    with pytest.raises(ValueError) as exc:
        pickup(PickupRequest(booking_id=bid))
    assert str(exc.value) == ERR_BOOKING_NOT_PICKABLE


def test_pickup_expired_marks_expired_and_releases_vehicle(seeded_store):
    bid = _reserve("V001")
    # Force deadline into the past
    store.bookings[bid].deadline = datetime.now(UTC) - timedelta(minutes=1)

    with pytest.raises(ValueError) as exc:
        pickup(PickupRequest(booking_id=bid))
    assert str(exc.value) == ERR_BOOKING_EXPIRED

    # Side-effects: booking EXPIRED, vehicle back to AVAILABLE
    assert store.bookings[bid].status == BookingStatus.EXPIRED
    assert store.vehicles["V001"].status == VehicleStatus.AVAILABLE


def test_pickup_battery_too_low_keeps_hold(seeded_store):
    bid = _reserve("V001")
    store.vehicles["V001"].pin = 10  # below MIN_RENTAL_PIN

    with pytest.raises(ValueError) as exc:
        pickup(PickupRequest(booking_id=bid))
    assert str(exc.value) == ERR_VEHICLE_BATTERY_TOO_LOW

    # Hold kept (UC-03 A4)
    assert store.bookings[bid].status == BookingStatus.CONFIRMED
    assert store.vehicles["V001"].status == VehicleStatus.RESERVED


# ------------------------------------------------------------
# UC-04 Return
# ------------------------------------------------------------

def test_return_success_relocates_vehicle(seeded_store):
    bid = _reserve("V001")
    pickup(PickupRequest(booking_id=bid))

    out = return_vehicle(
        ReturnRequest(booking_id=bid, station_id="S3", final_pin=55)
    )

    assert out.status == BookingStatus.COMPLETED

    v = store.vehicles["V001"]
    assert v.status == VehicleStatus.AVAILABLE
    assert v.station_id == "S3"
    assert v.zone == "B"          # S3 is in zone B
    assert v.pin == 55
    assert v.lat == store.stations["S3"].lat
    assert v.lng == store.stations["S3"].lng


def test_return_unknown_booking_raises_not_found(seeded_store):
    with pytest.raises(ValueError) as exc:
        return_vehicle(ReturnRequest(booking_id="B999", station_id="S3", final_pin=50))
    assert str(exc.value) == ERR_BOOKING_NOT_FOUND


def test_return_not_picked_up_raises_not_active(seeded_store):
    bid = _reserve("V001")  # CONFIRMED, not picked up
    with pytest.raises(ValueError) as exc:
        return_vehicle(ReturnRequest(booking_id=bid, station_id="S3", final_pin=50))
    assert str(exc.value) == ERR_BOOKING_NOT_ACTIVE


def test_return_unknown_station_raises_not_found(seeded_store):
    bid = _reserve("V001")
    pickup(PickupRequest(booking_id=bid))
    with pytest.raises(ValueError) as exc:
        return_vehicle(ReturnRequest(booking_id=bid, station_id="S999", final_pin=50))
    assert str(exc.value) == ERR_STATION_NOT_FOUND


# ------------------------------------------------------------
# Full lifecycle
# ------------------------------------------------------------

def test_full_lifecycle_reserve_pickup_return(seeded_store):
    bid = _reserve("V001")
    assert store.vehicles["V001"].status == VehicleStatus.RESERVED

    pickup(PickupRequest(booking_id=bid))
    assert store.vehicles["V001"].status == VehicleStatus.IN_USE
    assert store.bookings[bid].status == BookingStatus.PICKED_UP

    return_vehicle(ReturnRequest(booking_id=bid, station_id="S4", final_pin=40))
    assert store.vehicles["V001"].status == VehicleStatus.AVAILABLE
    assert store.bookings[bid].status == BookingStatus.COMPLETED