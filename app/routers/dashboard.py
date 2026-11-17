from fastapi import APIRouter, Query
from app.schemas import DashboardOut
from app.services import dashboard_service

router = APIRouter(tags=["UC-09 Dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(
    zone: str | None = Query(
        default=None,
        description="Optional zone filter, e.g. A or B",
    ),
) -> DashboardOut:
    return dashboard_service.get_dashboard(zone=zone)