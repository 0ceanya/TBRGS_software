"""API endpoints for graph/sensor information."""

from __future__ import annotations

from fastapi import APIRouter

from src.core.graph_adapter import load_npz
from src.algorithms.registry import get_available

router = APIRouter(prefix="/api/graph", tags=["graph"])

_npz_cache: dict | None = None


def _get_npz() -> dict:
    global _npz_cache
    if _npz_cache is None:
        _npz_cache = load_npz("data/graph.npz")
    return _npz_cache


@router.get("/sensors")
async def list_sensors() -> dict:
    """Return all sensor IDs with lat/lon coordinates."""
    npz = _get_npz()
    sensors = [
        {"id": str(sid), "lat": float(lat), "lon": float(lon)}
        for sid, lat, lon in zip(npz["sensor_ids"], npz["lats"], npz["lons"])
    ]
    return {"sensors": sensors, "count": len(sensors)}


@router.get("/info")
async def graph_info() -> dict:
    """Return graph summary metadata."""
    npz = _get_npz()
    return {
        "n_sensors": int(npz["n_nodes"]),
        "n_edges": npz["adj"].nnz,
        "bbox": {
            "lat_min": float(npz["lats"].min()),
            "lat_max": float(npz["lats"].max()),
            "lon_min": float(npz["lons"].min()),
            "lon_max": float(npz["lons"].max()),
        },
    }


@router.get("/algorithms")
async def list_algorithms() -> dict:
    """Return available search algorithm names."""
    return {"algorithms": get_available()}
