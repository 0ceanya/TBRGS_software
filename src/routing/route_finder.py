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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.algorithms.registry import run_algorithm
from src.algorithms.yen_ksp import yen_k_shortest_paths
from src.core.graph_adapter import build_graph, load_npz
from src.routing.edge_weights import compute_edge_travel_times, get_provider
from src.routing.endpoint_resolver import resolve_endpoint


@dataclass(frozen=True)
class RouteResult:
    """A single route from origin to destination."""

    path_sensor_ids: List[str]
    total_travel_time_seconds: float
    total_distance_km: float
    num_sensors: int
    algorithm: str
    model: str


@dataclass(frozen=True)
class RouteSearchOutcome:
    """Routes plus how origin/destination were resolved (sensor pick vs GPS snap)."""

    routes: List[RouteResult]
    origin: Dict[str, Any] = field(default_factory=dict)
    destination: Dict[str, Any] = field(default_factory=dict)


def find_routes(
    npz_path: str | Path = "data/graph.npz",
    origin_sensor: str = "",
    dest_sensor: str = "",
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
    model_name: str = "mock",
    algorithm: str = "AS",
    k: int = 5,
    horizon_steps: int = 1,
    npz_data: dict | None = None,
    pems_client=None,
    providers: dict | None = None,
) -> RouteSearchOutcome:
    """Find top-k routes from origin to destination.

    Each endpoint is defined either by ``origin_sensor`` / ``dest_sensor``
    or by latitude and longitude (snapped to the nearest graph sensor).

    Args:
        npz_path: path to the sensor graph .npz file.
        origin_sensor: starting sensor ID string (if not using coordinates).
        dest_sensor: destination sensor ID string (if not using coordinates).
        origin_lat, origin_lon: optional WGS84 start point (snapped to nearest sensor).
        dest_lat, dest_lon: optional WGS84 end point (snapped to nearest sensor).
        model_name: prediction model ("mock", "gru", "dcrnn", "lstm").
        algorithm: search algorithm ("AS", "BFS", "DFS", "GBFS", "CUS1", "CUS2").
        k: number of routes to return (1-10).
        horizon_steps: prediction horizon in 5-minute steps.
        npz_data: pre-loaded graph data; when *None*, loaded from *npz_path*.
        pems_client: optional PEMS data client for live sensor data.
        providers: optional pre-built provider registry from app lifespan.

    Returns:
        RouteSearchOutcome with routes sorted by ascending travel time and
        metadata describing how each endpoint was resolved.
    """
    # 1. Load graph
    if npz_data is None:
        npz_data = load_npz(npz_path)
    sensor_ids = [str(s) for s in npz_data["sensor_ids"]]

    origin_resolved, origin_detail = resolve_endpoint(
        npz_data, sensor_ids, "Origin", origin_sensor, origin_lat, origin_lon
    )
    dest_resolved, dest_detail = resolve_endpoint(
        npz_data, sensor_ids, "Destination", dest_sensor, dest_lat, dest_lon
    )

    # 2. Get predictions
    provider = get_provider(model_name, pems_client=pems_client, providers=providers)
    predictions = provider.predict(sensor_ids, horizon_steps=horizon_steps)
    sensor_flows = predictions[0].sensor_flows  # use first timestep

    # 3. Compute travel time for every edge
    edge_times, edge_dists = compute_edge_travel_times(npz_data, sensor_flows)

    # 4. Build Part A Graph via adapter
    graph, id_to_sensor, sensor_to_id = build_graph(npz_data, edge_times)

    origin_int = sensor_to_id[origin_resolved]
    dest_int = sensor_to_id[dest_resolved]

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
    return RouteSearchOutcome(
        routes=results,
        origin=origin_detail,
        destination=dest_detail,
    )
