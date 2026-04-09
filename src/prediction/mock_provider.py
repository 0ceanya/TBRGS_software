"""Mock prediction provider that generates realistic-looking flow data.

Generates flow values in [200, 1200] veh/hr using a deterministic hash so
results are reproducible across runs. The distribution loosely mimics typical
Bay Area highway traffic.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List

from src.prediction.interface import PredictionResult

FLOW_MIN: float = 200.0
FLOW_MAX: float = 1200.0


class MockProvider:
    """Deterministic mock prediction provider."""

    def __init__(self, seed: int = 42, base_flow: float = 700.0) -> None:
        self._seed = seed
        self._base_flow = base_flow

    @property
    def model_name(self) -> str:
        return "mock"

    def predict(
        self,
        sensor_ids: List[str],
        horizon_steps: int = 1,
    ) -> List[PredictionResult]:
        results: List[PredictionResult] = []
        for step in range(1, horizon_steps + 1):
            flows: Dict[str, float] = {}
            for sid in sensor_ids:
                flows[sid] = self._hash_flow(sid, step)
            results.append(
                PredictionResult(
                    sensor_flows=flows,
                    timestep_minutes=step * 5,
                    model_name=self.model_name,
                )
            )
        return results

    def is_available(self) -> bool:
        return True

    def _hash_flow(self, sensor_id: str, step: int) -> float:
        """Deterministic flow from sensor ID and step via SHA-256."""
        key = f"{self._seed}:{sensor_id}:{step}"
        digest = hashlib.sha256(key.encode()).hexdigest()
        # Use first 8 hex chars -> 32-bit int -> normalized to [0, 1]
        normalized = int(digest[:8], 16) / 0xFFFFFFFF
        return FLOW_MIN + normalized * (FLOW_MAX - FLOW_MIN)
