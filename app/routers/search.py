from fastapi import APIRouter, Query

from app.schemas import VehicleOut
from app.services import search_service

router = APIRouter(prefix="/search", tags=["UC-01 Search"])


@router.get("", response_model=list[VehicleOut])
def search_vehicles(
    zone: str | None = Query(default=None, description="Zone filter, e.g. A or B"),
    station_id: str | None = Query(default=None, description="Station filter, e.g. S1"),
    vehicle_type: str | None = Query(default=None, description="Vehicle type, e.g. bike or scooter"),
    min_battery: int = Query(default=0, ge=0, le=100, description="Minimum battery percentage"),
) -> list[VehicleOut]:
    return search_service.search(
        zone=zone,
        station_id=station_id,
        vehicle_type=vehicle_type,
        min_battery=min_battery,
    )