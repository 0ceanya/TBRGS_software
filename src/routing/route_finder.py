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
from typing import Any, Dict, List, Optional, Tuple

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


@dataclass(frozen=True)
class RouteSearchOutcome:
    """Routes plus how origin/destination were resolved (sensor pick vs GPS snap)."""

    routes: List[RouteResult]
    origin: Dict[str, Any] = field(default_factory=dict)
    destination: Dict[str, Any] = field(default_factory=dict)


def snap_to_nearest_sensor(npz_data: dict, lat: float, lon: float) -> Tuple[str, float, float]:
    """Return the sensor ID and position closest to the given WGS84 coordinates."""
    sensor_ids = [str(s) for s in npz_data["sensor_ids"]]
    lats = npz_data["lats"]
    lons = npz_data["lons"]
    best_sid: str = sensor_ids[0]
    best_la = float(lats[0])
    best_lo = float(lons[0])
    best_km = float("inf")
    for sid, la, lo in zip(sensor_ids, lats, lons):
        d = haversine_km(float(lat), float(lon), float(la), float(lo))
        if d < best_km:
            best_km = d
            best_sid = sid
            best_la = float(la)
            best_lo = float(lo)
    return best_sid, best_la, best_lo


def _resolve_route_endpoint(
    npz_data: dict,
    sensor_ids: List[str],
    label: str,
    sensor_arg: str,
    lat: Optional[float],
    lon: Optional[float],
) -> Tuple[str, Dict[str, Any]]:
    """Pick graph node from explicit coordinates (snap) or sensor ID."""
    has_coords = lat is not None and lon is not None
    has_sensor = bool(sensor_arg and sensor_arg.strip())

    if has_coords:
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValueError(f"{label}: latitude/longitude out of range")
        snapped, la, lo = snap_to_nearest_sensor(npz_data, lat, lon)
        detail: Dict[str, Any] = {
            "source": "coordinates",
            "sensor_id": snapped,
            "requested_lat": float(lat),
            "requested_lon": float(lon),
            "snapped_lat": la,
            "snapped_lon": lo,
        }
        return snapped, detail

    if not has_sensor:
        raise ValueError(
            f"{label}: provide a sensor ID or both latitude and longitude"
        )
    sid = sensor_arg.strip()
    if sid not in sensor_ids:
        raise ValueError(f"{label} sensor '{sid}' not in graph")
    idx = sensor_ids.index(sid)
    return sid, {
        "source": "sensor",
        "sensor_id": sid,
        "lat": float(npz_data["lats"][idx]),
        "lon": float(npz_data["lons"][idx]),
    }


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
    origin_lat: Optional[float] = None,
    origin_lon: Optional[float] = None,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
    model_name: str = "mock",
    algorithm: str = "AS",
    k: int = 5,
    horizon_steps: int = 1,
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

    Returns:
        RouteSearchOutcome with routes sorted by ascending travel time and
        metadata describing how each endpoint was resolved.
    """
    # 1. Load graph
    npz_data = load_npz(npz_path)
    sensor_ids = [str(s) for s in npz_data["sensor_ids"]]

    origin_resolved, origin_detail = _resolve_route_endpoint(
        npz_data, sensor_ids, "Origin", origin_sensor, origin_lat, origin_lon
    )
    dest_resolved, dest_detail = _resolve_route_endpoint(
        npz_data, sensor_ids, "Destination", dest_sensor, dest_lat, dest_lon
    )

    # 2. Get predictions
    provider = _get_provider(model_name)
    predictions = provider.predict(sensor_ids, horizon_steps=horizon_steps)
    sensor_flows = predictions[0].sensor_flows  # use first timestep

    # 3. Compute travel time for every edge
    edge_times, edge_dists = _compute_edge_travel_times(npz_data, sensor_flows)

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
