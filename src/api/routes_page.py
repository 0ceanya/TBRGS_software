"""API endpoints for route finding."""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator, model_validator

from src.api.dependencies import get_npz_data, get_pems_client, get_providers
from src.api.validation import validate_endpoints
from src.data.pems_client import PEMSClient
from src.routing.route_finder import RouteResult, find_routes

router = APIRouter(prefix="/api/routes", tags=["routes"])


class RouteRequest(BaseModel):
    origin: str = ""
    destination: str = ""
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    model: str = "lstm"
    algorithm: str = "AS"
    k: int = Field(default=2, ge=1, le=3)
    departure_time: Optional[str] = Field(
        default=None,
        description="Optional display-only departure clock time (e.g. 08:55).",
    )
    milestone_steps: List[int] = Field(
        default_factory=lambda: [1, 3, 6],
        description="Forecast steps (5 min each); max step 12 (60 minutes).",
    )

    @field_validator("milestone_steps", mode="before")
    @classmethod
    def _normalize_milestones(cls, v: Any) -> List[int]:
        if v is None:
            return [1, 3, 6]
        if not isinstance(v, list):
            raise ValueError("milestone_steps must be a list of integers")
        cleaned = sorted({int(x) for x in v if 1 <= int(x) <= 12})
        return cleaned if cleaned else [1]

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
            milestone_steps=req.milestone_steps,
            pems_client=pems,
            providers=providers,
        )
    except NotImplementedError as e:
        return {
            "error": str(e),
            "routes": [],
            "endpoints": None,
            "horizon_milestones": [],
            "departure_time": req.departure_time,
            "milestone_steps": req.milestone_steps,
        }
    except ValueError as e:
        return {
            "error": str(e),
            "routes": [],
            "endpoints": None,
            "horizon_milestones": [],
            "departure_time": req.departure_time,
            "milestone_steps": req.milestone_steps,
        }

    routes = [_serialize_route(r) for r in outcome.routes]

    horizon_payload = [
        {
            "step": m.step,
            "offset_minutes": m.offset_minutes,
            "label": m.label,
            "routes": [_serialize_route(r) for r in m.routes],
            "count": len(m.routes),
        }
        for m in outcome.horizon_milestones
    ]

    return {
        "routes": routes,
        "count": len(routes),
        "endpoints": {
            "origin": outcome.origin,
            "destination": outcome.destination,
        },
        "departure_time": req.departure_time,
        "milestone_steps": req.milestone_steps,
        "forecast_note": (
            "Each step is 5 minutes; the current model supports up to 12 steps (~60 minutes)."
        ),
        "horizon_milestones": horizon_payload,
    }


def _serialize_route(r: RouteResult) -> dict:
    return {
        "path": r.path_sensor_ids,
        "travel_time_seconds": round(r.total_travel_time_seconds, 1),
        "travel_time_display": _format_time(r.total_travel_time_seconds),
        "distance_km": round(r.total_distance_km, 2),
        "num_sensors": r.num_sensors,
        "algorithm": r.algorithm,
        "model": r.model,
    }


def _format_time(seconds: float) -> str:
    """Format seconds as 'Xm Ys'."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
