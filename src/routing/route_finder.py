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
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.algorithms.registry import run_algorithm
from src.algorithms.yen_ksp import yen_k_shortest_paths
from src.core.graph_adapter import build_graph, load_npz
from src.routing.edge_weights import compute_edge_travel_times, get_provider
from src.routing.endpoint_resolver import resolve_endpoint


def _collapse_consecutive_duplicates(path_sids: List[str]) -> List[str]:
    """Drop back-to-back repeats so path length matches traversed graph edges."""
    out: List[str] = []
    for sid in path_sids:
        if not out or out[-1] != sid:
            out.append(sid)
    return out


def _edge_set(path: List[str]) -> frozenset:
    """Set of directed (from, to) edges in a sensor-ID path."""
    return frozenset((path[i], path[i + 1]) for i in range(len(path) - 1))


def _filter_diverse_routes(
    results: List["RouteResult"],
    max_overlap: float = 0.75,
) -> List["RouteResult"]:
    """Keep only routes whose edges overlap ≤ *max_overlap* with every kept route.

    Overlap is measured as |shared edges| / |edges in shorter path|, so a
    route that reuses 80 % of a previously accepted route's edges is dropped
    even if the new route has extra segments.
    """
    if len(results) <= 1:
        return results

    kept: List["RouteResult"] = [results[0]]
    for candidate in results[1:]:
        cand_edges = _edge_set(candidate.path_sensor_ids)
        if not cand_edges:
            continue
        too_similar = False
        for accepted in kept:
            acc_edges = _edge_set(accepted.path_sensor_ids)
            if not acc_edges:
                continue
            shared = len(cand_edges & acc_edges)
            denom = min(len(cand_edges), len(acc_edges))
            if denom > 0 and shared / denom > max_overlap:
                too_similar = True
                break
        if not too_similar:
            kept.append(candidate)
    return kept


@dataclass(frozen=True)
class RouteResult:
    """A single route from origin to destination.

    ``num_sensors`` is len(path_sensor_ids) after collapsing consecutive
    duplicate IDs; it includes origin and destination graph stations.
    """

    path_sensor_ids: List[str]
    total_travel_time_seconds: float
    total_distance_km: float
    num_sensors: int
    algorithm: str
    model: str


@dataclass(frozen=True)
class HorizonMilestoneResult:
    """Routes computed using predicted flows at a single forecast timestep (5 min per step)."""

    step: int
    offset_minutes: int
    label: str
    routes: List[RouteResult]


@dataclass(frozen=True)
class RouteSearchOutcome:
    """Routes plus how origin/destination were resolved (sensor pick vs GPS snap)."""

    routes: List[RouteResult]
    origin: Dict[str, Any] = field(default_factory=dict)
    destination: Dict[str, Any] = field(default_factory=dict)
    horizon_milestones: List[HorizonMilestoneResult] = field(default_factory=list)


def _routes_for_sensor_flows(
    npz_data: dict,
    origin_resolved: str,
    dest_resolved: str,
    sensor_flows: Dict[str, float],
    algorithm: str,
    k: int,
    model_name: str,
) -> List[RouteResult]:
    """Run graph search for one set of per-sensor flow predictions."""
    edge_times, edge_dists = compute_edge_travel_times(npz_data, sensor_flows)
    graph, id_to_sensor, sensor_to_id = build_graph(npz_data, edge_times)

    origin_int = sensor_to_id[origin_resolved]
    dest_int = sensor_to_id[dest_resolved]

    if k <= 1:
        path, _ = run_algorithm(algorithm, graph, origin_int, [dest_int])
        raw_paths: List[Tuple[List[int], float]] = [(path, 0.0)] if path else []
    else:
        # Request extra candidates so the diversity filter can still
        # return k meaningfully different routes.
        raw_paths = yen_k_shortest_paths(graph, origin_int, dest_int, k=k * 3)

    results: List[RouteResult] = []
    for int_path, _ in raw_paths:
        if not int_path:
            continue

        path_sids = _collapse_consecutive_duplicates([id_to_sensor[n] for n in int_path])

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
    # Drop alternatives that visually overlap with already-accepted routes
    if k > 1:
        results = _filter_diverse_routes(results)
    return results[:k]


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
    k: int = 2,
    horizon_steps: int = 1,
    milestone_steps: Sequence[int] | None = None,
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
        k: number of routes to return (1-3).
        horizon_steps: unused if milestone_steps is set; otherwise prediction steps (default 1).
        milestone_steps: forecast timesteps (each step = 5 minutes, max 12 = 60 min).
            Example: (1, 3, 6) → now/+5 min, +15 min, +30 min traffic. When omitted, only step 1.
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

    # 2. Forecast horizon: one predict() call up to the furthest milestone (cap 12 steps = 60 min)
    provider = get_provider(model_name, pems_client=pems_client, providers=providers)
    if milestone_steps is None:
        steps_to_run = [1]
    else:
        steps_to_run = sorted({int(s) for s in milestone_steps if 1 <= int(s) <= 12})
        if not steps_to_run:
            steps_to_run = [1]
    predict_horizon = max(steps_to_run)
    if milestone_steps is None:
        predict_horizon = max(1, min(12, int(horizon_steps)))

    predictions = provider.predict(sensor_ids, horizon_steps=predict_horizon)

    horizon_results: List[HorizonMilestoneResult] = []
    for step in steps_to_run:
        idx = step - 1
        if idx >= len(predictions):
            continue
        sensor_flows = predictions[idx].sensor_flows
        offset = step * 5
        label = f"+{offset} min"
        step_routes = _routes_for_sensor_flows(
            npz_data,
            origin_resolved,
            dest_resolved,
            sensor_flows,
            algorithm,
            k,
            model_name,
        )
        horizon_results.append(
            HorizonMilestoneResult(
                step=step,
                offset_minutes=offset,
                label=label,
                routes=step_routes,
            )
        )

    baseline_routes = horizon_results[0].routes if horizon_results else []
    return RouteSearchOutcome(
        routes=baseline_routes,
        origin=origin_detail,
        destination=dest_detail,
        horizon_milestones=horizon_results,
    )
