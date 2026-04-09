"""Tests for haversine distance calculation (TC-04)."""

from src.routing.haversine import haversine_km


class TestHaversine:
    """TC-04: Known geographic distances."""

    def test_sf_to_san_jose(self):
        """TC-04: San Francisco to San Jose is approximately 67.6 km."""
        dist = haversine_km(37.7749, -122.4194, 37.3382, -121.8863)
        assert 60.0 < dist < 75.0

    def test_zero_distance(self):
        """Same point should return 0."""
        dist = haversine_km(37.0, -122.0, 37.0, -122.0)
        assert dist == 0.0

    def test_symmetry(self):
        """Distance A->B should equal B->A."""
        d1 = haversine_km(37.7749, -122.4194, 37.3382, -121.8863)
        d2 = haversine_km(37.3382, -121.8863, 37.7749, -122.4194)
        assert abs(d1 - d2) < 0.001
