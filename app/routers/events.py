from fastapi import APIRouter, HTTPException

from app.schemas import ErrorOut, EventRequest, EventResponse
from app.services import event_service

router = APIRouter(tags=["UC-14 Operational Events"])

@router.post(
    "/events",
    response_model=EventResponse,
    responses={
        400: {"model": ErrorOut, "description": "Invalid event sequence or state"}
    }
)
def process_event_webhook(req: EventRequest) -> EventResponse:
    """
    Ingest real-time IoT events from vehicles or stations.
    
    Guarantees:
    - Idempotent: Safe to retry (event_id is checked).
    - Consistent: State transitions are strictly validated.
    """
    try:
        return event_service.process_event(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))