"""Tests for LSTMProvider."""
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


class TestLSTMModelLoad:
    """Test LSTM model class definition and loading."""

    def test_model_output_shape(self):
        """LSTM_Deep should output (N, 12, 1) for N sensors."""
        torch = pytest.importorskip("torch", reason="torch not installed")
        from src.prediction.lstm_model import LSTM_Deep

        model = LSTM_Deep()
        x = torch.randn(5, 12, 3)
        with torch.no_grad():
            out = model(x)
        assert out.shape == (5, 12, 1)

    def test_model_loads_checkpoint(self):
        """LSTM checkpoint loads without key errors."""
        torch = pytest.importorskip("torch", reason="torch not installed")
        from src.prediction.lstm_model import LSTM_Deep
        from pathlib import Path

        path = Path("models/lstm/Deep_Final_best.pt")
        if not path.exists():
            pytest.skip("LSTM checkpoint not found")
        state_dict = torch.load(path, map_location="cpu", weights_only=False)
        model = LSTM_Deep()
        model.load_state_dict(state_dict)


class TestLSTMProvider:
    """Test LSTMProvider behaviour."""

    def test_is_unavailable_without_pems(self):
        from src.prediction.lstm_provider import LSTMProvider

        p = LSTMProvider(pems_client=None)
        assert p.is_available() is False

    def test_is_unavailable_with_unconfigured_pems(self):
        from src.prediction.lstm_provider import LSTMProvider
        from src.data.pems_client import PEMSClient

        p = LSTMProvider(pems_client=PEMSClient(api_key=None))
        assert p.is_available() is False

    def test_model_name(self):
        from src.prediction.lstm_provider import LSTMProvider

        assert LSTMProvider().model_name == "lstm"

    def test_predict_returns_correct_structure(self):
        """predict() returns List[PredictionResult] with correct fields."""
        pytest.importorskip("torch", reason="torch not installed")
        from pathlib import Path

        if not Path("models/lstm/Deep_Final_best.pt").exists():
            pytest.skip("LSTM checkpoint not found")
        from src.prediction.lstm_provider import LSTMProvider

        sensor_ids = ["400001", "400002", "400003"]
        p = LSTMProvider(pems_client=MockPEMSClient())
        results = p.predict(sensor_ids, horizon_steps=3)
        assert len(results) == 3
        for i, r in enumerate(results):
            assert r.timestep_minutes == (i + 1) * 5
            assert r.model_name == "lstm"
            assert set(r.sensor_flows.keys()) == set(sensor_ids)

    def test_predict_flows_in_valid_range(self):
        """Predicted flows should be clipped to [0, 1500] veh/hr."""
        pytest.importorskip("torch", reason="torch not installed")
        from pathlib import Path

        if not Path("models/lstm/Deep_Final_best.pt").exists():
            pytest.skip("LSTM checkpoint not found")
        from src.prediction.lstm_provider import LSTMProvider

        sensor_ids = ["400001", "400002"]
        p = LSTMProvider(pems_client=MockPEMSClient())
        results = p.predict(sensor_ids, horizon_steps=1)
        for flow in results[0].sensor_flows.values():
            assert 0.0 <= flow <= 1500.0, f"Flow out of range: {flow}"
