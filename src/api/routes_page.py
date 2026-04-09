"""API endpoints for route finding."""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.routing.route_finder import find_routes

router = APIRouter(prefix="/api/routes", tags=["routes"])


class RouteRequest(BaseModel):
    origin: str
    destination: str
    model: str = "mock"
    algorithm: str = "AS"
    k: int = Field(default=5, ge=1, le=10)


@router.post("/find")
async def find(req: RouteRequest) -> dict:
    """Find top-k routes between origin and destination."""
    try:
        results = find_routes(
            origin_sensor=req.origin,
            dest_sensor=req.destination,
            model_name=req.model,
            algorithm=req.algorithm,
            k=req.k,
        )
    except NotImplementedError as e:
        return {"error": str(e), "routes": []}
    except ValueError as e:
        return {"error": str(e), "routes": []}

    routes = []
    for r in results:
        routes.append({
            "path": r.path_sensor_ids,
            "travel_time_seconds": round(r.total_travel_time_seconds, 1),
            "travel_time_display": _format_time(r.total_travel_time_seconds),
            "distance_km": round(r.total_distance_km, 2),
            "num_sensors": r.num_sensors,
            "algorithm": r.algorithm,
            "model": r.model,
        })

    return {"routes": routes, "count": len(routes)}


def _format_time(seconds: float) -> str:
    """Format seconds as 'Xm Ys'."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
