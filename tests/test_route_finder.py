"""Tests for route finding orchestrator (TC-09)."""

from src.routing.route_finder import find_routes


class TestRouteFinder:
    """End-to-end route finding with mock provider."""

    def test_horizon_milestones_multiple_steps(self):
        """Multiple milestone steps each produce a route list."""
        outcome = find_routes(
            npz_path="data/graph.npz",
            origin_sensor="402365",
            dest_sensor="401129",
            model_name="mock",
            algorithm="AS",
            k=2,
            milestone_steps=[1, 3],
        )
        assert len(outcome.horizon_milestones) == 2
        assert outcome.horizon_milestones[0].step == 1
        assert outcome.horizon_milestones[1].step == 3
        assert len(outcome.routes) >= 1
        assert outcome.routes == outcome.horizon_milestones[0].routes


class TestRouteFinderBasics:
    """TC-09: End-to-end route finding with mock provider."""

    def test_find_routes_mock(self):
        """TC-09: Full pipeline produces valid routes from 402365 to 401129."""
        outcome = find_routes(
            npz_path="data/graph.npz",
            origin_sensor="402365",
            dest_sensor="401129",
            model_name="mock",
            algorithm="AS",
            k=3,
        )

        assert len(outcome.routes) >= 1

        best = outcome.routes[0]
        assert best.path_sensor_ids[0] == "402365"
        assert best.path_sensor_ids[-1] == "401129"
        assert best.total_travel_time_seconds > 0
        assert best.total_distance_km > 0
        assert best.num_sensors >= 2
        assert best.algorithm == "AS"
        assert best.model == "mock"
        assert outcome.origin["source"] == "sensor"
        assert outcome.destination["source"] == "sensor"
        assert len(outcome.horizon_milestones) == 1

    def test_find_routes_sorted(self):
        """Routes should be sorted by ascending travel time."""
        outcome = find_routes(
            npz_path="data/graph.npz",
            origin_sensor="402365",
            dest_sensor="401129",
            model_name="mock",
            algorithm="AS",
            k=3,
        )

        results = outcome.routes
        if len(results) > 1:
            times = [r.total_travel_time_seconds for r in results]
            assert times == sorted(times)

    def test_invalid_sensor_raises(self):
        """Invalid sensor ID should raise ValueError."""
        import pytest

        with pytest.raises(ValueError, match="not in graph"):
            find_routes(
                origin_sensor="INVALID",
                dest_sensor="401129",
                model_name="mock",
            )

    def test_find_routes_custom_coordinates_snap(self):
        """Custom lat/lon snaps to nearest sensors and finds a route."""
        outcome = find_routes(
            npz_path="data/graph.npz",
            origin_sensor="",
            dest_sensor="",
            origin_lat=37.4,
            origin_lon=-121.95,
            dest_lat=37.35,
            dest_lon=-121.9,
            model_name="mock",
            algorithm="AS",
            k=2,
        )
        assert len(outcome.routes) >= 1
        assert outcome.origin["source"] == "coordinates"
        assert outcome.destination["source"] == "coordinates"
        assert outcome.routes[0].path_sensor_ids[0] == outcome.origin["sensor_id"]
        assert outcome.routes[0].path_sensor_ids[-1] == outcome.destination["sensor_id"]
