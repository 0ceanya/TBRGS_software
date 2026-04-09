"""Tests for prediction providers (TC-12)."""

from src.prediction.mock_provider import MockProvider


class TestMockProvider:
    """TC-12: MockProvider determinism and correctness."""

    def test_deterministic_results(self):
        """TC-12: Same inputs produce identical predictions."""
        provider = MockProvider(seed=42)
        r1 = provider.predict(["400001", "400017"], horizon_steps=1)
        r2 = provider.predict(["400001", "400017"], horizon_steps=1)
        assert r1[0].sensor_flows == r2[0].sensor_flows

    def test_different_seeds_differ(self):
        """Different seeds produce different flow values."""
        p1 = MockProvider(seed=1)
        p2 = MockProvider(seed=2)
        r1 = p1.predict(["400001"], horizon_steps=1)
        r2 = p2.predict(["400001"], horizon_steps=1)
        assert r1[0].sensor_flows["400001"] != r2[0].sensor_flows["400001"]

    def test_flow_range(self):
        """Generated flows should be within [200, 1200] veh/hr."""
        provider = MockProvider(seed=42)
        result = provider.predict(
            [str(400000 + i) for i in range(100)], horizon_steps=1
        )
        for flow in result[0].sensor_flows.values():
            assert 200.0 <= flow <= 1200.0

    def test_horizon_steps(self):
        """Multiple horizon steps return multiple PredictionResults."""
        provider = MockProvider(seed=42)
        results = provider.predict(["400001"], horizon_steps=5)
        assert len(results) == 5
        assert results[0].timestep_minutes == 5
        assert results[4].timestep_minutes == 25

    def test_is_available(self):
        """MockProvider is always available."""
        assert MockProvider().is_available() is True

    def test_model_name(self):
        """Model name should be 'mock'."""
        assert MockProvider().model_name == "mock"
