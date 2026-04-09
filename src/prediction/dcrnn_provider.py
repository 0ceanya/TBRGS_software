"""DCRNN traffic flow prediction provider."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import List

import numpy as np

from src.prediction.interface import PredictionResult

MODEL_PATH = Path("models/dcrnn/dcrnn_best.pt")
GRAPH_PATH = Path("data/graph.npz")

# Normalization constants (matches training -- see src/config.py)
FLOW_NORM_MEAN: float = 1088.8
FLOW_NORM_STD: float = 156.5


class DCRNNProvider:
    """DCRNN traffic flow prediction provider."""

    def __init__(self, pems_client=None) -> None:
        self._pems_client = pems_client
        self._model = None
        self._diff_matrices = None
        self._all_sensor_ids: list[str] | None = None
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return "dcrnn"

    def is_available(self) -> bool:
        if self._pems_client is None or not self._pems_client.is_configured():
            return False
        if not MODEL_PATH.exists() or not GRAPH_PATH.exists():
            return False
        try:
            import torch  # noqa: F401

            return True
        except ImportError:
            return False

    def _load_model_and_graph(self):
        if self._model is not None:
            return self._model, self._diff_matrices, self._all_sensor_ids
        with self._lock:
            if self._model is not None:  # double-checked locking
                return self._model, self._diff_matrices, self._all_sensor_ids
            import torch

            from src.core.graph_adapter import load_npz
            from src.prediction.dcrnn_model import (
                DCRNNModel,
                compute_diffusion_matrices,
            )

            # Load graph and compute diffusion matrices
            npz = load_npz(GRAPH_PATH)
            adj_dense = npz["adj"].toarray()
            diff_np = compute_diffusion_matrices(adj_dense, K=2)
            self._diff_matrices = [
                torch.tensor(A, dtype=torch.float32) for A in diff_np
            ]
            self._all_sensor_ids = [str(s) for s in npz["sensor_ids"]]

            # weights_only=False is required because the checkpoint includes
            # non-tensor metadata (epoch count, optimizer state). These files are
            # locally-trained research checkpoints -- do not load untrusted
            # checkpoint files this way.
            ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
            model = DCRNNModel(num_nodes=325, K=2)
            model.load_state_dict(ckpt["model_state_dict"])
            model.eval()
            self._model = model
        return self._model, self._diff_matrices, self._all_sensor_ids

    def predict(
        self,
        sensor_ids: List[str],
        horizon_steps: int = 1,
    ) -> List[PredictionResult]:
        import torch

        model, diff_matrices, all_ids = self._load_model_and_graph()

        # DCRNN operates on the full graph (325 nodes) because the diffusion
        # matrices are (325, 325). Fetch readings for every sensor, run
        # inference over all of them, then select the requested subset.
        readings = self._pems_client.fetch_recent_readings(all_ids, steps=12)

        x = np.zeros((325, 12, 3), dtype=np.float32)
        for i, sid in enumerate(all_ids):
            arr = readings[sid]
            x[i, :, 0] = arr[:, 0] / 1500.0
            x[i, :, 1] = arr[:, 1] / 85.0
            x[i, :, 2] = arr[:, 2]

        tensor = torch.from_numpy(x)  # (325, 12, 3)

        with torch.no_grad():
            raw = model(tensor, diff_matrices, horizon=12)  # (325, 12, 1)

        flows_all = raw.squeeze(-1).numpy()  # (325, 12)
        flows_all = flows_all * FLOW_NORM_STD + FLOW_NORM_MEAN
        flows_all = np.clip(flows_all, 0.0, 1500.0)

        # Select only the requested sensors by index
        sid_to_idx = {sid: i for i, sid in enumerate(all_ids)}

        steps = min(horizon_steps, 12)
        results = []
        for t in range(steps):
            sensor_flows = {
                sid: float(flows_all[sid_to_idx[sid], t])
                for sid in sensor_ids
            }
            results.append(
                PredictionResult(
                    sensor_flows=sensor_flows,
                    timestep_minutes=(t + 1) * 5,
                    model_name=self.model_name,
                )
            )
        return results
