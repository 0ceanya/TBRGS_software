"""A* Search using f(n) = g(n) + h(n).

Ported from Part A (cos30019-Assignment2A) as a standalone copy.
h(n) = straight-line distance to nearest destination (admissible).
"""

import heapq
import math
from typing import Dict, List, Tuple

from src.core.graph import Graph


def _heuristic(
    node_coords: Tuple[int, int], dest_coords: List[Tuple[int, int]]
) -> float:
    """Straight-line distance to the nearest destination."""
    return min(
        math.sqrt((d[0] - node_coords[0]) ** 2 + (d[1] - node_coords[1]) ** 2)
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
