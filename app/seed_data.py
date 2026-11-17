from datetime import datetime, UTC
from app import store
from app.schemas import Station, Vehicle, VehicleStatus


# ------------------------------------------------------------
# Stations
# ------------------------------------------------------------

STATIONS = [
    {"id": "S1", "zone": "A", "name": "Hub Dormitory A",   "capacity": 20, "slots_total": 5, "lat": 10.7626, "lng": 106.6602},
    {"id": "S2", "zone": "A", "name": "Hub Canteen A",     "capacity": 15, "slots_total": 3, "lat": 10.7631, "lng": 106.6615},
    {"id": "S3", "zone": "B", "name": "Hub Library B",     "capacity": 25, "slots_total": 6, "lat": 10.7640, "lng": 106.6621},
    {"id": "S4", "zone": "B", "name": "Hub Stadium B",     "capacity": 10, "slots_total": 2, "lat": 10.7652, "lng": 106.6638},
]


# ------------------------------------------------------------
# Vehicles
# ------------------------------------------------------------

# Distribution:
# - 5 vehicles in zone A, 5 in zone B
# - pin ranges from 10 to 95 (two vehicles below MIN_RENTAL_PIN=20
#   so the UC-01 filter can be demonstrated)
# - statuses: 8 AVAILABLE, 1 IN_USE, 1 MAINTENANCE
# - types: mixed bike / scooter
VEHICLES = [
    # --- Zone A ---
    {"id": "V001", "zone": "A", "vehicle_type": "bike",    "pin": 85, "status": VehicleStatus.AVAILABLE,   "station_id": "S1", "lat": 10.7626, "lng": 106.6602},
    {"id": "V002", "zone": "A", "vehicle_type": "bike",    "pin": 60, "status": VehicleStatus.AVAILABLE,   "station_id": "S1", "lat": 10.7626, "lng": 106.6602},
    {"id": "V003", "zone": "A", "vehicle_type": "scooter", "pin": 45, "status": VehicleStatus.AVAILABLE,   "station_id": "S2", "lat": 10.7631, "lng": 106.6615},
    {"id": "V004", "zone": "A", "vehicle_type": "bike",    "pin": 15, "status": VehicleStatus.AVAILABLE,   "station_id": "S2", "lat": 10.7631, "lng": 106.6615},
    {"id": "V005", "zone": "A", "vehicle_type": "bike",    "pin": 70, "status": VehicleStatus.IN_USE,      "station_id": "S1", "lat": 10.7626, "lng": 106.6602},
    # --- Zone B ---
    {"id": "V006", "zone": "B", "vehicle_type": "scooter", "pin": 95, "status": VehicleStatus.AVAILABLE,   "station_id": "S3", "lat": 10.7640, "lng": 106.6621},
    {"id": "V007", "zone": "B", "vehicle_type": "bike",    "pin": 55, "status": VehicleStatus.AVAILABLE,   "station_id": "S3", "lat": 10.7640, "lng": 106.6621},
    {"id": "V008", "zone": "B", "vehicle_type": "bike",    "pin": 10, "status": VehicleStatus.AVAILABLE,   "station_id": "S4", "lat": 10.7652, "lng": 106.6638},
    {"id": "V009", "zone": "B", "vehicle_type": "scooter", "pin": 30, "status": VehicleStatus.AVAILABLE,   "station_id": "S4", "lat": 10.7652, "lng": 106.6638},
    {"id": "V010", "zone": "B", "vehicle_type": "bike",    "pin": 80, "status": VehicleStatus.MAINTENANCE, "station_id": "S3", "lat": 10.7640, "lng": 106.6621},
]


# ------------------------------------------------------------
# Loader
# ------------------------------------------------------------

def load_seed() -> None:
    """Reset the store, then populate it with hard-coded demo data."""
    store.reset()
    now = datetime.now(UTC)

    with store.lock:
        for s in STATIONS:
            store.stations[s["id"]] = Station(**s)

        for v in VEHICLES:
            data = dict(v)
            data["last_updated"] = now
            store.vehicles[data["id"]] = Vehicle(**data)