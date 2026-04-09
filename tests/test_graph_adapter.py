"""Tests for the graph adapter (TC-05, TC-06)."""

import pytest
from src.core.graph_adapter import load_npz, build_graph, get_all_edges, get_sensor_mapping


@pytest.fixture
def npz_data():
    return load_npz("data/graph.npz")


class TestGraphAdapter:
    """TC-05, TC-06: Graph adapter correctness."""

    def test_adapter_node_count(self, npz_data):
        """TC-05: Adapted graph should have 325 nodes."""
        edges = get_all_edges(npz_data)
        edge_times = {(s1, s2): 60.0 for s1, s2 in edges}
        graph, id_to_sensor, sensor_to_id = build_graph(npz_data, edge_times)

        assert len(graph.nodes) == 325
        assert len(id_to_sensor) == 325
        assert len(sensor_to_id) == 325

    def test_adapter_id_mapping_consistency(self, npz_data):
        """TC-06: id_to_sensor and sensor_to_id are inverses."""
        id_to_sensor, sensor_to_id = get_sensor_mapping(npz_data)

        for int_id, sensor_id in id_to_sensor.items():
            assert sensor_to_id[sensor_id] == int_id

        for sensor_id, int_id in sensor_to_id.items():
            assert id_to_sensor[int_id] == sensor_id

    def test_graph_has_edges(self, npz_data):
        """Adapted graph should have edges with travel time costs."""
        edges = get_all_edges(npz_data)
        assert len(edges) > 0

        edge_times = {(s1, s2): 90.0 for s1, s2 in edges}
        graph, _, _ = build_graph(npz_data, edge_times)

        total_edges = sum(len(v) for v in graph.edges.values())
        assert total_edges > 0

    def test_coordinates_are_scaled(self, npz_data):
        """Node coordinates should be scaled lat/lon (large integers)."""
        edges = get_all_edges(npz_data)
        edge_times = {(s1, s2): 60.0 for s1, s2 in edges}
        graph, _, _ = build_graph(npz_data, edge_times)

        # PEMS-BAY lats are ~37.x, scaled by 10000 -> ~370000
        for x, y in graph.nodes.values():
            assert 300000 < x < 400000  # scaled latitude
            assert -1300000 < y < -1200000  # scaled longitude (negative)
