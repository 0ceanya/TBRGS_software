"""API endpoints for graph/sensor information."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from src.algorithms.registry import get_available
from src.api.dependencies import get_npz_data

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/sensors")
async def list_sensors(npz: dict = Depends(get_npz_data)) -> dict:
    """Return all sensor IDs with lat/lon coordinates."""
    sensors = [
        {"id": str(sid), "lat": float(lat), "lon": float(lon)}
        for sid, lat, lon in zip(npz["sensor_ids"], npz["lats"], npz["lons"])
    ]
    return {"sensors": sensors, "count": len(sensors)}


@router.get("/info")
async def graph_info(npz: dict = Depends(get_npz_data)) -> dict:
    """Return graph summary metadata."""
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
