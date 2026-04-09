"""Tests for route finding orchestrator (TC-09)."""

from src.routing.route_finder import find_routes


class TestRouteFinder:
    """TC-09: End-to-end route finding with mock provider."""

    def test_find_routes_mock(self):
        """TC-09: Full pipeline produces valid routes from 402365 to 401129."""
        results = find_routes(
            npz_path="data/graph.npz",
            origin_sensor="402365",
            dest_sensor="401129",
            model_name="mock",
            algorithm="AS",
            k=3,
        )

        assert len(results) >= 1

        best = results[0]
        assert best.path_sensor_ids[0] == "402365"
        assert best.path_sensor_ids[-1] == "401129"
        assert best.total_travel_time_seconds > 0
        assert best.total_distance_km > 0
        assert best.num_sensors >= 2
        assert best.algorithm == "AS"
        assert best.model == "mock"

    def test_find_routes_sorted(self):
        """Routes should be sorted by ascending travel time."""
        results = find_routes(
            npz_path="data/graph.npz",
            origin_sensor="402365",
            dest_sensor="401129",
            model_name="mock",
            algorithm="AS",
            k=3,
        )

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
