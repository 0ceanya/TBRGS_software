"""Uninformed Depth-First Search (DFS) using an explicit stack.

Ported from Part A (cos30019-Assignment2A) as a standalone copy.
"""

from typing import List, Set, Tuple

from src.core.graph import Graph


def depth_first_search(
    graph: Graph, origin: int, destinations: List[int]
) -> Tuple[List[int], int]:
    """DFS: expand deepest unexplored node first.

    Returns (path, nodes_generated). path == [] if no goal is found.
    """
    stack: List[Tuple[int, List[int]]] = [(origin, [origin])]
    explored: Set[int] = set()
    nodes_generated: int = 1

    while stack:
        current_node, path = stack.pop()

        if current_node in destinations:
            return path, nodes_generated

        if current_node in explored:
            continue
        explored.add(current_node)

        # Push in reverse so smaller IDs are popped first
        for neighbor in reversed(sorted(graph.get_neighbors(current_node))):
            if neighbor not in explored:
                stack.append((neighbor, path + [neighbor]))
                nodes_generated += 1

    return [], nodes_generated
