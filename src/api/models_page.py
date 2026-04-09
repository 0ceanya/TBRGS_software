"""API endpoints for model comparison."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

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
    def validate_endpoints(self) -> "CompareRequest":
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


@router.get("/available")
async def available_models() -> dict:
    """Return which models are usable."""
    from src.prediction.mock_provider import MockProvider
    from src.prediction.gru_provider import GRUProvider
    from src.prediction.dcrnn_provider import DCRNNProvider
    from src.prediction.lstm_provider import LSTMProvider

    return {
        "models": [
            {"name": "mock", "available": MockProvider().is_available()},
            {"name": "gru", "available": GRUProvider().is_available()},
            {"name": "dcrnn", "available": DCRNNProvider().is_available()},
            {"name": "lstm", "available": LSTMProvider().is_available()},
        ]
    }


@router.post("/compare")
async def compare(req: CompareRequest) -> dict:
    """Run the same route query with multiple models and compare results."""
    comparisons: dict = {}
    endpoints_meta: dict | None = None

    for model_name in req.models:
        try:
            outcome = find_routes(
                origin_sensor=req.origin,
                dest_sensor=req.destination,
                origin_lat=req.origin_lat,
                origin_lon=req.origin_lon,
                dest_lat=req.dest_lat,
                dest_lon=req.dest_lon,
                model_name=model_name,
                algorithm=req.algorithm,
                k=req.k,
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
