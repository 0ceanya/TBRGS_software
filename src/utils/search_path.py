"""
Dijkstra shortest path over the PEMS-BAY sensor graph.

The adjacency matrix stores proximity weights in (0, 1]:
  higher weight  →  sensors are closer  →  lower travel cost
Edge cost is therefore 1 / weight so that nearby sensors are preferred.

Usage (library):
    from src.utils.map import load_graph
    from src.utils.search_path import find_shortest_path

    g = load_graph("data/graph.npz")
    path = find_shortest_path(g, "402365", "401129")
    # ["402365", "401816", ..., "401129"]

Usage (CLI — run from repo root):
    python3 src/utils/search_path.py 402365 401129
    python3 src/utils/search_path.py 402365 401129 --graph data/graph.npz
"""

import argparse
import heapq
import sys
from pathlib import Path


def find_shortest_path(graph: dict, start_id: str, end_id: str) -> list:
    """Return the shortest path (list of sensor ID strings) from start_id to end_id.

    Args:
        graph:    dict returned by load_graph() — keys: sensor_ids, adj, n, lats, lons
        start_id: sensor ID string of the start node
        end_id:   sensor ID string of the end node

    Returns:
        Ordered list of sensor ID strings from start to end (inclusive).

    Raises:
        ValueError: if either sensor ID is not in the graph or no path exists.
    """
    sensor_ids = [
        s.decode() if isinstance(s, bytes) else str(s)
        for s in graph["sensor_ids"]
    ]
    id_to_idx = {sid: i for i, sid in enumerate(sensor_ids)}

    if start_id not in id_to_idx:
        raise ValueError(f"start_id '{start_id}' not found in graph")
    if end_id not in id_to_idx:
        raise ValueError(f"end_id '{end_id}' not found in graph")

    src = id_to_idx[start_id]
    dst = id_to_idx[end_id]

    if src == dst:
        return [start_id]

    # Symmetrise so both directions of each road edge are usable
    adj = graph["adj"]
    adj = adj + adj.T
    n = graph["n"]

    dist = [float("inf")] * n
    prev = [-1] * n
    dist[src] = 0.0

    # min-heap: (cost, node_index)
    heap = [(0.0, src)]

    while heap:
        cost, u = heapq.heappop(heap)

        if cost > dist[u]:
            continue

        if u == dst:
            break

        # iterate over neighbours of u
        row_start = adj.indptr[u]
        row_end = adj.indptr[u + 1]
        for ptr in range(row_start, row_end):
            v = adj.indices[ptr]
            w = float(adj.data[ptr])
            if w <= 0:
                continue
            edge_cost = 1.0 / w          # higher weight → lower cost
            new_cost = dist[u] + edge_cost
            if new_cost < dist[v]:
                dist[v] = new_cost
                prev[v] = u
                heapq.heappush(heap, (new_cost, v))

    if dist[dst] == float("inf"):
        raise ValueError(f"No path found between '{start_id}' and '{end_id}'")

    # Reconstruct path
    path_idx = []
    cur = dst
    while cur != -1:
        path_idx.append(cur)
        cur = prev[cur]
    path_idx.reverse()

    return [sensor_ids[i] for i in path_idx]


def main():
    ap = argparse.ArgumentParser(description="Dijkstra shortest path between two sensors")
    ap.add_argument("start", help="Start sensor ID ")
    ap.add_argument("end",   help="End sensor ID ")
    ap.add_argument("--graph", default="data/graph.npz", help="Path to graph.npz (default: data/graph.npz)")
    args = ap.parse_args()

    graph_path = Path(args.graph)
    if not graph_path.exists():
        sys.exit(f"Graph file not found: {graph_path}")

    # Import here so the module is usable without src.utils.map when called as a library
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.utils.map import load_graph

    g = load_graph(str(graph_path))

    try:
        path = find_shortest_path(g, args.start, args.end)
    except ValueError as e:
        sys.exit(str(e))

    print(f"Shortest path ({len(path)} nodes):")
    for i, sid in enumerate(path):
        prefix = "  START →" if i == 0 else ("  END   :" if i == len(path) - 1 else f"  [{i}]    ")
        print(f"{prefix} {sid}")


if __name__ == "__main__":
    main()
