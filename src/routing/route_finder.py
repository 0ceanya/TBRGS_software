"""Route finding orchestrator.

Chains: prediction -> travel time conversion -> graph adapter -> search -> results.

Data flow:
    1. Load sensor graph from .npz
    2. Get flow predictions from the selected model provider
    3. For each edge: haversine -> distance, flow_to_speed -> speed -> travel_time
    4. Build Part A Graph via adapter with travel_time edge costs
    5. Run search algorithm (single path or Yen's KSP for top-k)
    6. Translate integer paths back to sensor IDs
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.core.graph_adapter import build_graph, get_all_edges, load_npz
from src.prediction.interface import PredictionProvider
from src.prediction.mock_provider import MockProvider
from src.routing.haversine import haversine_km
from src.routing.travel_time import compute_travel_time
from src.algorithms.registry import run_algorithm
from src.algorithms.yen_ksp import yen_k_shortest_paths


@dataclass(frozen=True)
class RouteResult:
    """A single route from origin to destination."""

    path_sensor_ids: List[str]
    total_travel_time_seconds: float
    total_distance_km: float
    num_sensors: int
    algorithm: str
    model: str


# Provider registry -- add new providers here when inference code is ready
def _get_provider(model_name: str) -> PredictionProvider:
    if model_name == "mock":
        return MockProvider()

    # Attempt real providers (will raise NotImplementedError if not integrated)
    if model_name == "gru":
        from src.prediction.gru_provider import GRUProvider
        return GRUProvider()
    if model_name == "dcrnn":
        from src.prediction.dcrnn_provider import DCRNNProvider
        return DCRNNProvider()
    if model_name == "lstm":
        from src.prediction.lstm_provider import LSTMProvider
        return LSTMProvider()

    raise ValueError(f"Unknown model: {model_name}")


def _compute_edge_travel_times(
    npz_data: dict,
    sensor_flows: Dict[str, float],
) -> Tuple[Dict[Tuple[str, str], float], Dict[Tuple[str, str], float]]:
    """Compute travel time and distance for every edge in the graph.

    Returns:
        edge_travel_times: (from, to) -> travel time in seconds
        edge_distances: (from, to) -> distance in km
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


def find_routes(
    npz_path: str | Path = "data/graph.npz",
    origin_sensor: str = "",
    dest_sensor: str = "",
    model_name: str = "mock",
    algorithm: str = "AS",
    k: int = 5,
    horizon_steps: int = 1,
) -> List[RouteResult]:
    """Find top-k routes from origin to destination.

    Args:
        npz_path: path to the sensor graph .npz file.
        origin_sensor: starting sensor ID string.
        dest_sensor: destination sensor ID string.
        model_name: prediction model ("mock", "gru", "dcrnn", "lstm").
        algorithm: search algorithm ("AS", "BFS", "DFS", "GBFS", "CUS1", "CUS2").
        k: number of routes to return (1-10).
        horizon_steps: prediction horizon in 5-minute steps.

    Returns:
        List of RouteResult, sorted by ascending travel time.
    """
    # 1. Load graph
    npz_data = load_npz(npz_path)
    sensor_ids = [str(s) for s in npz_data["sensor_ids"]]

    if origin_sensor not in sensor_ids:
        raise ValueError(f"Origin sensor '{origin_sensor}' not in graph")
    if dest_sensor not in sensor_ids:
        raise ValueError(f"Destination sensor '{dest_sensor}' not in graph")

    # 2. Get predictions
    provider = _get_provider(model_name)
    predictions = provider.predict(sensor_ids, horizon_steps=horizon_steps)
    sensor_flows = predictions[0].sensor_flows  # use first timestep

    # 3. Compute travel time for every edge
    edge_times, edge_dists = _compute_edge_travel_times(npz_data, sensor_flows)

    # 4. Build Part A Graph via adapter
    graph, id_to_sensor, sensor_to_id = build_graph(npz_data, edge_times)

    origin_int = sensor_to_id[origin_sensor]
    dest_int = sensor_to_id[dest_sensor]

    # 5. Find paths
    if k <= 1:
        path, _ = run_algorithm(algorithm, graph, origin_int, [dest_int])
        raw_paths = [(path, 0.0)] if path else []
    else:
        raw_paths = yen_k_shortest_paths(graph, origin_int, dest_int, k=k)

    # 6. Translate to RouteResults
    results: List[RouteResult] = []
    for int_path, _ in raw_paths:
        if not int_path:
            continue

        path_sids = [id_to_sensor[n] for n in int_path]

        # Recalculate totals from edge data
        total_time = 0.0
        total_dist = 0.0
        for i in range(len(path_sids) - 1):
            key = (path_sids[i], path_sids[i + 1])
            total_time += edge_times.get(key, 0.0)
            total_dist += edge_dists.get(key, 0.0)

        results.append(
            RouteResult(
                path_sensor_ids=path_sids,
                total_travel_time_seconds=total_time,
                total_distance_km=total_dist,
                num_sensors=len(path_sids),
                algorithm=algorithm,
                model=model_name,
            )
        )

    results.sort(key=lambda r: r.total_travel_time_seconds)
    return results
