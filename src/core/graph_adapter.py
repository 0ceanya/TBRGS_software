"""Convert the PEMS-BAY .npz sensor graph into a Part A Graph object.

The adapter:
1. Loads the sparse adjacency from graph.npz
2. Maps string sensor IDs to sequential integer node IDs (0..N-1)
3. Uses (lat, lon) scaled to integers as (x, y) coordinates
4. Accepts pre-computed travel time edge costs

This is the key System Integration piece (Section VIII of the report).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy import sparse

from src.core.graph import Graph

# Scale lat/lon to integer-like values for Part A heuristics.
# 1 degree lat ~ 111 km -> 10000 units per degree gives ~11m resolution.
COORDINATE_SCALE: int = 10000


def load_npz(path: str | Path) -> dict:
    """Load graph.npz and return raw components.

    Returns dict with keys:
        sensor_ids: ndarray of string sensor IDs (N,)
        lats: ndarray of latitudes (N,)
        lons: ndarray of longitudes (N,)
        n_nodes: int
        adj: scipy sparse CSR matrix (N x N)
    """
    path = Path(path)
    data = np.load(path, allow_pickle=True)

    n = int(data["n_nodes"])
    row = data["row"].astype(int)
    col = data["col"].astype(int)
    weights = data["data"].astype(float)

    adj = sparse.csr_matrix((weights, (row, col)), shape=(n, n))

    return {
        "sensor_ids": data["sensor_ids"].astype(str),
        "lats": data["lats"].astype(float),
        "lons": data["lons"].astype(float),
        "n_nodes": n,
        "adj": adj,
    }


def get_sensor_mapping(
    npz_data: dict,
) -> Tuple[Dict[int, str], Dict[str, int]]:
    """Return bidirectional ID mappings without building the full graph.

    Returns:
        id_to_sensor: int_id -> sensor_id string
        sensor_to_id: sensor_id string -> int_id
    """
    sensor_ids = npz_data["sensor_ids"]
    id_to_sensor = {i: str(sid) for i, sid in enumerate(sensor_ids)}
    sensor_to_id = {sid: i for i, sid in id_to_sensor.items()}
    return id_to_sensor, sensor_to_id


def get_all_edges(npz_data: dict) -> List[Tuple[str, str]]:
    """Return all (sensor_from, sensor_to) edge pairs from adjacency.

    The adjacency is symmetrized (adj + adj.T) so both directions are
    included, matching how search_path.py treats the graph.
    """
    adj = npz_data["adj"]
    sensor_ids = npz_data["sensor_ids"]

    # Symmetrize
    sym = adj + adj.T
    sym = sym.tocoo()

    edges: List[Tuple[str, str]] = []
    for r, c in zip(sym.row, sym.col):
        if r != c:
            edges.append((str(sensor_ids[r]), str(sensor_ids[c])))
    return edges


def build_graph(
    npz_data: dict,
    edge_travel_times: Dict[Tuple[str, str], float],
) -> Tuple[Graph, Dict[int, str], Dict[str, int]]:
    """Build a Part A Graph from .npz data and predicted travel times.

    Args:
        npz_data: dict from load_npz().
        edge_travel_times: mapping (sensor_from, sensor_to) -> travel_time_seconds.
            Must have an entry for every edge in the symmetrized adjacency.

    Returns:
        graph: Part A Graph object with integer node IDs and travel-time costs.
        id_to_sensor: int_id -> sensor_id string.
        sensor_to_id: sensor_id string -> int_id.
    """
    sensor_ids = npz_data["sensor_ids"]
    lats = npz_data["lats"]
    lons = npz_data["lons"]

    id_to_sensor, sensor_to_id = get_sensor_mapping(npz_data)

    graph = Graph()

    # Add nodes with scaled coordinates
    for i, sid in enumerate(sensor_ids):
        x = int(lats[i] * COORDINATE_SCALE)
        y = int(lons[i] * COORDINATE_SCALE)
        graph.add_node(i, x, y)

    # Symmetrize adjacency and add edges with travel time costs
    adj = npz_data["adj"]
    sym = adj + adj.T
    sym = sym.tocoo()

    for r, c in zip(sym.row, sym.col):
        if r == c:
            continue
        s_from = str(sensor_ids[r])
        s_to = str(sensor_ids[c])
        key = (s_from, s_to)
        if key in edge_travel_times:
            cost = edge_travel_times[key]
            graph.add_edge(int(r), int(c), cost)

    return graph, id_to_sensor, sensor_to_id
