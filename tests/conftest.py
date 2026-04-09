"""Shared pytest fixtures for TBRGS tests."""

import pytest


@pytest.fixture
def small_graph():
    """A 5-node directed graph with multiple paths for testing.

    Layout (coordinates kept small so Euclidean heuristic is admissible):
        0 --10--> 1 --10--> 4
        |                    ^
        5--> 2 ---5---> 3 --5-|
        |                    ^
        +-------20-----------+

    Paths from 0 to 4:
        0->2->3->4      cost=15 (shortest)
        0->1->4          cost=20
        0->3->4          cost=25
    """
    from src.core.graph import Graph

    g = Graph()
    g.add_node(0, 0, 0)
    g.add_node(1, 1, 0)
    g.add_node(2, 0, 1)
    g.add_node(3, 1, 1)
    g.add_node(4, 2, 0)

    g.add_edge(0, 1, 10)
    g.add_edge(1, 4, 10)
    g.add_edge(0, 2, 5)
    g.add_edge(2, 3, 5)
    g.add_edge(3, 4, 5)
    g.add_edge(0, 3, 20)

    g.origin = 0
    g.destinations = [4]
    return g


@pytest.fixture
def npz_data():
    """Load the real PEMS-BAY graph.npz."""
    from src.core.graph_adapter import load_npz

    return load_npz("data/graph.npz")


@pytest.fixture
def mock_provider():
    """A deterministic mock prediction provider."""
    from src.prediction.mock_provider import MockProvider

    return MockProvider(seed=42)


@pytest.fixture
def client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    app = create_app()
    return TestClient(app)
