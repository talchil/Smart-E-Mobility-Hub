from fastapi import APIRouter, HTTPException
from app.schemas import BookingOut, ErrorOut, PickupRequest, ReturnRequest
from app.services import reservation_service

router = APIRouter(tags=["UC-03/04 Pickup & Return"])


_PICKUP_ERROR_STATUS = {
    reservation_service.ERR_BOOKING_NOT_FOUND: 404,
    reservation_service.ERR_BOOKING_ALREADY_PICKED_UP: 409,
    reservation_service.ERR_BOOKING_NOT_PICKABLE: 409,
    reservation_service.ERR_BOOKING_EXPIRED: 409,
    reservation_service.ERR_VEHICLE_NOT_RESERVED: 409,
    reservation_service.ERR_VEHICLE_BATTERY_TOO_LOW: 409,
}

_RETURN_ERROR_STATUS = {
    reservation_service.ERR_BOOKING_NOT_FOUND: 404,
    reservation_service.ERR_BOOKING_NOT_ACTIVE: 409,
    reservation_service.ERR_STATION_NOT_FOUND: 404,
    reservation_service.ERR_VEHICLE_NOT_RESERVED: 409,
}


@router.post(
    "/pickup",
    response_model=BookingOut,
    status_code=200,
    responses={
        404: {"model": ErrorOut, "description": "Booking not found"},
        409: {"model": ErrorOut, "description": "Booking not pickable / expired / vehicle not reserved / battery too low"},
    },
)
def pickup(req: PickupRequest) -> BookingOut:
    """Pick up a reserved vehicle, starting an active rental."""
    try:
        return reservation_service.pickup(req)
    except ValueError as exc:
        code = str(exc)
        status = _PICKUP_ERROR_STATUS.get(code, 400)
        raise HTTPException(status_code=status, detail=code) from exc


@router.post(
    "/return",
    response_model=BookingOut,
    status_code=200,
    responses={
        404: {"model": ErrorOut, "description": "Booking or station not found"},
        409: {"model": ErrorOut, "description": "Booking not active"},
    },
)
def return_vehicle(req: ReturnRequest) -> BookingOut:
    """Return a rented vehicle to a station and complete the rental."""
    try:
        return reservation_service.return_vehicle(req)
    except ValueError as exc:
        code = str(exc)
        status = _RETURN_ERROR_STATUS.get(code, 400)
        raise HTTPException(status_code=status, detail=code) from exc