"""A* Search using f(n) = g(n) + h(n).

Ported from Part A (cos30019-Assignment2A) as a standalone copy.
h(n) = minimum travel time estimate to nearest destination (admissible).

Graph coordinates are (lat * 10000, lon * 10000).  Edge costs are travel
time in seconds, so the heuristic must also return seconds.  We convert
the coordinate distance to approximate km (equirectangular projection)
then divide by the speed limit with no intersection delays to guarantee
the estimate never exceeds the real cost.
"""

import heapq
import math
from typing import Dict, List, Tuple

from src.core.graph import Graph

# -- heuristic calibration constants --
_COORD_SCALE: float = 10000.0
_KM_PER_DEG_LAT: float = 111.0
# cos(37°) ≈ 0.799; using 0.8 keeps a small safety margin
_COS_LAT: float = 0.8
# Speed limit from the fundamental diagram (travel_time.py)
_MAX_SPEED_KMH: float = 60.0


def _min_travel_time_seconds(
    a: Tuple[int, int], b: Tuple[int, int]
) -> float:
    """Admissible lower-bound travel time between two scaled-coordinate points."""
    dlat_deg = (a[0] - b[0]) / _COORD_SCALE
    dlon_deg = (a[1] - b[1]) / _COORD_SCALE
    dlat_km = dlat_deg * _KM_PER_DEG_LAT
    dlon_km = dlon_deg * _KM_PER_DEG_LAT * _COS_LAT
    dist_km = math.sqrt(dlat_km ** 2 + dlon_km ** 2)
    return dist_km / _MAX_SPEED_KMH * 3600


def _heuristic(
    node_coords: Tuple[int, int], dest_coords: List[Tuple[int, int]]
) -> float:
    """Minimum travel time (seconds) to the nearest destination."""
    return min(
        _min_travel_time_seconds(node_coords, d)
        for d in dest_coords
    )


def a_star_search(
    graph: Graph, origin: int, destinations: List[int]
) -> Tuple[List[int], int]:
    """A*: expand node with lowest f(n) = g(n) + h(n).

    Returns (path, nodes_generated). path == [] if no goal is found.
    """
    # (f_score, node_id, counter, path, g_score)
    frontier: list = []
    best_g: Dict[int, float] = {}
    counter: int = 0
    nodes_generated: int = 0

    start_coords = graph.get_coords(origin)
    dest_coords = graph.get_dest_coords(destinations)

    start_g = 0.0
    start_h = _heuristic(start_coords, dest_coords)
    start_f = start_g + start_h

    heapq.heappush(frontier, (start_f, origin, counter, [origin], start_g))
    best_g[origin] = start_g
    nodes_generated += 1

    while frontier:
        _, current_node, _, path, current_g = heapq.heappop(frontier)

        if current_node in destinations:
            return path, nodes_generated

        if current_g > best_g.get(current_node, float("inf")):
            continue

        neighbors = graph.get_neighbors_with_costs(current_node)
        for neighbor, step_cost in sorted(neighbors, key=lambda x: x[0]):
            counter += 1
            neighbor_g = current_g + step_cost

            if neighbor_g < best_g.get(neighbor, float("inf")):
                best_g[neighbor] = neighbor_g
                neighbor_h = _heuristic(graph.get_coords(neighbor), dest_coords)
                neighbor_f = neighbor_g + neighbor_h
                heapq.heappush(
                    frontier,
                    (neighbor_f, neighbor, counter, path + [neighbor], neighbor_g),
                )
                nodes_generated += 1

    return [], nodes_generated
