"""
Visualize the PEMS-BAY sensor graph on a geographic map.
Loads data/graph.npz (produced by export_graph.py) — no raw data files needed.

Usage:
    python3 python3 src/utils/map.py [--save]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from scipy import sparse


# ── Loader ────────────────────────────────────────────────────────────────────

def load_graph(path: str) -> dict:
    npz = np.load(path, allow_pickle=False)
    n = int(npz["n_nodes"])
    adj = sparse.csr_matrix(
        (npz["data"], (npz["row"], npz["col"])),
        shape=(n, n),
        dtype=np.float32,
    )
    return dict(
        sensor_ids=npz["sensor_ids"].tolist(),
        lats=npz["lats"],
        lons=npz["lons"],
        adj=adj,
        n=n,
    )


# ── Map panel ─────────────────────────────────────────────────────────────────

def plot_geo_map(ax, g: dict, edge_threshold: float = 0.05) -> None:
    lats, lons = g["lats"], g["lons"]
    sensor_ids = g["sensor_ids"]
    adj = g["adj"]

    degree = np.array(adj.sum(axis=1)).flatten()

    # Edges — upper-triangle only, above weight threshold
    adj_dense = adj.toarray()
    rows, cols = np.where((adj_dense > edge_threshold))
    upper = rows < cols
    rows, cols = rows[upper], cols[upper]
    weights = adj_dense[rows, cols]

    # Draw edges
    for r, c, w in zip(rows, cols, weights):
        if np.isnan(lats[r]) or np.isnan(lats[c]):
            continue
        ax.plot(
            [lons[r], lons[c]], [lats[r], lats[c]],
            color="#999999", alpha=float(w) * 0.55,
            linewidth=0.7, zorder=1, solid_capstyle="round",
        )

    # Draw nodes coloured by degree
    valid = ~np.isnan(lats)
    norm = mcolors.Normalize(vmin=float(degree[valid].min()),
                             vmax=float(degree[valid].max()))
    sc = ax.scatter(
        lons[valid], lats[valid],
        c=degree[valid], cmap="RdYlGn_r", norm=norm,
        s=22, zorder=3, edgecolors="#333333", linewidths=0.3,
    )
    plt.colorbar(sc, ax=ax, label="Degree (sum of edge weights)", shrink=0.85)

    # Annotate top-5 hubs
    top5 = np.argsort(degree)[-5:][::-1]
    for idx in top5:
        if not np.isnan(lats[idx]):
            ax.annotate(
                f"#{sensor_ids[idx]}\nd={degree[idx]:.1f}",
                xy=(lons[idx], lats[idx]),
                xytext=(lons[idx] + 0.02, lats[idx] + 0.012),
                fontsize=6.5, color="darkred", zorder=5,
                arrowprops=dict(arrowstyle="->", color="darkred", lw=0.8),
            )

    n_edges = len(rows)
    ax.set_title(
        f"PEMS-BAY Sensor Network — Bay Area Highway\n"
        f"{valid.sum()} sensors · {n_edges} edges (weight > {edge_threshold})\n"
        "Color = degree  ·  Red = highly connected  ·  Green = sparse",
        fontsize=9,
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_facecolor("#EEF2F7")
    ax.grid(True, alpha=0.25, linewidth=0.5)


# ── Degree histogram panel ────────────────────────────────────────────────────

def plot_degree_hist(ax, g: dict) -> None:
    adj = g["adj"]
    lats = g["lats"]
    degree = np.array(adj.sum(axis=1)).flatten()
    valid = ~np.isnan(lats)

    ax.hist(
        degree[valid], bins=30,
        color="steelblue", edgecolor="white", linewidth=0.5,
    )
    mean_deg = float(degree[valid].mean())
    ax.axvline(mean_deg, color="crimson", linestyle="--", linewidth=1.5,
               label=f"Mean = {mean_deg:.1f}")
    ax.set_title(
        "Degree Distribution\n(sum of outgoing edge weights per sensor)",
        fontsize=9,
    )
    ax.set_xlabel("Degree")
    ax.set_ylabel("# Sensors")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25, linewidth=0.5)

    # Print stats
    print(f"  Degree  min={float(degree[valid].min()):.2f} "
          f"mean={mean_deg:.2f} "
          f"max={float(degree[valid].max()):.2f}")
    print(f"  Isolated sensors (degree=0): {int((degree == 0).sum())}")


# ── Main ──────────────────────────────────────────────────────────────────────

def visualize(graph_path: str, save: bool = False) -> None:
    g = load_graph(graph_path)
    lats, lons = g["lats"], g["lons"]
    valid = ~np.isnan(lats)

    print(f"Sensors : {g['n']}  ({valid.sum()} with GPS)")
    print(f"Edges   : {g['adj'].nnz}  ({g['adj'].nnz / g['n']**2 * 100:.2f}% dense)")
    print(f"Lat     : {float(lats[valid].min()):.4f} – {float(lats[valid].max()):.4f}")
    print(f"Lon     : {float(lons[valid].min()):.4f} – {float(lons[valid].max()):.4f}")

    fig, axes = plt.subplots(1, 2, figsize=(16, 7),
                             gridspec_kw={"width_ratios": [2.5, 1]})
    fig.suptitle(
        "Bay Area Traffic Sensor Graph  ·  PEMS-BAY\n"
        "DCRNN diffuses traffic signals along these road edges during each GRU step",
        fontsize=11, fontweight="bold",
    )

    plot_geo_map(axes[0], g)
    plot_degree_hist(axes[1], g)

    plt.tight_layout()

    if save:
        out = Path(graph_path).with_suffix(".png")
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Saved → {out}")
    else:
        plt.show()


def main():
    ap = argparse.ArgumentParser(description="Visualize .npz sensor graph on a geo map")
    ap.add_argument("--graph", default="data/graph.npz", help="Path to graph.npz")
    ap.add_argument("--save",  action="store_true",      help="Save PNG instead of showing")
    args = ap.parse_args()

    if not Path(args.graph).exists():
        sys.exit(f"Graph file not found: {args.graph}\n"
                 "Run:  python3 scripts/export_graph.py  first.")

    visualize(args.graph, save=args.save)


if __name__ == "__main__":
    main()
