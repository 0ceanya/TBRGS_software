"""DCRNN prediction provider stub.

To integrate the real DCRNN model:
1. Ensure models/dcrnn/dcrnn_best.pt exists (it should already).
2. Implement the DCRNN model class (see models/dcrnn/dcrnn_architecture.png).
3. Fill in the predict() method below.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from src.prediction.interface import PredictionResult

MODEL_PATH = Path("models/dcrnn/dcrnn_best.pt")


class DCRNNProvider:
    """DCRNN traffic flow prediction provider."""

    @property
    def model_name(self) -> str:
        return "dcrnn"

    def predict(
        self,
        sensor_ids: List[str],
        horizon_steps: int = 1,
    ) -> List[PredictionResult]:
        raise NotImplementedError(
            "DCRNN inference not yet integrated. "
            "See models/dcrnn/dcrnn_architecture.png for architecture reference."
        )

    def is_available(self) -> bool:
        if not MODEL_PATH.exists():
            return False
        try:
            import torch  # noqa: F401
            return True
        except ImportError:
            return False
