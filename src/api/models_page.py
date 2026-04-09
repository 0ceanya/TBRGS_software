"""API endpoints for model comparison."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from src.api.dependencies import get_npz_data, get_pems_client, get_providers
from src.api.validation import validate_endpoints
from src.data.pems_client import PEMSClient
from src.routing.route_finder import find_routes

router = APIRouter(prefix="/api/models", tags=["models"])


class CompareRequest(BaseModel):
    origin: str = ""
    destination: str = ""
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    models: List[str] = ["mock"]
    algorithm: str = "AS"
    k: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def _check_endpoints(self) -> "CompareRequest":
        validate_endpoints(
            self.origin,
            self.origin_lat,
            self.origin_lon,
            self.destination,
            self.dest_lat,
            self.dest_lon,
        )
        return self


@router.get("/available")
async def available_models(providers: dict = Depends(get_providers)) -> dict:
    """Return which models are usable."""
    return {
        "models": [
            {"name": name, "available": p.is_available()}
            for name, p in providers.items()
        ]
    }


@router.post("/compare")
async def compare(
    req: CompareRequest,
    npz: dict = Depends(get_npz_data),
    pems: PEMSClient = Depends(get_pems_client),
    providers: dict = Depends(get_providers),
) -> dict:
    """Run the same route query with multiple models and compare results."""
    comparisons: dict = {}
    endpoints_meta: dict | None = None

    for model_name in req.models:
        try:
            outcome = find_routes(
                npz_data=npz,
                origin_sensor=req.origin,
                dest_sensor=req.destination,
                origin_lat=req.origin_lat,
                origin_lon=req.origin_lon,
                dest_lat=req.dest_lat,
                dest_lon=req.dest_lon,
                model_name=model_name,
                algorithm=req.algorithm,
                k=req.k,
                pems_client=pems,
                providers=providers,
            )
            if endpoints_meta is None:
                endpoints_meta = {
                    "origin": outcome.origin,
                    "destination": outcome.destination,
                }
            results = outcome.routes
            comparisons[model_name] = {
                "routes": [
                    {
                        "path": r.path_sensor_ids,
                        "travel_time_seconds": round(r.total_travel_time_seconds, 1),
                        "distance_km": round(r.total_distance_km, 2),
                        "num_sensors": r.num_sensors,
                    }
                    for r in results
                ],
                "best_time": round(results[0].total_travel_time_seconds, 1)
                if results
                else None,
                "error": None,
            }
        except (NotImplementedError, ValueError) as e:
            comparisons[model_name] = {
                "routes": [],
                "best_time": None,
                "error": str(e),
            }

    return {"comparisons": comparisons, "endpoints": endpoints_meta}
