import copy
from app import store
from app.schemas import WhatIfOut, WhatIfRequest, VehicleStatus, MIN_RENTAL_PIN

def _simulate_station_full(state: dict, params: dict) -> dict:
    """Simulate the impact of reduced capacity at a specific station."""
    station_id = params.get("station_id")
    if not station_id or station_id not in state["stations"]:
        raise ValueError("INVALID_STATION_ID")
        
    station = state["stations"][station_id]
    
    # Apply scenario parameter (e.g. simulate blocked spaces or full closure)
    if "capacity" in params:
        station.capacity = params["capacity"]
        
    parked_count = sum(1 for v in state["vehicles"].values() if v.station_id == station_id)
    available_slots = max(0, station.capacity - parked_count)
    
    # Simulate N vehicles trying to return to this station
    incoming_returns = params.get("incoming_returns", 5)
    accepted = min(incoming_returns, available_slots)
    rejected = max(0, incoming_returns - available_slots)
    
    return {
        "capacity": station.capacity,
        "parked_vehicles": parked_count,
        "available_slots": available_slots,
        "incoming_returns": incoming_returns,
        "accepted_returns": accepted,
        "rejected_returns": rejected,
    }

def _simulate_demand_surge(state: dict, params: dict) -> dict:
    """Simulate a sudden spike in reservation requests."""
    zone = params.get("zone")
    surge_requests = params.get("surge_requests", 10)
    
    rentable_count = 0
    for v in state["vehicles"].values():
        if v.status == VehicleStatus.AVAILABLE and v.pin >= MIN_RENTAL_PIN:
            if zone is None or v.zone == zone:
                rentable_count += 1
                
    served = min(surge_requests, rentable_count)
    unmet = max(0, surge_requests - rentable_count)
    
    return {
        "surge_requests": surge_requests,
        "rentable_vehicles": rentable_count,
        "served_demand": served,
        "unmet_demand": unmet,
    }

def evaluate_whatif(req: WhatIfRequest) -> WhatIfOut:
    """
    Evaluate a hypothetical scenario by running it in an isolated memory state (NIF-10).
    """
    # 1. Snapshot generation under lock for consistency
    with store.lock:
        raw_snapshot = store.snapshot()
        
    # 2. Deepcopy to completely isolate from operational state
    baseline_state = copy.deepcopy(raw_snapshot)
    scenario_state = copy.deepcopy(raw_snapshot)
    
    # 3. Route to the correct simulation
    if req.scenario == "station_full":
        # Baseline assumes current operational parameters
        base_params = {"station_id": req.params.get("station_id"), "incoming_returns": req.params.get("incoming_returns", 5)}
        baseline_res = _simulate_station_full(baseline_state, base_params)
        # Scenario applies the user's "What-if" parameters
        scenario_res = _simulate_station_full(scenario_state, req.params)
        
    elif req.scenario == "demand_surge":
        # Baseline assumes a normal request volume (e.g. 5 requests)
        base_params = {"zone": req.params.get("zone"), "surge_requests": req.params.get("base_requests", 5)}
        baseline_res = _simulate_demand_surge(baseline_state, base_params)
        scenario_res = _simulate_demand_surge(scenario_state, req.params)
        
    else:
        raise ValueError("UNSUPPORTED_SCENARIO")

    # 4. Calculate delta (Scenario vs Baseline)
    delta = {
        key: scenario_res[key] - baseline_res.get(key, 0)
        for key in scenario_res if isinstance(scenario_res[key], int)
    }
    
    return WhatIfOut(
        scenario=req.scenario,
        baseline=baseline_res,
        scenario_result=scenario_res,
        delta=delta
    )