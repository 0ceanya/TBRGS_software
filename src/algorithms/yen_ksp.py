"""Yen's K-Shortest Paths algorithm.

Finds the top-k shortest loopless paths in a weighted directed graph.
Uses A* as the single-source shortest path subroutine.

Reference: Yen, J.Y. (1971) "Finding the K Shortest Loopless Paths in a Network"
"""

from __future__ import annotations

import copy
import heapq
from typing import List, Tuple

from src.core.graph import Graph
from src.algorithms.astar import a_star_search


def _path_cost(graph: Graph, path: List[int]) -> float:
    """Sum edge costs along a path."""
    total = 0.0
    for i in range(len(path) - 1):
        for neighbor, cost in graph.edges.get(path[i], []):
            if neighbor == path[i + 1]:
                total += cost
                break
    return total


def _remove_edge(graph: Graph, u: int, v: int) -> None:
    """Remove a single directed edge u->v from the graph (in place)."""
    graph.edges[u] = [(n, c) for n, c in graph.edges.get(u, []) if n != v]
    graph.reverse_edges[v] = [
        (n, c) for n, c in graph.reverse_edges.get(v, []) if n != u
    ]


def _remove_node(graph: Graph, node: int) -> None:
    """Remove a node from the graph by clearing its edges (in place)."""
    graph.edges[node] = []
    graph.reverse_edges[node] = []
    # Remove edges pointing to this node
    for src in list(graph.edges.keys()):
        graph.edges[src] = [(n, c) for n, c in graph.edges[src] if n != node]
    for src in list(graph.reverse_edges.keys()):
        graph.reverse_edges[src] = [
            (n, c) for n, c in graph.reverse_edges[src] if n != node
        ]


def yen_k_shortest_paths(
    graph: Graph,
    origin: int,
    destination: int,
    k: int = 5,
) -> List[Tuple[List[int], float]]:
    """Find k shortest loopless paths from origin to destination.

    Args:
        graph: Part A Graph object with travel-time edge costs.
        origin: start node (integer ID).
        destination: end node (integer ID).
        k: number of paths to find (default 5).

    Returns:
        List of (path, total_cost) tuples, sorted by ascending cost.
        May return fewer than k paths if fewer exist.
    """
    # Step 1: find the shortest path
    path_1, _ = a_star_search(graph, origin, [destination])
    if not path_1:
        return []

    cost_1 = _path_cost(graph, path_1)
    confirmed: List[Tuple[List[int], float]] = [(path_1, cost_1)]

    # Min-heap of candidates: (cost, path_tuple)
    candidates: List[Tuple[float, Tuple[int, ...]]] = []
    seen_paths: set = {tuple(path_1)}

    for i in range(1, k):
        prev_path = confirmed[i - 1][0]

        for j in range(len(prev_path) - 1):
            spur_node = prev_path[j]
            root_path = prev_path[: j + 1]
            root_cost = _path_cost(graph, root_path) if j > 0 else 0.0

            # Deep copy the graph so we can modify it
            g_copy = Graph()
            g_copy.nodes = dict(graph.nodes)
            g_copy.edges = {n: list(e) for n, e in graph.edges.items()}
            g_copy.reverse_edges = {n: list(e) for n, e in graph.reverse_edges.items()}

            # Remove edges used by confirmed paths that share this root
            for confirmed_path, _ in confirmed:
                if confirmed_path[: j + 1] == root_path and j + 1 < len(confirmed_path):
                    _remove_edge(g_copy, confirmed_path[j], confirmed_path[j + 1])

            # Remove root path nodes (except spur) to prevent loops
            for node in root_path[:-1]:
                _remove_node(g_copy, node)

            # Find spur path
            spur_path, _ = a_star_search(g_copy, spur_node, [destination])

            if spur_path:
                total_path = root_path[:-1] + spur_path
                path_tuple = tuple(total_path)

                if path_tuple not in seen_paths:
                    total_cost = root_cost + _path_cost(g_copy, spur_path)
                    heapq.heappush(candidates, (total_cost, path_tuple))
                    seen_paths.add(path_tuple)

        if not candidates:
            break

        best_cost, best_tuple = heapq.heappop(candidates)
        confirmed.append((list(best_tuple), best_cost))

    return confirmed
