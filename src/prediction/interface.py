"""Prediction interface for traffic flow forecasting.

Defines the Protocol that all model providers must satisfy.
The system works with MockProvider by default; real providers plug in later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Protocol, runtime_checkable


@dataclass(frozen=True)
class PredictionResult:
    """Flow predictions for all sensors at a single future timestep."""

    sensor_flows: Dict[str, float]  # sensor_id -> predicted flow (veh/hr)
    timestep_minutes: int           # minutes into the future (5, 10, ..., 60)
    model_name: str                 # "gru", "dcrnn", "lstm", "mock"


@runtime_checkable
class PredictionProvider(Protocol):
    """Protocol for traffic flow prediction providers.

    Each model (GRU, DCRNN, LSTM) implements this interface.
    MockProvider is the default when no real model is available.
    """

    @property
    def model_name(self) -> str:
        """Short identifier for this model (e.g. 'gru', 'mock')."""
        ...

    def predict(
        self,
        sensor_ids: List[str],
        horizon_steps: int = 1,
    ) -> List[PredictionResult]:
        """Predict future traffic flow for the given sensors.

        Args:
            sensor_ids: list of sensor ID strings to predict for.
            horizon_steps: number of 5-minute steps to forecast (1..12).

        Returns:
            List of PredictionResult, one per timestep.
        """
        ...

    def is_available(self) -> bool:
        """Whether this provider can run predictions (model file + deps present)."""
        ...
