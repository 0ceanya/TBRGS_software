"""Tests for GRUProvider."""
from __future__ import annotations
import numpy as np
import pytest


class MockPEMSClient:
    """Minimal PEMS client mock that returns synthetic sensor data."""

    def is_configured(self):
        return True

    def fetch_recent_readings(self, sensor_ids, steps=12):
        rng = np.random.default_rng(42)
        return {
            sid: np.column_stack([
                rng.uniform(200, 1500, steps),   # flow
                rng.uniform(20, 85, steps),       # speed
                np.linspace(0.3, 0.5, steps),    # time_of_day
            ]).astype(np.float32)
            for sid in sensor_ids
        }


class TestGRUModelLoad:
    """Test GRU model class definition and loading."""

    def test_model_output_shape(self):
        """GRUTrafficPredictor should output (N, 12, 1) for N sensors."""
        torch = pytest.importorskip("torch", reason="torch not installed")
        from src.prediction.gru_model import GRUTrafficPredictor

        model = GRUTrafficPredictor()
        x = torch.randn(5, 12, 3)
        with torch.no_grad():
            out = model(x)
        assert out.shape == (5, 12, 1)

    def test_model_loads_checkpoint(self):
        """GRU checkpoint loads without key errors."""
        torch = pytest.importorskip("torch", reason="torch not installed")
        from src.prediction.gru_model import GRUTrafficPredictor
        from pathlib import Path

        path = Path("models/gru/best_model.pt")
        if not path.exists():
            pytest.skip("GRU checkpoint not found")
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        model = GRUTrafficPredictor()
        model.load_state_dict(ckpt["model_state_dict"])


class TestGRUProvider:
    """Test GRUProvider behaviour."""

    def test_is_unavailable_without_pems(self):
        from src.prediction.gru_provider import GRUProvider

        p = GRUProvider(pems_client=None)
        assert p.is_available() is False

    def test_is_unavailable_with_unconfigured_pems(self):
        from src.prediction.gru_provider import GRUProvider
        from src.data.pems_client import PEMSClient

        p = GRUProvider(pems_client=PEMSClient(api_key=None))
        assert p.is_available() is False

    def test_model_name(self):
        from src.prediction.gru_provider import GRUProvider

        assert GRUProvider().model_name == "gru"

    def test_predict_returns_correct_structure(self):
        """predict() returns List[PredictionResult] with correct fields."""
        pytest.importorskip("torch", reason="torch not installed")
        from pathlib import Path

        if not Path("models/gru/best_model.pt").exists():
            pytest.skip("GRU checkpoint not found")
        from src.prediction.gru_provider import GRUProvider

        sensor_ids = ["400001", "400002", "400003"]
        p = GRUProvider(pems_client=MockPEMSClient())
        results = p.predict(sensor_ids, horizon_steps=3)
        assert len(results) == 3
        for i, r in enumerate(results):
            assert r.timestep_minutes == (i + 1) * 5
            assert r.model_name == "gru"
            assert set(r.sensor_flows.keys()) == set(sensor_ids)

    def test_predict_flows_in_valid_range(self):
        """Predicted flows should be clipped to [0, 1500] veh/hr."""
        pytest.importorskip("torch", reason="torch not installed")
        from pathlib import Path

        if not Path("models/gru/best_model.pt").exists():
            pytest.skip("GRU checkpoint not found")
        from src.prediction.gru_provider import GRUProvider

        sensor_ids = ["400001", "400002"]
        p = GRUProvider(pems_client=MockPEMSClient())
        results = p.predict(sensor_ids, horizon_steps=1)
        for flow in results[0].sensor_flows.values():
            assert 0.0 <= flow <= 1500.0, f"Flow out of range: {flow}"
