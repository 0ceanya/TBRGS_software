"""Edge weight computation for the sensor graph.

Converts per-sensor flow predictions into per-edge travel times and distances
using the haversine distance and the fundamental-diagram speed model.
"""

from __future__ import annotations

from typing import Dict, Tuple

from src.core.graph_adapter import get_all_edges
from src.prediction.interface import PredictionProvider
from src.prediction.mock_provider import MockProvider
from src.routing.haversine import haversine_km
from src.routing.travel_time import compute_travel_time


def get_provider(
    model_name: str,
    pems_client=None,
    providers: dict | None = None,
) -> PredictionProvider:
    """Return the prediction provider for the given model name.

    When *providers* is supplied (from ``app.state.providers``), cached
    instances are returned so model weights stay in memory across requests.

    When a real provider is requested but cannot run (missing PEMS key,
    missing checkpoint, etc.) the function falls back to MockProvider
    automatically.

    Args:
        model_name: one of "mock", "gru", "dcrnn", "lstm".
        pems_client: optional PEMS data client for live sensor data.
        providers: optional pre-built provider registry from app lifespan.

    Raises:
        ValueError: if *model_name* is not recognised.
    """
    if providers is not None and model_name in providers:
        provider = providers[model_name]
        if provider.is_available():
            return provider
        return providers["mock"]

    # Fallback: construct fresh (for tests and CLI usage)
    if model_name == "mock":
        return MockProvider()

    if model_name == "gru":
        from src.prediction.gru_provider import GRUProvider

        provider = GRUProvider(pems_client=pems_client)
    elif model_name == "dcrnn":
        from src.prediction.dcrnn_provider import DCRNNProvider

        provider = DCRNNProvider(pems_client=pems_client)
    elif model_name == "lstm":
        from src.prediction.lstm_provider import LSTMProvider

        provider = LSTMProvider(pems_client=pems_client)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    # Fall back to mock when provider cannot run
    if not provider.is_available():
        return MockProvider()
    return provider


def compute_edge_travel_times(
    npz_data: dict,
    sensor_flows: Dict[str, float],
) -> Tuple[Dict[Tuple[str, str], float], Dict[Tuple[str, str], float]]:
    """Compute travel time and distance for every edge in the graph.

    Args:
        npz_data: loaded graph data from ``load_npz``.
        sensor_flows: mapping sensor_id -> predicted flow (veh/hr).

    Returns:
        edge_travel_times: (from, to) -> travel time in seconds.
        edge_distances: (from, to) -> distance in km.
    """
    sensor_ids = npz_data["sensor_ids"]
    lats = npz_data["lats"]
    lons = npz_data["lons"]

    # Build sensor -> index lookup
    sid_to_idx = {str(sid): i for i, sid in enumerate(sensor_ids)}

    edges = get_all_edges(npz_data)
    edge_times: Dict[Tuple[str, str], float] = {}
    edge_dists: Dict[Tuple[str, str], float] = {}

    for s_from, s_to in edges:
        i = sid_to_idx[s_from]
        j = sid_to_idx[s_to]

        dist_km = haversine_km(lats[i], lons[i], lats[j], lons[j])

        # Flow at the starting sensor determines speed on this link
        flow = sensor_flows.get(s_from, 600.0)

        travel_time = compute_travel_time(
            distance_km=dist_km, flow=flow, num_intersections=1
        )

        edge_times[(s_from, s_to)] = travel_time
        edge_dists[(s_from, s_to)] = dist_km

    return edge_times, edge_dists
