from datetime import UTC, datetime, timedelta

import pytest

from app import store
from app.schemas import (
    BookingStatus,
    ReserveRequest,
    VehicleStatus,
)
from app.services.reservation_service import (
    ERR_INVALID_TIME_RANGE,
    ERR_VEHICLE_CONFLICT,
    ERR_VEHICLE_NOT_ELIGIBLE,
    ERR_VEHICLE_NOT_FOUND,
    reserve,
)


def _req(vehicle_id: str = "V001", start_offset_h: int = 1, duration_h: int = 2) -> ReserveRequest:
    now = datetime.now(UTC)
    return ReserveRequest(
        vehicle_id=vehicle_id,
        student_id="SV001",
        start=now + timedelta(hours=start_offset_h),
        end=now + timedelta(hours=start_offset_h + duration_h),
    )


# ------------------------------------------------------------
# Happy path
# ------------------------------------------------------------

def test_reserve_success_creates_booking_and_marks_vehicle(seeded_store):
    booking = reserve(_req("V001"))

    assert booking.id == "B001"
    assert booking.vehicle_id == "V001"
    assert booking.status == BookingStatus.CONFIRMED
    assert booking.deadline is not None

    # Store side-effects
    assert store.bookings["B001"].vehicle_id == "V001"
    assert store.vehicles["V001"].status == VehicleStatus.RESERVED


def test_reserve_second_booking_gets_next_id(seeded_store):
    b1 = reserve(_req("V001"))
    b2 = reserve(_req("V002"))

    assert b1.id == "B001"
    assert b2.id == "B002"
    assert len(store.bookings) == 2


# ------------------------------------------------------------
# Error paths
# ------------------------------------------------------------

def test_reserve_unknown_vehicle_raises_not_found(seeded_store):
    with pytest.raises(ValueError) as exc:
        reserve(_req("V999"))
    assert str(exc.value) == ERR_VEHICLE_NOT_FOUND


def test_reserve_vehicle_already_reserved_raises_not_eligible(seeded_store):
    reserve(_req("V001"))  # first reservation flips V001 to RESERVED
    with pytest.raises(ValueError) as exc:
        reserve(_req("V001"))
    assert str(exc.value) == ERR_VEHICLE_NOT_ELIGIBLE


def test_reserve_vehicle_in_use_raises_not_eligible(seeded_store):
    # V005 is seeded as IN_USE
    with pytest.raises(ValueError) as exc:
        reserve(_req("V005"))
    assert str(exc.value) == ERR_VEHICLE_NOT_ELIGIBLE


def test_reserve_low_battery_vehicle_raises_not_eligible(seeded_store):
    # V004 has pin 15 < MIN_RENTAL_PIN (20)
    with pytest.raises(ValueError) as exc:
        reserve(_req("V004"))
    assert str(exc.value) == ERR_VEHICLE_NOT_ELIGIBLE


def test_reserve_invalid_time_range_raises(seeded_store):
    now = datetime.now(UTC)
    bad = ReserveRequest(
        vehicle_id="V001",
        student_id="SV001",
        start=now + timedelta(hours=3),
        end=now + timedelta(hours=1),
    )
    with pytest.raises(ValueError) as exc:
        reserve(bad)
    assert str(exc.value) == ERR_INVALID_TIME_RANGE


def test_reserve_overlapping_booking_raises_conflict(seeded_store):
    # Manually keep V001 AVAILABLE so eligibility passes on the second call;
    # this isolates the conflict check from the eligibility check.
    first = reserve(_req("V001", start_offset_h=1, duration_h=2))
    store.vehicles["V001"].status = VehicleStatus.AVAILABLE

    # Same vehicle, overlapping window
    overlapping = ReserveRequest(
        vehicle_id="V001",
        student_id="SV002",
        start=first.start + timedelta(minutes=30),
        end=first.end + timedelta(minutes=30),
    )
    with pytest.raises(ValueError) as exc:
        reserve(overlapping)
    assert str(exc.value) == ERR_VEHICLE_CONFLICT