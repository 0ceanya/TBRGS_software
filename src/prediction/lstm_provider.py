"""LSTM traffic flow prediction provider."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import List

import numpy as np

from src.prediction.interface import PredictionResult

MODEL_PATH = Path("models/lstm/Deep_Final_best.pt")

# Normalization constants (matches training -- see src/config.py)
FLOW_NORM_MEAN: float = 1088.8
FLOW_NORM_STD: float = 156.5


class LSTMProvider:
    """LSTM traffic flow prediction provider."""

    def __init__(self, pems_client=None) -> None:
        self._pems_client = pems_client
        self._model = None
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return "lstm"

    def is_available(self) -> bool:
        if self._pems_client is None or not self._pems_client.is_configured():
            return False
        if not MODEL_PATH.exists():
            return False
        try:
            import torch  # noqa: F401

            return True
        except ImportError:
            return False

    def _load_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:  # double-checked locking
                return self._model
            import torch

            from src.prediction.lstm_model import LSTM_Deep

            # weights_only=False is required because the checkpoint includes
            # non-tensor metadata (epoch count, optimizer state). These files are
            # locally-trained research checkpoints -- do not load untrusted
            # checkpoint files this way.
            state_dict = torch.load(
                MODEL_PATH, map_location="cpu", weights_only=False
            )
            model = LSTM_Deep()
            model.load_state_dict(state_dict)
            model.eval()
            self._model = model
        return self._model

    def predict(
        self,
        sensor_ids: List[str],
        horizon_steps: int = 1,
    ) -> List[PredictionResult]:
        import torch

        model = self._load_model()

        # Fetch live data for all sensors
        readings = self._pems_client.fetch_recent_readings(sensor_ids, steps=12)

        # Build input tensor (N, 12, 3)
        N = len(sensor_ids)
        x = np.zeros((N, 12, 3), dtype=np.float32)
        for i, sid in enumerate(sensor_ids):
            arr = readings[sid]  # (12, 3): [flow, speed, time_of_day]
            x[i, :, 0] = arr[:, 0] / 1500.0  # flow normalized [0,1]
            x[i, :, 1] = arr[:, 1] / 85.0  # speed normalized [0,1]
            x[i, :, 2] = arr[:, 2]  # time_of_day already [0,1]

        tensor = torch.from_numpy(x)  # (N, 12, 3)

        with torch.no_grad():
            raw = model(tensor)  # (N, 12, 1)

        # Inverse Z-score transform -> veh/hr
        flows_np = raw.squeeze(-1).numpy()  # (N, 12)
        flows_np = flows_np * FLOW_NORM_STD + FLOW_NORM_MEAN
        flows_np = np.clip(flows_np, 0.0, 1500.0)

        # Build PredictionResult list (one per timestep, up to horizon_steps)
        steps = min(horizon_steps, 12)
        results = []
        for t in range(steps):
            sensor_flows = {
                sid: float(flows_np[i, t]) for i, sid in enumerate(sensor_ids)
            }
            results.append(
                PredictionResult(
                    sensor_flows=sensor_flows,
                    timestep_minutes=(t + 1) * 5,
                    model_name=self.model_name,
                )
            )
        return results
