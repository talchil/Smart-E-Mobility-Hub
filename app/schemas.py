from datetime import datetime, UTC
from enum import Enum
from typing import Optional
from typing import Any, Dict

from pydantic import BaseModel, Field


# ============================================================
# 6. CONSTANTS (placed first so Requests can reference them)
# ============================================================

HOLDING_PERIOD_MIN = 15   # UC-02: pickup deadline = now + 15 minutes
MIN_RENTAL_PIN     = 20   # UC-01: minimum battery to be rentable
SLOT_DURATION_MIN  = 30   # UC-06: default charging slot duration


# ============================================================
# 1. ENUMS
# ============================================================

class VehicleStatus(str, Enum):
    """Vehicle state - state machine for UC-03/04."""
    AVAILABLE   = "AVAILABLE"    # ready to be rented
    RESERVED    = "RESERVED"     # held by a CONFIRMED booking
    IN_USE      = "IN_USE"       # currently rented (after pickup)
    RETURNED    = "RETURNED"     # returned, awaiting processing
    MAINTENANCE = "MAINTENANCE"  # faulty / waiting for charge / maintenance
    CHARGING = "CHARGING"


class BookingStatus(str, Enum):
    """Booking state - UC-02/03/04."""
    CONFIRMED = "CONFIRMED"   # vehicle held, awaiting pickup
    PICKED_UP = "PICKED_UP"   # picked up -> rental is active
    COMPLETED = "COMPLETED"   # vehicle returned
    CANCELLED = "CANCELLED"   # cancelled by the student
    EXPIRED   = "EXPIRED"     # pickup deadline passed without pickup


class ChargingStatus(str, Enum):
    """Charging request state - UC-06."""
    PENDING     = "PENDING"      # waiting for a slot
    CONFIRMED   = "CONFIRMED"    # slot assigned
    CHARGING    = "CHARGING"     # charging in progress
    COMPLETED   = "COMPLETED"    # charging finished
    CANCELLED   = "CANCELLED"    # cancelled
    INTERRUPTED = "INTERRUPTED"  # charging interrupted


# ============================================================
# 2. INTERNAL MODELS (stored in the in-memory store)
# ============================================================

class Vehicle(BaseModel):
    """Electric vehicle - core entity for UC-01/02/03/04/14."""
    id: str
    zone: str
    vehicle_type: str = "bike"
    pin: int = Field(ge=0, le=100, description="Battery level 0-100%")
    status: VehicleStatus = VehicleStatus.AVAILABLE
    station_id: Optional[str] = None
    lat: float
    lng: float
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Station(BaseModel):
    """Charging station / hub - parking and charging location."""
    id: str
    zone: str
    name: str
    capacity: int = Field(gt=0, description="Maximum parking capacity")
    slots_total: int = Field(gt=0, description="Total charging slots")
    lat: float
    lng: float


class Booking(BaseModel):
    """Vehicle reservation - UC-02/03/04. Also represents an active rental
    when status is PICKED_UP."""
    id: str
    vehicle_id: str
    student_id: str
    start: datetime
    end: datetime
    status: BookingStatus = BookingStatus.CONFIRMED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deadline: Optional[datetime] = Field(
        default=None,
        description="Pickup deadline = created_at + HOLDING_PERIOD_MIN"
    )


class ChargingSlot(BaseModel):
    """Charging schedule request - UC-06."""
    id: str
    station_id: str
    vehicle_id: str
    start: datetime
    end: datetime
    status: ChargingStatus = ChargingStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    usage_deadline: Optional[datetime] = Field(
        default=None,
        description="Optional usage deadline used for NIF-04 priority."
    )


# ============================================================
# 3. REQUEST MODELS
# ============================================================

class ReserveRequest(BaseModel):
    """Body for POST /reserve - UC-02."""
    vehicle_id: str
    student_id: str
    start: datetime
    end: datetime


class PickupRequest(BaseModel):
    """Body for POST /pickup - UC-03."""
    booking_id: str


class ReturnRequest(BaseModel):
    """Body for POST /return - UC-04."""
    booking_id: str
    station_id: str
    final_pin: int = Field(ge=0, le=100)


class ScheduleChargingRequest(BaseModel):
    """Body for POST /charging/schedule - UC-06."""
    vehicle_id: str
    station_id: str
    start: datetime
    duration_min: int = Field(default=SLOT_DURATION_MIN, gt=0)
    usage_deadline: Optional[datetime] = Field(
        default=None,
        description="Optional deadline by which charging must be done. "
                    "Used for NIF-04 priority ordering."
    )


class WhatIfRequest(BaseModel):
    """Body for POST /what-if - UC-12."""
    scenario: str = Field(description='"demand_surge" | "station_full"')
    params: dict = Field(default_factory=dict)


# ============================================================
# 4. RESPONSE MODELS
# ============================================================

class VehicleOut(BaseModel):
    """Vehicle response - UC-01 Search, UC-03 Pickup, UC-04 Return."""
    id: str
    zone: str
    vehicle_type: str
    pin: int
    status: VehicleStatus
    station_id: Optional[str]
    lat: float
    lng: float


class StationOut(BaseModel):
    """Station response - UC-01 Search, UC-09 Dashboard."""
    id: str
    zone: str
    name: str
    capacity: int
    slots_total: int
    slots_used: int


class BookingOut(BaseModel):
    """Booking response - UC-02 Reserve, UC-03 Pickup, UC-04 Return."""
    id: str
    vehicle_id: str
    student_id: str
    status: BookingStatus
    start: datetime
    end: datetime
    deadline: Optional[datetime]


class ChargingOut(BaseModel):
    """Charging request response - UC-06 Schedule Charging."""
    id: str
    station_id: str
    vehicle_id: str
    status: ChargingStatus
    start: datetime
    end: datetime
    created_at: datetime


class DashboardOut(BaseModel):
    """Response for GET /dashboard - UC-09 Monitor Resources."""
    total_vehicles: int
    available: int
    in_use: int
    avg_pin: float
    stations: list[StationOut]
    alerts: list[str] = Field(default_factory=list)


class WhatIfOut(BaseModel):
    """Response for POST /what-if - UC-12 Evaluate What-if Scenario."""
    scenario: str
    baseline: dict
    scenario_result: dict
    delta: dict


# --- UC-14 EVENT SCHEMAS ---

class EventType(str, Enum):
    TELEMETRY = "telemetry"
    PARKING_ENTRY = "parking_entry"
    PARKING_EXIT = "parking_exit"
    CHARGING_START = "charging_start"
    CHARGING_COMPLETION = "charging_completion"

class EventRequest(BaseModel):
    event_id: str
    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    resource_id: str  # Trong context prototype này là Vehicle ID (VD: V001)
    payload: Dict[str, Any] = Field(default_factory=dict)

class EventResponse(BaseModel):
    event_id: str
    status: str
    message: str


# ============================================================
# 5. ERROR
# ============================================================

class ErrorOut(BaseModel):
    """Error response documented in OpenAPI. Runtime uses HTTPException."""
    detail: str