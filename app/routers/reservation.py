from fastapi import APIRouter, HTTPException

from app.schemas import BookingOut, ErrorOut, ReserveRequest
from app.services import reservation_service

router = APIRouter(prefix="/reserve", tags=["UC-02 Reserve"])


# Map service error codes to HTTP statuses.
_ERROR_STATUS = {
    reservation_service.ERR_VEHICLE_NOT_FOUND: 404,
    reservation_service.ERR_VEHICLE_NOT_ELIGIBLE: 409,
    reservation_service.ERR_VEHICLE_CONFLICT: 409,
    reservation_service.ERR_INVALID_TIME_RANGE: 400,
}


@router.post(
    "",
    response_model=BookingOut,
    status_code=201,
    responses={
        400: {"model": ErrorOut, "description": "Invalid time range"},
        404: {"model": ErrorOut, "description": "Vehicle not found"},
        409: {"model": ErrorOut, "description": "Vehicle not eligible or conflicting booking"},
    },
)
def reserve(req: ReserveRequest) -> BookingOut:
    """Reserve a vehicle for the given time window.

    On success, returns 201 with the created BookingOut. The vehicle
    is marked RESERVED and the booking has a pickup deadline of
    HOLDING_PERIOD_MIN minutes from now.
    """
    try:
        return reservation_service.reserve(req)
    except ValueError as exc:
        code = str(exc)
        status = _ERROR_STATUS.get(code, 400)
        raise HTTPException(status_code=status, detail=code) from exc