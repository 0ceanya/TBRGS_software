"""Tests for FastAPI endpoints (TC-10, TC-11)."""

import pytest


class TestGraphAPI:
    """TC-10: Graph sensor endpoints."""

    def test_sensors_returns_325(self, client):
        """TC-10: GET /api/graph/sensors returns all 325 sensors."""
        response = client.get("/api/graph/sensors")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 325
        assert len(data["sensors"]) == 325

        # Each sensor has id, lat, lon
        sensor = data["sensors"][0]
        assert "id" in sensor
        assert "lat" in sensor
        assert "lon" in sensor

    def test_algorithms_list(self, client):
        """Available algorithms endpoint returns expected set."""
        response = client.get("/api/graph/algorithms")
        assert response.status_code == 200
        algos = response.json()["algorithms"]
        assert "AS" in algos
        assert "BFS" in algos
        assert "CUS1" in algos


class TestRoutesAPI:
    """TC-11: Route finding endpoint."""

    def test_find_routes_returns_results(self, client):
        """TC-11: POST /api/routes/find returns valid routes."""
        response = client.post(
            "/api/routes/find",
            json={
                "origin": "402365",
                "destination": "401129",
                "model": "mock",
                "algorithm": "AS",
                "k": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "routes" in data
        assert len(data["routes"]) >= 1

        route = data["routes"][0]
        assert route["path"][0] == "402365"
        assert route["path"][-1] == "401129"
        assert route["travel_time_seconds"] > 0
        assert data["endpoints"]["origin"]["source"] == "sensor"
        assert data["endpoints"]["destination"]["source"] == "sensor"

    def test_find_routes_custom_coordinates(self, client):
        """POST with lat/lon snaps to sensors and returns endpoints metadata."""
        response = client.post(
            "/api/routes/find",
            json={
                "origin": "",
                "destination": "",
                "origin_lat": 37.4,
                "origin_lon": -121.95,
                "dest_lat": 37.35,
                "dest_lon": -121.9,
                "model": "mock",
                "algorithm": "AS",
                "k": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("error") is None
        assert len(data["routes"]) >= 1
        assert data["endpoints"]["origin"]["source"] == "coordinates"
        assert data["endpoints"]["destination"]["source"] == "coordinates"
        assert data["routes"][0]["path"][0] == data["endpoints"]["origin"]["sensor_id"]

    def test_invalid_sensor_returns_error(self, client):
        """Invalid sensor ID returns error in response."""
        response = client.post(
            "/api/routes/find",
            json={
                "origin": "INVALID",
                "destination": "401129",
                "model": "mock",
                "algorithm": "AS",
                "k": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert data["routes"] == []

    def test_find_routes_k_out_of_range_422(self, client):
        """k above max returns validation error."""
        response = client.post(
            "/api/routes/find",
            json={
                "origin": "402365",
                "destination": "401129",
                "model": "mock",
                "algorithm": "AS",
                "k": 10,
            },
        )
        assert response.status_code == 422

    def test_test_cases_list(self, client):
        """GET /api/test-cases lists JSON fixtures with endpoints."""
        response = client.get("/api/test-cases")
        assert response.status_code == 200
        data = response.json()
        assert "test_cases" in data
        assert data["count"] >= 1
        first = data["test_cases"][0]
        assert first["id"].startswith("tc_")
        assert first["default_origin"]
        assert first["default_destination"]

    def test_scenarios_list(self, client):
        """GET /api/scenarios returns preset traffic scenarios."""
        response = client.get("/api/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert data["count"] >= 1
        first = data["scenarios"][0]
        assert "id" in first
        assert "label" in first

    def test_find_routes_includes_horizon_milestones(self, client):
        """Multi-step forecast returns horizon_milestones in response."""
        response = client.post(
            "/api/routes/find",
            json={
                "origin": "402365",
                "destination": "401129",
                "model": "mock",
                "algorithm": "AS",
                "k": 2,
                "milestone_steps": [1, 3],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("error") is None
        assert "horizon_milestones" in data
        assert len(data["horizon_milestones"]) == 2
        assert data["horizon_milestones"][0]["step"] == 1
        assert data["horizon_milestones"][1]["step"] == 3
        assert len(data["horizon_milestones"][0]["routes"]) >= 1
