"""Tests for FastAPI endpoints (TC-10, TC-11)."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app

client = TestClient(create_app())


class TestGraphAPI:
    """TC-10: Graph sensor endpoints."""

    def test_sensors_returns_325(self):
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

    def test_algorithms_list(self):
        """Available algorithms endpoint returns expected set."""
        response = client.get("/api/graph/algorithms")
        assert response.status_code == 200
        algos = response.json()["algorithms"]
        assert "AS" in algos
        assert "BFS" in algos
        assert "CUS1" in algos


class TestRoutesAPI:
    """TC-11: Route finding endpoint."""

    def test_find_routes_returns_results(self):
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

    def test_invalid_sensor_returns_error(self):
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
