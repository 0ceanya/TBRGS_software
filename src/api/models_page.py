"""API endpoints for model comparison."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.routing.route_finder import find_routes

router = APIRouter(prefix="/api/models", tags=["models"])


class CompareRequest(BaseModel):
    origin: str
    destination: str
    models: List[str] = ["mock"]
    algorithm: str = "AS"
    k: int = Field(default=5, ge=1, le=10)


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
    comparisons = {}

    for model_name in req.models:
        try:
            results = find_routes(
                origin_sensor=req.origin,
                dest_sensor=req.destination,
                model_name=model_name,
                algorithm=req.algorithm,
                k=req.k,
            )
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

    return {"comparisons": comparisons}
