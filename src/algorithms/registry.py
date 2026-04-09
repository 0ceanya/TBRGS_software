"""Algorithm registry mapping names to search functions."""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from src.core.graph import Graph
from src.algorithms.bfs import breadth_first_search
from src.algorithms.dfs import depth_first_search
from src.algorithms.gbfs import greedy_best_first_search
from src.algorithms.astar import a_star_search
from src.algorithms.cus1 import adaptive_survivor_search
from src.algorithms.cus2 import bala_star

# Standard signature: (graph, origin, destinations) -> (path, nodes_generated)
SearchFn = Callable[[Graph, int, List[int]], Tuple[List[int], int]]

ALGORITHM_MAP: Dict[str, SearchFn] = {
    "BFS": breadth_first_search,
    "DFS": depth_first_search,
    "GBFS": greedy_best_first_search,
    "AS": a_star_search,
    "CUS2": bala_star,
}


def run_algorithm(
    name: str, graph: Graph, origin: int, destinations: List[int]
) -> Tuple[List[int], int]:
    """Run a named search algorithm.

    CUS1 has a different signature (uses graph.origin/destinations internally),
    so it's handled separately.
    """
    if name == "CUS1":
        graph.origin = origin
        graph.destinations = destinations
        return adaptive_survivor_search(graph)

    if name not in ALGORITHM_MAP:
        raise ValueError(f"Unknown algorithm '{name}'. Available: {get_available()}")

    return ALGORITHM_MAP[name](graph, origin, destinations)


def get_available() -> List[str]:
    """Return sorted list of available algorithm names."""
    return sorted(list(ALGORITHM_MAP.keys()) + ["CUS1"])
