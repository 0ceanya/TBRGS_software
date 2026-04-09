"""GRU prediction provider stub.

To integrate the real GRU model:
1. Ensure models/gru/best_model.pt exists (it should already).
2. Implement the GRUTrafficPredictor class (see models/gru/PROJECT_SUMMARY.md
   for the architecture: 2-layer GRU encoder-decoder, 128 hidden, input_size=3).
3. Fill in the predict() method below to:
   - Load the checkpoint with torch.load()
   - Prepare input tensor (batch, 12, 325, 3)
   - Run forward pass
   - Inverse-transform predictions back to veh/hr
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from src.prediction.interface import PredictionResult

MODEL_PATH = Path("models/gru/best_model.pt")


class GRUProvider:
    """GRU traffic flow prediction provider."""

    @property
    def model_name(self) -> str:
        return "gru"

    def predict(
        self,
        sensor_ids: List[str],
        horizon_steps: int = 1,
    ) -> List[PredictionResult]:
        raise NotImplementedError(
            "GRU inference not yet integrated. "
            "See models/gru/PROJECT_SUMMARY.md for implementation guide."
        )

    def is_available(self) -> bool:
        if not MODEL_PATH.exists():
            return False
        try:
            import torch  # noqa: F401
            return True
        except ImportError:
            return False
