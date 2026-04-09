"""Tests for DCRNNProvider."""
from __future__ import annotations
import numpy as np
import pytest


class MockPEMSClientDCRNN:
    """Returns data for any sensor ID including all 325."""

    def is_configured(self):
        return True

    def fetch_recent_readings(self, sensor_ids, steps=12):
        rng = np.random.default_rng(0)
        return {
            sid: np.column_stack([
                rng.uniform(200, 1500, steps),
                rng.uniform(20, 85, steps),
                np.linspace(0.3, 0.5, steps),
            ]).astype(np.float32)
            for sid in sensor_ids
        }


class TestDCRNNModelLoad:
    """Test DCRNN model class definition and loading."""

    def test_model_loads_checkpoint(self):
        """DCRNN checkpoint loads without key errors."""
        torch = pytest.importorskip("torch", reason="torch not installed")
        from src.prediction.dcrnn_model import DCRNNModel
        from pathlib import Path

        path = Path("models/dcrnn/dcrnn_best.pt")
        if not path.exists():
            pytest.skip("DCRNN checkpoint not found")
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        model = DCRNNModel(num_nodes=325, K=2)
        model.load_state_dict(ckpt["model_state_dict"])


class TestDCRNNProvider:
    """Test DCRNNProvider behaviour."""

    def test_is_unavailable_without_pems(self):
        from src.prediction.dcrnn_provider import DCRNNProvider

        p = DCRNNProvider(pems_client=None)
        assert p.is_available() is False

    def test_is_unavailable_with_unconfigured_pems(self):
        from src.prediction.dcrnn_provider import DCRNNProvider
        from src.data.pems_client import PEMSClient

        p = DCRNNProvider(pems_client=PEMSClient(api_key=None))
        assert p.is_available() is False

    def test_model_name(self):
        from src.prediction.dcrnn_provider import DCRNNProvider

        assert DCRNNProvider().model_name == "dcrnn"

    def test_predict_returns_correct_structure(self):
        """predict() returns List[PredictionResult] with correct fields.

        Note: DCRNNProvider.predict() always requests all 325 sensors
        internally; sensor_ids here is the requested subset.
        """
        pytest.importorskip("torch", reason="torch not installed")
        from pathlib import Path

        if not Path("models/dcrnn/dcrnn_best.pt").exists():
            pytest.skip("DCRNN checkpoint not found")
        if not Path("data/graph.npz").exists():
            pytest.skip("graph.npz not found")
        from src.prediction.dcrnn_provider import DCRNNProvider

        sensor_ids = ["400001", "400017"]
        p = DCRNNProvider(pems_client=MockPEMSClientDCRNN())
        results = p.predict(sensor_ids, horizon_steps=3)
        assert len(results) == 3
        for i, r in enumerate(results):
            assert r.timestep_minutes == (i + 1) * 5
            assert r.model_name == "dcrnn"
            assert set(r.sensor_flows.keys()) == set(sensor_ids)

    def test_predict_flows_in_valid_range(self):
        """Predicted flows should be clipped to [0, 1500] veh/hr."""
        pytest.importorskip("torch", reason="torch not installed")
        from pathlib import Path

        if not Path("models/dcrnn/dcrnn_best.pt").exists():
            pytest.skip("DCRNN checkpoint not found")
        if not Path("data/graph.npz").exists():
            pytest.skip("graph.npz not found")
        from src.prediction.dcrnn_provider import DCRNNProvider

        sensor_ids = ["400001", "400017"]
        p = DCRNNProvider(pems_client=MockPEMSClientDCRNN())
        results = p.predict(sensor_ids, horizon_steps=1)
        for flow in results[0].sensor_flows.values():
            assert 0.0 <= flow <= 1500.0, f"Flow out of range: {flow}"
