from fastapi import APIRouter, HTTPException

from app.schemas import ChargingOut, ErrorOut, ScheduleChargingRequest
from app.services import charging_service

router = APIRouter(prefix="/charging", tags=["UC-06 Schedule Charging"])


_ERROR_STATUS = {
    charging_service.ERR_VEHICLE_NOT_FOUND: 404,
    charging_service.ERR_STATION_NOT_FOUND: 404,
    charging_service.ERR_BATTERY_FULL: 400,
    charging_service.ERR_INVALID_TIME_RANGE: 400,
    charging_service.ERR_CHARGING_DUPLICATE_ACTIVE: 409,
    charging_service.ERR_CHARGING_VEHICLE_OVERLAP: 409,
}


@router.post(
    "/schedule",
    response_model=ChargingOut,
    status_code=201,
    responses={
        400: {"model": ErrorOut, "description": "Battery full or invalid time range"},
        404: {"model": ErrorOut, "description": "Vehicle or station not found"},
        409: {"model": ErrorOut, "description": "Duplicate active or overlapping request"},
    },
)
def schedule_charging(req: ScheduleChargingRequest) -> ChargingOut:
    try:
        created = charging_service.schedule_charging(req)
    except ValueError as exc:
        code = str(exc)
        status = _ERROR_STATUS.get(code, 400)
        raise HTTPException(status_code=status, detail=code) from exc

    # Run a cycle so the caller sees the final status right away
    charging_service.run_scheduling_cycle()
    return charging_service.list_requests() and _find(created.id)


def _find(slot_id: str) -> ChargingOut:
    """Return the current state of a charging slot by id."""
    for c in charging_service.list_requests():
        if c.id == slot_id:
            return c
    # Should not happen
    raise HTTPException(status_code=500, detail="INTERNAL_SLOT_NOT_FOUND")


@router.post("/run-cycle", response_model=list[ChargingOut])
def run_cycle() -> list[ChargingOut]:
    """Run one scheduling cycle manually and return the confirmed requests."""
    return charging_service.run_scheduling_cycle()


@router.get("/requests", response_model=list[ChargingOut])
def list_requests() -> list[ChargingOut]:
    """List all charging requests (for queue inspection during demos)."""
    return charging_service.list_requests()