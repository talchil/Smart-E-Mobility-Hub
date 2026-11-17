def test_api_dashboard_returns_200(client, seeded_store):
    r = client.get("/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert body["total_vehicles"] == 10
    assert body["in_use"] == 1
    assert body["available"] == 6
    assert len(body["stations"]) == 4
    assert body["alerts"] == []


def test_api_dashboard_zone_filter(client, seeded_store):
    r = client.get("/dashboard?zone=A")
    assert r.status_code == 200
    body = r.json()
    assert body["total_vehicles"] == 5
    assert {s["id"] for s in body["stations"]} == {"S1", "S2"}


def test_api_dashboard_unknown_zone(client, seeded_store):
    r = client.get("/dashboard?zone=Z")
    assert r.status_code == 200
    body = r.json()
    assert body["total_vehicles"] == 0
    assert body["avg_pin"] == 0.0
    assert body["stations"] == []


def test_api_dashboard_stations_have_expected_shape(client, seeded_store):
    r = client.get("/dashboard")
    station = r.json()["stations"][0]
    for key in ("id", "zone", "name", "capacity", "slots_total", "slots_used"):
        assert key in station