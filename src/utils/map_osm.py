"""
Interactive OpenStreetMap visualisation of the PEMS-BAY sensor graph.
Uses Folium (Leaflet.js + OSM tiles) — output is a self-contained HTML file.

Speedups vs map.py:
  • All edges rendered as a single GeoJSON layer (no per-edge Python loop).
  • Vectorised numpy edge extraction before any Python iteration.
  • prefer_canvas=True — Canvas renderer instead of SVG (faster for >1 k markers).
  • macOS desktop notifications at every major step.

Usage (run from repo root, inside venv):
    python3 src/utils/map_osm.py
    python3 src/utils/map_osm.py --graph data/graph.npz --out map.html
    python3 src/utils/map_osm.py --path 402365 401129   # highlight shortest path
"""

import argparse
import json
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import numpy as np
from scipy import sparse


# ── macOS notification ────────────────────────────────────────────────────────

def notify(title: str, msg: str) -> None:
    """Send a macOS desktop notification (silent fail on other OS)."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{msg}" with title "{title}"'],
            check=False, timeout=3, capture_output=True,
        )
    except Exception:
        pass


# ── Graph loader ──────────────────────────────────────────────────────────────

def load_graph(path: str) -> dict:
    npz = np.load(path, allow_pickle=False)
    n = int(npz["n_nodes"])
    adj = sparse.csr_matrix(
        (npz["data"], (npz["row"], npz["col"])),
        shape=(n, n), dtype=np.float32,
    )
    sensor_ids = [
        s.decode() if isinstance(s, bytes) else str(s)
        for s in npz["sensor_ids"]
    ]
    return dict(sensor_ids=sensor_ids,
                lats=npz["lats"].astype(float),
                lons=npz["lons"].astype(float),
                adj=adj, n=n)


# ── Colour helpers ────────────────────────────────────────────────────────────

def _degree_colour(ratio: float) -> str:
    """Red (high degree) → green (low degree) hex colour."""
    r = int(200 * ratio + 55)
    g = int(200 * (1 - ratio) + 55)
    return f"#{r:02x}{g:02x}55"


# ── Map builder ───────────────────────────────────────────────────────────────

def build_map(g: dict, path_ids: list | None = None,
              edge_threshold: float = 0.05):
    try:
        import folium
        from folium.plugins import MiniMap
    except ImportError:
        sys.exit("folium not installed — run:  pip install folium  (or activate .venv)")

    lats, lons = g["lats"], g["lons"]
    sensor_ids = g["sensor_ids"]
    adj = g["adj"]
    valid = ~np.isnan(lats)

    clat = float(np.nanmean(lats[valid]))
    clon = float(np.nanmean(lons[valid]))

    m = folium.Map(
        location=[clat, clon],
        zoom_start=11,
        tiles="OpenStreetMap",
        prefer_canvas=True,          # Canvas renderer — faster for many markers
        control_scale=True,
    )
    MiniMap(toggle_display=True).add_to(m)

    # ── Edges: vectorised extraction → single GeoJSON layer ──────────────────
    t0 = time.time()
    adj_arr = adj.toarray()
    r_idx, c_idx = np.where((adj_arr > edge_threshold) & (np.arange(adj_arr.shape[0])[:, None] < np.arange(adj_arr.shape[1])))
    weights = adj_arr[r_idx, c_idx]

    # Filter out pairs where either endpoint has NaN coordinates
    mask = ~(np.isnan(lats[r_idx]) | np.isnan(lats[c_idx]))
    r_idx, c_idx, weights = r_idx[mask], c_idx[mask], weights[mask]

    # Build GeoJSON in one list comprehension — no per-edge folium objects
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [float(lons[r]), float(lats[r])],
                    [float(lons[c]), float(lats[c])],
                ],
            },
            "properties": {"w": round(float(w), 3)},
        }
        for r, c, w in zip(r_idx.tolist(), c_idx.tolist(), weights.tolist())
    ]

    folium.GeoJson(
        {"type": "FeatureCollection", "features": features},
        name="Sensor edges",
        style_function=lambda f: {
            "color": "#888888",
            "weight": 1.2,
            "opacity": min(0.9, f["properties"]["w"] * 0.9),
        },
        tooltip=folium.GeoJsonTooltip(["w"], aliases=["weight"]),
    ).add_to(m)

    elapsed = time.time() - t0
    print(f"  Edges layer : {len(features)} edges  ({elapsed:.2f}s)")
    notify("TBRGS Map", f"{len(features)} edges rendered in {elapsed:.1f}s")

    # ── Sensor markers as a single GeoJSON layer (fast serialisation) ─────────
    t0 = time.time()
    degree = np.array(adj.sum(axis=1)).flatten()
    max_deg = float(degree[valid].max()) if valid.any() else 1.0
    valid_idxs = np.where(valid)[0]

    sensor_features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(lons[i]), float(lats[i])],
            },
            "properties": {
                "sid": sensor_ids[i],
                "deg": round(float(degree[i]), 2),
                "color": _degree_colour(float(degree[i]) / max_deg),
            },
        }
        for i in valid_idxs.tolist()
    ]

    folium.GeoJson(
        {"type": "FeatureCollection", "features": sensor_features},
        name="Sensors",
        marker=folium.CircleMarker(radius=4, weight=0.5, color="#333333",
                                   fill=True, fill_opacity=0.85),
        style_function=lambda f: {
            "fillColor": f["properties"]["color"],
            "color": "#333333",
            "weight": 0.5,
            "fillOpacity": 0.85,
        },
        tooltip=folium.GeoJsonTooltip(
            ["sid", "deg"], aliases=["Sensor", "Degree"]
        ),
    ).add_to(m)

    print(f"  Sensor markers: {len(valid_idxs)}  ({time.time()-t0:.2f}s)")

    # ── Shortest-path overlay ─────────────────────────────────────────────────
    if path_ids:
        id_to_idx = {sid: i for i, sid in enumerate(sensor_ids)}
        path_coords = [
            [float(lats[id_to_idx[sid]]), float(lons[id_to_idx[sid]])]
            for sid in path_ids
            if sid in id_to_idx and not np.isnan(lats[id_to_idx[sid]])
        ]
        if path_coords:
            path_group = folium.FeatureGroup(name="Shortest path", show=True)
            folium.PolyLine(
                path_coords, color="#0055FF", weight=5, opacity=0.85,
                tooltip=f"Shortest path — {len(path_ids)} sensors",
            ).add_to(path_group)
            folium.Marker(
                path_coords[0],
                tooltip=f"START: {path_ids[0]}",
                icon=folium.Icon(color="green", icon="play", prefix="fa"),
            ).add_to(path_group)
            folium.Marker(
                path_coords[-1],
                tooltip=f"END: {path_ids[-1]}",
                icon=folium.Icon(color="red", icon="stop", prefix="fa"),
            ).add_to(path_group)
            path_group.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Interactive OSM map of the PEMS-BAY sensor graph"
    )
    ap.add_argument("--graph", default="data/road_graph.npz",
                    help="Path to graph .npz (falls back to data/graph.npz)")
    ap.add_argument("--out",   default="map.html",
                    help="Output HTML file (default: map.html)")
    ap.add_argument("--path",  nargs=2, metavar=("START", "END"),
                    help="Highlight shortest path between two sensor IDs")
    ap.add_argument("--threshold", type=float, default=0.05,
                    help="Min edge weight to display (default 0.05)")
    ap.add_argument("--no-open", action="store_true",
                    help="Do not auto-open the HTML in a browser")
    args = ap.parse_args()

    # Graph with fallback
    graph_path = args.graph
    if not Path(graph_path).exists():
        fallback = "data/graph.npz"
        if Path(fallback).exists():
            print(f"'{graph_path}' not found — using fallback '{fallback}'")
            notify("TBRGS Map", f"Using fallback: {fallback}")
            graph_path = fallback
        else:
            sys.exit(f"Graph not found: {graph_path}\n"
                     "Run: python3 scripts/build_road_graph.py")

    print(f"Loading {graph_path} ...", flush=True)
    t0 = time.time()
    g = load_graph(graph_path)
    print(f"  {g['n']} sensors  |  {g['adj'].nnz} edges  ({time.time()-t0:.2f}s)")
    notify("TBRGS Map", f"Loaded {g['n']} sensors, {g['adj'].nnz} edges")

    # Shortest path
    path_ids = None
    if args.path:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from src.utils.search_path import find_shortest_path
        try:
            path_ids = find_shortest_path(g, args.path[0], args.path[1])
            print(f"  Path: {len(path_ids)} sensors  ({args.path[0]} → {args.path[1]})")
            notify("TBRGS Map", f"Path: {len(path_ids)} sensors")
        except ValueError as e:
            print(f"  Warning: {e}", file=sys.stderr)
            notify("TBRGS Map — Warning", str(e))

    # Build
    print("Building map ...", flush=True)
    t1 = time.time()
    m = build_map(g, path_ids, edge_threshold=args.threshold)
    print(f"  Map built  ({time.time()-t1:.2f}s)", flush=True)

    # Save
    out = Path(args.out)
    m.save(str(out))
    abs_path = out.resolve()
    print(f"Saved → {abs_path}")
    notify("TBRGS Map — Done", f"Saved to {out.name}. Opening in browser…")

    if not args.no_open:
        webbrowser.open(abs_path.as_uri())


if __name__ == "__main__":
    main()
