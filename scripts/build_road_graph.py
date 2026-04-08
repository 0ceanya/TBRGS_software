"""
Build a road-topology sensor graph using OpenStreetMap.

Speed optimisations:
  1. Download only motorway/trunk — PEMS sensors are on freeways.
  2. Tight bbox with no padding.
  3. Parallel Dijkstra with ProcessPoolExecutor (--workers flag).
  4. 2 km cutoff per source so each search stays local.
  5. OSMnx caches the download so re-runs are instant.
  6. macOS desktop notifications at each major step.

Output: data/road_graph.npz  (same format as data/graph.npz)
  sensor_ids, lats, lons, n_nodes, row, col, data

Usage (from repo root, inside .venv):
    python3 scripts/build_road_graph.py
    python3 scripts/build_road_graph.py --workers 8
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import networkx as nx


DIST_THRESHOLD_M = 2_000
SNAP_MAX_M       = 200
HIGHWAY_FILTER   = '["highway"~"motorway|motorway_link|trunk|trunk_link"]'


# ── macOS notification ────────────────────────────────────────────────────────

def notify(title: str, msg: str) -> None:
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{msg}" with title "{title}"'],
            check=False, timeout=3, capture_output=True,
        )
    except Exception:
        pass


# ── Sensor loader ─────────────────────────────────────────────────────────────

def load_sensors(path):
    npz = np.load(path, allow_pickle=False)
    ids = [s.decode() if isinstance(s, bytes) else str(s) for s in npz["sensor_ids"]]
    return ids, npz["lats"].astype(float), npz["lons"].astype(float)


# ── Worker (runs in subprocess) ───────────────────────────────────────────────

def _dijkstra_worker(args):
    """Top-level function so it is picklable for ProcessPoolExecutor."""
    sensor_idx, osm_source, G_osm, osm_to_sensors, dist_threshold = args
    reachable = nx.single_source_dijkstra_path_length(
        G_osm, osm_source, cutoff=dist_threshold, weight="length"
    )
    results = []
    for osm_j, dist_m in reachable.items():
        if dist_m == 0 or osm_j not in osm_to_sensors:
            continue
        for j in osm_to_sensors[osm_j]:
            if j == sensor_idx:
                continue
            results.append((sensor_idx, j, min(1.0, 1000.0 / dist_m)))
    return results


# ── Main build ────────────────────────────────────────────────────────────────

def build(src: str, out: str, workers: int = 4):
    try:
        import osmnx as ox
    except ImportError:
        sys.exit("osmnx not installed — run:  pip install osmnx")

    ox.settings.use_cache = True
    ox.settings.log_console = False
    ox.settings.timeout = 180
    ox.settings.overpass_url = "https://overpass.kumi.systems/api/interpreter"

    sensor_ids, lats, lons = load_sensors(src)
    n = len(sensor_ids)
    print(f"Sensors: {n}", flush=True)
    notify("TBRGS Build", f"Starting — {n} sensors")

    # ── 1. Download OSM motorway/trunk only ───────────────────────────────────
    north = float(lats.max()) + 0.005
    south = float(lats.min()) - 0.005
    east  = float(lons.max()) + 0.005
    west  = float(lons.min()) - 0.005
    print(f"Downloading OSM (motorway+trunk) bbox "
          f"({south:.3f},{west:.3f})→({north:.3f},{east:.3f}) ...", flush=True)
    t0 = time.time()
    G_osm = ox.graph_from_bbox(
        bbox=(north, south, east, west),
        custom_filter=HIGHWAY_FILTER,
        retain_all=False,
    )
    G_osm = ox.project_graph(G_osm)
    elapsed = time.time() - t0
    print(f"OSM graph: {G_osm.number_of_nodes()} nodes, "
          f"{G_osm.number_of_edges()} edges  ({elapsed:.1f}s)", flush=True)
    notify("TBRGS Build", f"OSM downloaded in {elapsed:.0f}s — {G_osm.number_of_nodes()} nodes")

    # ── 2. Snap sensors to nearest OSM node ───────────────────────────────────
    import pyproj
    transformer = pyproj.Transformer.from_crs(
        "EPSG:4326", G_osm.graph["crs"], always_xy=True
    )
    sensor_x, sensor_y = transformer.transform(lons, lats)

    print("Snapping sensors ...", flush=True)
    t0 = time.time()
    nn_osm, nn_dist = ox.nearest_nodes(G_osm, sensor_x, sensor_y, return_dist=True)

    sensor_osm = {
        i: nn_osm[i]
        for i in range(n)
        if nn_dist[i] <= SNAP_MAX_M
    }
    elapsed = time.time() - t0
    print(f"Snapped {len(sensor_osm)}/{n} sensors  ({elapsed:.1f}s)", flush=True)
    notify("TBRGS Build", f"Snapped {len(sensor_osm)}/{n} sensors")

    # ── 3. Parallel Dijkstra per sensor with cutoff ───────────────────────────
    osm_to_sensors: dict = {}
    for si, osm_node in sensor_osm.items():
        osm_to_sensors.setdefault(osm_node, []).append(si)

    snapped_list = sorted(sensor_osm.keys())
    total = len(snapped_list)
    print(f"Building edges (cutoff={DIST_THRESHOLD_M} m, workers={workers}) ...",
          flush=True)
    t0 = time.time()

    tasks = [
        (i, sensor_osm[i], G_osm, osm_to_sensors, DIST_THRESHOLD_M)
        for i in snapped_list
    ]

    rows, cols, weights = [], [], []

    # Use ThreadPoolExecutor — networkx/graph objects are not easily pickled,
    # so threads share the graph in-process (GIL-released during C-level work).
    from concurrent.futures import ThreadPoolExecutor, as_completed
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_dijkstra_worker, t): t[0] for t in tasks}
        for fut in as_completed(futures):
            done += 1
            for r, c, w in fut.result():
                rows.append(r)
                cols.append(c)
                weights.append(w)
            if done % 50 == 0 or done == total:
                elapsed_so_far = time.time() - t0
                print(f"  {done}/{total}  edges so far: {len(rows)}"
                      f"  ({elapsed_so_far:.1f}s)", flush=True)
                if done % 100 == 0:
                    notify("TBRGS Build",
                           f"Dijkstra {done}/{total} — {len(rows)} edges so far")

    elapsed = time.time() - t0
    print(f"Edges: {len(rows)}  ({elapsed:.1f}s)", flush=True)
    notify("TBRGS Build", f"Dijkstra done — {len(rows)} edges in {elapsed:.0f}s")

    # ── 4. Save ───────────────────────────────────────────────────────────────
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out,
        sensor_ids=np.array(sensor_ids),
        lats=lats.astype(np.float32),
        lons=lons.astype(np.float32),
        n_nodes=np.int64(n),
        row=np.array(rows,    dtype=np.int32),
        col=np.array(cols,    dtype=np.int32),
        data=np.array(weights, dtype=np.float32),
    )
    print(f"Saved → {out}", flush=True)
    notify("TBRGS Build — Done", f"road_graph.npz saved ({len(rows)} edges)")


def main():
    ap = argparse.ArgumentParser(description="Build OSM road-topology sensor graph")
    ap.add_argument("--src",     default="data/graph.npz",      help="Source graph (IDs + GPS)")
    ap.add_argument("--out",     default="data/road_graph.npz", help="Output path")
    ap.add_argument("--workers", type=int, default=4,
                    help="Parallel threads for Dijkstra (default 4)")
    args = ap.parse_args()

    if not Path(args.src).exists():
        sys.exit(f"Source not found: {args.src}")

    build(args.src, args.out, workers=args.workers)


if __name__ == "__main__":
    main()
