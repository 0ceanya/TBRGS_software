"""Uninformed Breadth-First Search (BFS) using a FIFO queue.

Ported from Part A (cos30019-Assignment2A) as a standalone copy.
"""

from collections import deque
from typing import List, Set, Tuple

from src.core.graph import Graph


def breadth_first_search(
    graph: Graph, origin: int, destinations: List[int]
) -> Tuple[List[int], int]:
    """BFS: expand nodes level by level.

    Returns (path, nodes_generated). path == [] if no goal is found.
    """
    queue = deque([(origin, [origin])])
    explored: Set[int] = set()
    nodes_generated: int = 1

    while queue:
        current_node, path = queue.popleft()

        if current_node in destinations:
            return path, nodes_generated

        if current_node in explored:
            continue
        explored.add(current_node)

        for neighbor in sorted(graph.get_neighbors(current_node)):
            if neighbor not in explored:
                queue.append((neighbor, path + [neighbor]))
                nodes_generated += 1

    return [], nodes_generated
