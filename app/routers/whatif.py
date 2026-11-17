from fastapi import APIRouter, HTTPException

from app.schemas import ErrorOut, WhatIfOut, WhatIfRequest
from app.services import whatif_service

router = APIRouter(tags=["UC-12 What-if Scenario"])

@router.post(
    "/what-if",
    response_model=WhatIfOut,
    responses={
        400: {"model": ErrorOut, "description": "Invalid scenario or parameters"}
    }
)
def evaluate_whatif(req: WhatIfRequest) -> WhatIfOut:
    try:
        return whatif_service.evaluate_whatif(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))