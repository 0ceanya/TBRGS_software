"""PEMS live sensor data client.

Fetches recent 5-minute interval readings for a set of sensor IDs.

Two data modes:
- **Local mode** (default): derives synthetic but graph-aware flow values from a
  local ``graph.npz`` file.  No API key required.  Sensors with more connections
  receive higher base flows; values vary sinusoidally with time-of-day.
- **Live mode**: fetches real readings from the PEMS API when ``api_key`` is set.
  The HTTP call is currently stubbed — see the TODO comment inside
  ``fetch_recent_readings``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

__all__ = ["PEMSClient", "PEMSUnavailableError"]


class PEMSUnavailableError(Exception):
    """Raised when PEMS data is not accessible (no API key and no local graph)."""


class PEMSClient:
    def __init__(
        self,
        api_key: str | None,
        base_url: str = "https://pems.dot.ca.gov",
        npz_path: str | Path | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url
        # Per-sensor base flow derived from graph topology (local mode).
        self._local_flows: dict[str, float] | None = None
        if npz_path is not None:
            self._local_flows = self._build_local_flows(Path(npz_path))

    # ------------------------------------------------------------------
    # Local data helpers
    # ------------------------------------------------------------------

    def _build_local_flows(self, npz_path: Path) -> dict[str, float]:
        """Derive a base flow value per sensor from graph.npz adjacency.

        Uses node out-degree (number of outgoing connections) as a proxy
        for sensor busyness.  Sensors with more connections get higher
        synthetic base flows in [300, 1200] veh/hr.
        """
        from scipy import sparse

        data = np.load(npz_path, allow_pickle=True)
        sensor_ids = data["sensor_ids"].astype(str)
        n = int(data["n_nodes"])
        adj = sparse.csr_matrix(
            (
                data["data"].astype(float),
                (data["row"].astype(int), data["col"].astype(int)),
            ),
            shape=(n, n),
        )
        degrees = np.array(adj.getnnz(axis=1), dtype=float)
        max_deg = degrees.max() if degrees.max() > 0 else 1.0
        flows = 300.0 + (degrees / max_deg) * 900.0  # scale to [300, 1200]
        return {str(sid): float(f) for sid, f in zip(sensor_ids, flows)}

    def _generate_local_readings(
        self,
        sensor_ids: list[str],
        steps: int,
        time_of_day_values: list[float],
    ) -> dict[str, np.ndarray]:
        """Generate deterministic, graph-aware synthetic readings.

        Flow varies sinusoidally with time-of-day (±10% of base).
        Speed is derived as a simple inverse of flow.
        """
        tod = np.array(time_of_day_values, dtype=np.float32)
        result: dict[str, np.ndarray] = {}
        for sensor_id in sensor_ids:
            base_flow = (self._local_flows or {}).get(sensor_id, 700.0)
            # Sinusoidal time-of-day variation — peak congestion mid-day
            phase = tod * 2.0 * np.pi
            flow = base_flow * (1.0 + 0.1 * np.sin(phase + np.pi))
            flow = np.clip(flow, 200.0, 1500.0).astype(np.float32)
            # Speed inversely proportional to flow
            speed = np.clip(85.0 - (flow / 1500.0) * 65.0, 20.0, 85.0).astype(np.float32)
            result[sensor_id] = np.column_stack([flow, speed, tod])
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        """Return True when data is available via API key OR local graph file."""
        return self._api_key is not None or self._local_flows is not None

    def fetch_recent_readings(
        self,
        sensor_ids: list[str],
        steps: int = 12,
    ) -> dict[str, np.ndarray]:
        """Fetch recent sensor readings.

        Returns empty dict if sensor_ids is empty.

        Returns:
            dict mapping sensor_id -> numpy array of shape (steps, 3).
            Columns: [flow_veh_hr, speed_mph, time_of_day_0_to_1].
            Each row is one 5-minute interval, ordered oldest -> newest.

        Raises:
            PEMSUnavailableError: if neither API key nor local graph is available.
            ValueError: if steps is not a positive integer.
        """
        if not self.is_configured():
            raise PEMSUnavailableError(
                "No data source configured: set PEMS_API_KEY or supply npz_path"
            )

        if steps <= 0:
            raise ValueError("steps must be a positive integer")

        if not sensor_ids:
            return {}

        # Compute time_of_day values for each step (oldest first).
        # Step 0 is (steps-1) intervals ago, step (steps-1) is the most recent.
        now_utc = datetime.now(tz=timezone.utc)
        time_of_day_values: list[float] = []
        for offset in range(steps - 1, -1, -1):
            # Each step covers 5 minutes; shift back 'offset' steps from now.
            # Sub-minute precision is intentionally truncated; 5-minute interval data tolerates this.
            total_minutes = (now_utc.hour * 60 + now_utc.minute - offset * 5) % 1440
            time_of_day_values.append(total_minutes / 1440.0)

        # Local mode: no API key — use graph.npz-derived synthetic readings.
        if self._api_key is None:
            return self._generate_local_readings(sensor_ids, steps, time_of_day_values)

        # TODO: replace with real PEMS API call.
        #
        #   import httpx
        #   try:
        #       with httpx.Client() as client:
        #           resp = client.get(
        #               f"{self._base_url}/api/d2/stations/recent",
        #               headers={"Authorization": f"Bearer {self._api_key}"},
        #               params={"station_id": sensor_ids, "steps": steps},
        #               timeout=10.0,
        #           )
        #           resp.raise_for_status()
        #           payload = resp.json()
        #   except httpx.HTTPError as exc:
        #       raise PEMSUnavailableError(str(exc)) from exc

        # Placeholder until real API call is wired above.
        rng = np.random.default_rng()
        result: dict[str, np.ndarray] = {}
        for sensor_id in sensor_ids:
            flow = rng.uniform(200.0, 1500.0, size=steps).astype(np.float32)
            speed = rng.uniform(20.0, 85.0, size=steps).astype(np.float32)
            tod = np.array(time_of_day_values, dtype=np.float32)
            result[sensor_id] = np.column_stack([flow, speed, tod])
        return result
