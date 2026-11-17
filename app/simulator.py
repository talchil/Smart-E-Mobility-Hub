import asyncio
import random
import os
from app import store
from app.schemas import VehicleStatus

async def run_simulation_loop():
    """Infinite loop, runs every 5 seconds."""
    while True:
        await asyncio.sleep(5)
        with store.lock:
            for vehicle in store.vehicles.values():
                if vehicle.status == VehicleStatus.IN_USE:
                    # 1. Decrease battery
                    battery_drop = random.randint(1, 2)
                    vehicle.pin = max(0, vehicle.pin - battery_drop)
                    
                    # 2. Moving
                    lat_shift = random.uniform(-0.001, 0.001)
                    lng_shift = random.uniform(-0.001, 0.001)

                    vehicle.lat = round(vehicle.lat + lat_shift, 6)
                    vehicle.lng = round(vehicle.lng + lng_shift, 6)

def start_simulator():
    sim_enabled = os.getenv("SIM_ENABLED", "False").lower() in ("true", "1", "yes")
    if sim_enabled:
        print("[simulator] VROOM! Simulator is ENABLED. Starting background loop...")
        # Bắn vòng lặp vào chạy ngầm (fire-and-forget task)
        asyncio.create_task(run_simulation_loop())
    else:
        print("[simulator] Simulator is DISABLED. Set SIM_ENABLED=True to activate.")