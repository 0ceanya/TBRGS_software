"""Graph data structure for search algorithms.

Copied from Part A (cos30019-Assignment2A-Tree-based-Search/src/core/graph.py)
to keep Part B self-contained. Supports directed weighted graphs with
coordinate-based heuristics for informed search algorithms.
"""

from typing import Dict, List, Tuple


class Graph:
    def __init__(self) -> None:
        # Maps node_id -> (x, y)
        self.nodes: Dict[int, Tuple[int, int]] = {}

        # Maps node_id -> List of (neighbor_id, cost)
        self.edges: Dict[int, List[Tuple[int, float]]] = {}

        # Maps node_id -> List of (source_id, cost) for reverse/incoming edges
        self.reverse_edges: Dict[int, List[Tuple[int, float]]] = {}

        self.origin: int = -1
        self.destinations: List[int] = []

        # Exploration tracking for animation replay
        self.exploration_log: List[Tuple[int, str]] = []
        self._tracking: bool = False
        self._tracking_direction: str = "f"
        self._logged_nodes: set = set()

    def enable_tracking(self) -> None:
        """Enable exploration order tracking for animation."""
        self._tracking = True
        self.exploration_log = []
        self._logged_nodes = set()

    def disable_tracking(self) -> None:
        """Disable exploration tracking."""
        self._tracking = False

    def set_tracking_direction(self, direction: str) -> None:
        """Set current tracking direction: 'f' (forward) or 'b' (backward)."""
        self._tracking_direction = direction

    def _log_node(self, node_id: int) -> None:
        """Internal: log a node exploration if tracking is on."""
        if self._tracking and node_id not in self._logged_nodes:
            self.exploration_log.append((node_id, self._tracking_direction))
            self._logged_nodes.add(node_id)

    def add_node(self, node_id: int, x: int, y: int) -> None:
        self.nodes[node_id] = (x, y)
        if node_id not in self.edges:
            self.edges[node_id] = []

    def add_edge(self, from_node: int, to_node: int, cost: float) -> None:
        if from_node not in self.edges:
            self.edges[from_node] = []
        self.edges[from_node].append((to_node, cost))
        if to_node not in self.reverse_edges:
            self.reverse_edges[to_node] = []
        self.reverse_edges[to_node].append((from_node, cost))

    def get_neighbors(self, node_id: int) -> List[int]:
        self._log_node(node_id)
        return [neighbor for neighbor, cost in self.edges.get(node_id, [])]

    def get_coords(self, node_id: int) -> Tuple[int, int]:
        """Returns the (x, y) coordinates of a specific node."""
        return self.nodes.get(node_id, (0, 0))

    def get_dest_coords(self, destinations: List[int]) -> List[Tuple[int, int]]:
        """Returns a list of (x, y) coordinates for all destination nodes."""
        return [self.nodes[d] for d in destinations if d in self.nodes]

    def get_neighbors_with_costs(self, node_id: int) -> List[Tuple[int, float]]:
        """Returns a list of (neighbor_id, step_cost) to calculate g(n)."""
        self._log_node(node_id)
        return self.edges.get(node_id, [])

    def get_reverse_neighbors_with_costs(self, node_id: int) -> List[Tuple[int, float]]:
        """Returns a list of (source_id, step_cost) for incoming edges."""
        self._log_node(node_id)
        return self.reverse_edges.get(node_id, [])
