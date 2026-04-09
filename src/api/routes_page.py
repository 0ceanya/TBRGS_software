"""API endpoints for route finding."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from src.routing.route_finder import find_routes

router = APIRouter(prefix="/api/routes", tags=["routes"])


class RouteRequest(BaseModel):
    origin: str = ""
    destination: str = ""
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    model: str = "mock"
    algorithm: str = "AS"
    k: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def validate_endpoints(self) -> "RouteRequest":
        has_o_sensor = bool(self.origin and self.origin.strip())
        has_o_coords = self.origin_lat is not None and self.origin_lon is not None
        if self.origin_lat is not None or self.origin_lon is not None:
            if not has_o_coords:
                raise ValueError("origin_lat and origin_lon must be supplied together")
        if not has_o_sensor and not has_o_coords:
            raise ValueError(
                "Origin required: select a sensor or provide origin_lat and origin_lon"
            )

        has_d_sensor = bool(self.destination and self.destination.strip())
        has_d_coords = self.dest_lat is not None and self.dest_lon is not None
        if self.dest_lat is not None or self.dest_lon is not None:
            if not has_d_coords:
                raise ValueError("dest_lat and dest_lon must be supplied together")
        if not has_d_sensor and not has_d_coords:
            raise ValueError(
                "Destination required: select a sensor or provide dest_lat and dest_lon"
            )
        return self


@router.post("/find")
async def find(req: RouteRequest) -> dict:
    """Find top-k routes between origin and destination."""
    try:
        outcome = find_routes(
            origin_sensor=req.origin,
            dest_sensor=req.destination,
            origin_lat=req.origin_lat,
            origin_lon=req.origin_lon,
            dest_lat=req.dest_lat,
            dest_lon=req.dest_lon,
            model_name=req.model,
            algorithm=req.algorithm,
            k=req.k,
        )
    except NotImplementedError as e:
        return {"error": str(e), "routes": [], "endpoints": None}
    except ValueError as e:
        return {"error": str(e), "routes": [], "endpoints": None}

    routes = []
    for r in outcome.routes:
        routes.append({
            "path": r.path_sensor_ids,
            "travel_time_seconds": round(r.total_travel_time_seconds, 1),
            "travel_time_display": _format_time(r.total_travel_time_seconds),
            "distance_km": round(r.total_distance_km, 2),
            "num_sensors": r.num_sensors,
            "algorithm": r.algorithm,
            "model": r.model,
        })

    return {
        "routes": routes,
        "count": len(routes),
        "endpoints": {
            "origin": outcome.origin,
            "destination": outcome.destination,
        },
    }


def _format_time(seconds: float) -> str:
    """Format seconds as 'Xm Ys'."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
