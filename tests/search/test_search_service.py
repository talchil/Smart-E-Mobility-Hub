from app.services.search_service import search


def test_search_no_filter_returns_only_rentable(seeded_store):
    """No filters -> only AVAILABLE vehicles with pin >= MIN_RENTAL_PIN."""
    results = search()
    assert [v.id for v in results] == ["V006", "V001", "V002", "V007", "V003", "V009"]


def test_search_filter_by_zone(seeded_store):
    """zone=A -> only zone A vehicles that are rentable."""
    results = search(zone="A")
    assert [v.id for v in results] == ["V001", "V002", "V003"]


def test_search_filter_by_min_battery(seeded_store):
    """min_battery=50 -> only vehicles with pin >= 50."""
    results = search(min_battery=50)
    assert [v.id for v in results] == ["V006", "V001", "V002", "V007"]


def test_search_filter_by_vehicle_type(seeded_store):
    """vehicle_type=scooter -> only scooters."""
    results = search(vehicle_type="scooter")
    assert [v.id for v in results] == ["V006", "V003", "V009"]


def test_search_no_match_returns_empty(seeded_store):
    """Non-existent zone -> empty list."""
    results = search(zone="Z")
    assert results == []


def test_search_sort_order(seeded_store):
    """Results are sorted by battery descending."""
    results = search()
    pins = [v.pin for v in results]
    assert pins == sorted(pins, reverse=True)


def test_search_excludes_low_battery(seeded_store):
    """Vehicles below MIN_RENTAL_PIN (V004=15, V008=10) are excluded
    even when min_battery=0."""
    results = search(min_battery=0)
    ids = [v.id for v in results]
    assert "V004" not in ids
    assert "V008" not in ids