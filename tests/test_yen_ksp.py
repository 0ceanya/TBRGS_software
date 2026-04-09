"""Tests for Yen's K-Shortest Paths algorithm (TC-07, TC-08)."""

import pytest
from src.algorithms.yen_ksp import yen_k_shortest_paths


class TestYenKSP:
    """TC-07, TC-08: Yen's algorithm correctness."""

    def test_finds_multiple_paths(self, small_graph):
        """TC-07: Should find multiple distinct paths on a graph with alternatives."""
        results = yen_k_shortest_paths(small_graph, origin=0, destination=4, k=3)

        assert len(results) >= 2
        # All paths should be distinct
        paths = [tuple(p) for p, c in results]
        assert len(set(paths)) == len(paths)

    def test_paths_sorted_by_cost(self, small_graph):
        """TC-08: Returned paths should be in ascending cost order."""
        results = yen_k_shortest_paths(small_graph, origin=0, destination=4, k=5)

        costs = [c for _, c in results]
        assert costs == sorted(costs)

    def test_shortest_is_optimal(self, small_graph):
        """First path should be the shortest (0->2->3->4 = cost 15)."""
        results = yen_k_shortest_paths(small_graph, origin=0, destination=4, k=3)

        path, cost = results[0]
        assert path == [0, 2, 3, 4]
        assert cost == 15.0

    def test_no_path_returns_empty(self):
        """If no path exists, return empty list."""
        from src.core.graph import Graph

        g = Graph()
        g.add_node(0, 0, 0)
        g.add_node(1, 10, 0)
        # No edges between them

        results = yen_k_shortest_paths(g, origin=0, destination=1, k=3)
        assert results == []

    def test_single_path_graph(self):
        """Graph with only one path should return exactly 1 result."""
        from src.core.graph import Graph

        g = Graph()
        g.add_node(0, 0, 0)
        g.add_node(1, 10, 0)
        g.add_node(2, 20, 0)
        g.add_edge(0, 1, 5)
        g.add_edge(1, 2, 5)

        results = yen_k_shortest_paths(g, origin=0, destination=2, k=3)
        assert len(results) == 1
        assert results[0][0] == [0, 1, 2]
