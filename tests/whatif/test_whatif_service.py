import pytest
from app import store
from app.services import whatif_service
from app.schemas import WhatIfRequest

def test_evaluate_station_full_scenario(seeded_store):
    """Test the station_full scenario where station capacity is reduced."""
    # Record the original capacity of station S001
    original_capacity = store.stations["S1"].capacity
    
    # Mock request: Station S001 is closed (capacity = 0), with 5 vehicles attempting to return
    req = WhatIfRequest(
        scenario="station_full",
        params={"station_id": "S1", "capacity": 0, "incoming_returns": 5}
    )
    
    result = whatif_service.evaluate_whatif(req)
    
    # Verify the response data structure and values
    assert result.scenario == "station_full"
    assert result.baseline["capacity"] == original_capacity
    assert result.scenario_result["capacity"] == 0
    assert result.scenario_result["rejected_returns"] == 5 # All 5 vehicles are rejected due to 0 capacity
    
    # Check the delta (difference between scenario and baseline)
    assert result.delta["capacity"] == -original_capacity
    assert result.delta["rejected_returns"] > 0 # Rejected returns must increase compared to the baseline


def test_evaluate_demand_surge_scenario(seeded_store):
    """Test the demand_surge scenario where reservation requests spike."""
    # Mock request: Spike of 20 requests in Zone A
    req = WhatIfRequest(
        scenario="demand_surge",
        params={"zone": "Zone A", "surge_requests": 20, "base_requests": 5}
    )
    
    result = whatif_service.evaluate_whatif(req)
    
    assert result.scenario == "demand_surge"
    assert result.baseline["surge_requests"] == 5
    assert result.scenario_result["surge_requests"] == 20
    
    # Since vehicles are limited, 20 requests will likely result in unmet demand
    assert result.scenario_result["unmet_demand"] > 0
    # The delta for unmet demand must be a positive number (increased rejections)
    assert result.delta["unmet_demand"] > 0


def test_whatif_isolation_nif_10(seeded_store):
    """
    VERIFY NIF-10: Ensure the simulation runs in complete isolation
    and does not mutate the actual operational data in the store.
    """
    original_capacity = store.stations["S1"].capacity
    
    req = WhatIfRequest(
        scenario="station_full",
        params={"station_id": "S1", "capacity": 0}
    )
    
    # Execute the what-if simulation
    whatif_service.evaluate_whatif(req)
    
    # Verify the actual store: The capacity of S001 must remain unchanged
    assert store.stations["S1"].capacity == original_capacity, "NIF-10 Violated: Operational state was mutated!"


def test_unsupported_scenario(seeded_store):
    """Test the system's behavior when an unsupported scenario is requested."""
    req = WhatIfRequest(scenario="alien_attack", params={})
    
    with pytest.raises(ValueError, match="UNSUPPORTED_SCENARIO"):
        whatif_service.evaluate_whatif(req)