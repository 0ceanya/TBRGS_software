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
    """FastAPI test client with lifespan events."""
    from fastapi.testclient import TestClient
    from src.api.app import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_pems_client():
    """Unconfigured PEMS client (no API key)."""
    from src.data.pems_client import PEMSClient

    return PEMSClient(api_key=None)


@pytest.fixture
def configured_pems_client():
    """Mock PEMS client that appears configured but returns synthetic data."""
    from unittest.mock import MagicMock
    import numpy as np

    client = MagicMock()
    client.is_configured.return_value = True

    def fake_fetch(sensor_ids, steps=12):
        rng = np.random.default_rng(42)
        return {
            sid: np.column_stack([
                rng.uniform(200, 1500, steps),
                rng.uniform(20, 85, steps),
                np.linspace(0.3, 0.5, steps),
            ]).astype(np.float32)
            for sid in sensor_ids
        }

    client.fetch_recent_readings.side_effect = fake_fetch
    return client


@pytest.fixture
def live_pems_client():
    """Real PEMS client -- skips if PEMS_API_KEY not set in environment."""
    import os

    key = os.environ.get("PEMS_API_KEY")
    if not key:
        pytest.skip("PEMS_API_KEY not set -- skipping live PEMS test")
    from src.data.pems_client import PEMSClient

    return PEMSClient(api_key=key)
