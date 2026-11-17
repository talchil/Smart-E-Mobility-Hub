from app import store
from app.schemas import EventRequest, EventResponse, EventType, VehicleStatus

def process_event(req: EventRequest) -> EventResponse:
    """Process incoming IoT or scheduled events strictly enforcing state rules."""
    with store.lock:
        # NIF-01: Idempotency (Bỏ qua sự kiện trùng lặp)
        if req.event_id in store.processed_events:
            saved_response = store.processed_events[req.event_id]
            return EventResponse(**saved_response)

        # Trích xuất resource (Trong prototype này, resource chủ yếu là Vehicle)
        vehicle = store.vehicles.get(req.resource_id)
        if not vehicle:
            raise ValueError("INVALID_RESOURCE_ID")

        # Routing theo Event Type
        if req.type == EventType.TELEMETRY:
            _handle_telemetry(vehicle, req.payload)
        elif req.type == EventType.PARKING_ENTRY:
            _handle_parking_entry(vehicle, req.payload)
        elif req.type == EventType.PARKING_EXIT:
            _handle_parking_exit(vehicle)
        elif req.type == EventType.CHARGING_START:
            _handle_charging_start(vehicle)
        elif req.type == EventType.CHARGING_COMPLETION:
            _handle_charging_completion(vehicle, req.payload)
        else:
            raise ValueError("UNSUPPORTED_EVENT_TYPE")

        # Lưu lại kết quả để chặn trùng lặp cho các request tương lai
        response_data = {
            "event_id": req.event_id,
            "status": "applied",
            "message": f"Event {req.type.value} applied successfully."
        }
        store.processed_events[req.event_id] = response_data
        
        return EventResponse(**response_data)

def _handle_telemetry(vehicle, payload: dict):
    """Cập nhật pin và vị trí GPS."""
    if "battery" in payload:
        vehicle.pin = payload["battery"]
    if "zone" in payload:
        vehicle.zone = payload["zone"]

def _handle_parking_entry(vehicle, payload: dict):
    """Xử lý xe vào trạm đỗ."""
    station_id = payload.get("station_id")
    if not station_id or station_id not in store.stations:
        raise ValueError("INVALID_STATION_ID")
    
    # Kiểm tra xem bãi còn chỗ không
    station = store.stations[station_id]
    parked_count = sum(1 for v in store.vehicles.values() if v.station_id == station_id)
    if parked_count >= station.capacity:
        raise ValueError("STATION_FULL")
        
    vehicle.station_id = station_id

def _handle_parking_exit(vehicle):
    """Xử lý xe rời trạm đỗ (Alternative Flow A3: Reject exit while charging)."""
    if not vehicle.station_id:
        raise ValueError("VEHICLE_NOT_IN_STATION")
    if vehicle.status == VehicleStatus.CHARGING:
        raise ValueError("CANNOT_EXIT_WHILE_CHARGING")
        
    vehicle.station_id = None

def _handle_charging_start(vehicle):
    """Bắt đầu sạc pin (Yêu cầu xe phải đang ở trong trạm)."""
    if not vehicle.station_id:
        raise ValueError("VEHICLE_MUST_BE_PARKED_TO_CHARGE")
    if vehicle.status == VehicleStatus.CHARGING:
        raise ValueError("ALREADY_CHARGING")
        
    vehicle.status = VehicleStatus.CHARGING

def _handle_charging_completion(vehicle, payload: dict):
    """Kết thúc sạc pin và nhả lốt sạc."""
    if vehicle.status != VehicleStatus.CHARGING:
        raise ValueError("VEHICLE_NOT_CHARGING")
        
    vehicle.status = VehicleStatus.AVAILABLE
    vehicle.pin = payload.get("final_battery", 100)