"""Greedy Best-First Search (GBFS) using straight-line distance heuristic.

Ported from Part A (cos30019-Assignment2A) as a standalone copy.
"""

import heapq
import math
from typing import List, Set, Tuple

from src.core.graph import Graph


def _heuristic(
    node_coords: Tuple[int, int], dest_coords: List[Tuple[int, int]]
) -> float:
    """Straight-line distance to the nearest destination."""
    return min(
        math.sqrt((d[0] - node_coords[0]) ** 2 + (d[1] - node_coords[1]) ** 2)
        for d in dest_coords
    )


def greedy_best_first_search(
    graph: Graph, origin: int, destinations: List[int]
) -> Tuple[List[int], int]:
    """GBFS: expand node with lowest h(n) (estimated distance to goal).

    Returns (path, nodes_generated). path == [] if no goal is found.
    """
    start_coords = graph.get_coords(origin)
    dest_coords = graph.get_dest_coords(destinations)
    start_h = _heuristic(start_coords, dest_coords)

    # (h_score, node_id, counter, path)
    frontier: list = []
    explored: Set[int] = set()
    counter: int = 0
    nodes_generated: int = 0

    heapq.heappush(frontier, (start_h, origin, counter, [origin]))
    nodes_generated += 1

    while frontier:
        _, current_node, _, path = heapq.heappop(frontier)

        if current_node in destinations:
            return path, nodes_generated

        if current_node in explored:
            continue
        explored.add(current_node)

        for neighbor in sorted(graph.get_neighbors(current_node)):
            if neighbor not in explored:
                counter += 1
                h = _heuristic(graph.get_coords(neighbor), dest_coords)
                heapq.heappush(frontier, (h, neighbor, counter, path + [neighbor]))
                nodes_generated += 1

    return [], nodes_generated
