"""API endpoints for route finding."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, model_validator

from src.api.dependencies import get_npz_data, get_pems_client, get_providers
from src.api.validation import validate_endpoints
from src.data.pems_client import PEMSClient
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
    def _check_endpoints(self) -> "RouteRequest":
        validate_endpoints(
            self.origin,
            self.origin_lat,
            self.origin_lon,
            self.destination,
            self.dest_lat,
            self.dest_lon,
        )
        return self


@router.post("/find")
async def find(
    req: RouteRequest,
    npz: dict = Depends(get_npz_data),
    pems: PEMSClient = Depends(get_pems_client),
    providers: dict = Depends(get_providers),
) -> dict:
    """Find top-k routes between origin and destination."""
    try:
        outcome = find_routes(
            npz_data=npz,
            origin_sensor=req.origin,
            dest_sensor=req.destination,
            origin_lat=req.origin_lat,
            origin_lon=req.origin_lon,
            dest_lat=req.dest_lat,
            dest_lon=req.dest_lon,
            model_name=req.model,
            algorithm=req.algorithm,
            k=req.k,
            pems_client=pems,
            providers=providers,
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
