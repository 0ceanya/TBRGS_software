"""LSTM prediction provider stub.

To integrate the LSTM model:
1. Drop the trained model file into models/lstm/best_model.pt
2. Implement the LSTM model class matching the training architecture.
3. Fill in the predict() method below.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from src.prediction.interface import PredictionResult

MODEL_PATH = Path("models/lstm/best_model.pt")


class LSTMProvider:
    """LSTM traffic flow prediction provider."""

    @property
    def model_name(self) -> str:
        return "lstm"

    def predict(
        self,
        sensor_ids: List[str],
        horizon_steps: int = 1,
    ) -> List[PredictionResult]:
        raise NotImplementedError(
            "LSTM inference not yet integrated. "
            "Drop best_model.pt into models/lstm/ and implement this method."
        )

    def is_available(self) -> bool:
        if not MODEL_PATH.exists():
            return False
        try:
            import torch  # noqa: F401
            return True
        except ImportError:
            return False
