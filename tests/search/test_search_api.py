def test_api_search_returns_200_and_list(client, seeded_store):
    """GET /search returns 200 and a JSON list of VehicleOut."""
    r = client.get("/search")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 6
    # Pydantic serialization sanity check
    assert body[0]["status"] == "AVAILABLE"
    assert "id" in body[0]


def test_api_search_filter_zone(client, seeded_store):
    """GET /search?zone=A returns only zone A vehicles."""
    r = client.get("/search?zone=A")
    assert r.status_code == 200
    assert [v["id"] for v in r.json()] == ["V001", "V002", "V003"]


def test_api_search_invalid_min_battery_returns_422(client, seeded_store):
    """min_battery=150 is rejected by Pydantic with HTTP 422."""
    r = client.get("/search?min_battery=150")
    assert r.status_code == 422
    assert "detail" in r.json()


def test_api_search_no_match_returns_empty_list(client, seeded_store):
    """Non-existent zone returns 200 with an empty list."""
    r = client.get("/search?zone=Z")
    assert r.status_code == 200
    assert r.json() == []
