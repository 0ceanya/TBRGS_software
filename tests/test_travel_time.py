"""Tests for traffic flow to travel time conversion (TC-01 to TC-03)."""

import pytest
from src.routing.travel_time import (
    A,
    B,
    SPEED_LIMIT,
    FLOW_THRESHOLD,
    flow_to_speed,
    compute_travel_time,
)


class TestFlowToSpeed:
    """TC-01 and TC-02: flow_to_speed conversion."""

    def test_below_threshold_returns_speed_limit(self):
        """TC-01: Flow <= 351 veh/hr should return 60 km/hr."""
        assert flow_to_speed(0.0) == SPEED_LIMIT
        assert flow_to_speed(100.0) == SPEED_LIMIT
        assert flow_to_speed(200.0) == SPEED_LIMIT
        assert flow_to_speed(FLOW_THRESHOLD) == SPEED_LIMIT

    def test_at_threshold_boundary(self):
        """TC-01b: Just above threshold should be < 60 km/hr."""
        speed = flow_to_speed(FLOW_THRESHOLD + 1)
        assert speed < SPEED_LIMIT

    def test_quadratic_region_round_trip(self):
        """TC-02: Flow in quadratic region, verify round-trip consistency."""
        test_flow = 800.0
        speed = flow_to_speed(test_flow)

        # Speed should be between 32 (capacity) and 60 (speed limit)
        assert 32.0 < speed < SPEED_LIMIT

        # Round-trip: recompute flow from speed using the quadratic
        recomputed_flow = A * speed**2 + B * speed
        assert abs(recomputed_flow - test_flow) < 0.01

    def test_at_capacity(self):
        """Flow at capacity (1500) should return ~32 km/hr."""
        speed = flow_to_speed(1500.0)
        assert abs(speed - 32.0) < 0.5

    def test_negative_flow_raises(self):
        """Negative flow is invalid."""
        with pytest.raises(ValueError):
            flow_to_speed(-1.0)


class TestComputeTravelTime:
    """TC-03: End-to-end travel time computation."""

    def test_travel_time_with_intersection(self):
        """TC-03: 1 km at flow=800 + 1 intersection gives reasonable time."""
        time_sec = compute_travel_time(
            distance_km=1.0, flow=800.0, num_intersections=1
        )
        # speed ~53.86 km/hr -> drive ~66.8s + 30s delay = ~96.8s
        assert 90.0 < time_sec < 110.0

    def test_travel_time_no_traffic(self):
        """Low flow = speed limit. 1 km at 60 km/hr = 60s + 30s = 90s."""
        time_sec = compute_travel_time(
            distance_km=1.0, flow=100.0, num_intersections=1
        )
        assert abs(time_sec - 90.0) < 0.1

    def test_travel_time_multiple_intersections(self):
        """Multiple intersections add 30s each."""
        t1 = compute_travel_time(distance_km=1.0, flow=100.0, num_intersections=1)
        t3 = compute_travel_time(distance_km=1.0, flow=100.0, num_intersections=3)
        assert abs((t3 - t1) - 60.0) < 0.1  # 2 extra intersections = 60s
