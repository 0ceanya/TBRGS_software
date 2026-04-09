"""Preset traffic scenarios for demos (PEMS-BAY style time-of-day labels).

These are UI presets only; they do not load the large ``test_cases/tc_*.json`` fixtures.
Sensor pairs align with common examples in ``test_cases/README.md`` where applicable.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

_SCENARIOS = [
    {
        "id": "custom",
        "label": "Custom",
        "description": "Keep the current start/end on the map.",
        "default_origin": "",
        "default_destination": "",
        "time_context": "",
    },
    {
        "id": "early_morning",
        "label": "Early morning — light traffic",
        "description": "Similar to tc_005 free-flow; suggested ~06:00.",
        "default_origin": "402365",
        "default_destination": "401129",
        "time_context": "06:00",
    },
    {
        "id": "morning_peak",
        "label": "Morning peak",
        "description": "Building congestion (tc_007 ~09:07).",
        "default_origin": "402365",
        "default_destination": "401129",
        "time_context": "09:07",
    },
    {
        "id": "midday",
        "label": "Midday — heavy bottlenecks",
        "description": "Network-wide stress (tc_003 ~13:54).",
        "default_origin": "402365",
        "default_destination": "401129",
        "time_context": "13:54",
    },
    {
        "id": "evening_clearing",
        "label": "Evening — easing congestion",
        "description": "Clearing trend (tc_004 ~17:32).",
        "default_origin": "402365",
        "default_destination": "401129",
        "time_context": "17:32",
    },
    {
        "id": "evening_mixed",
        "label": "Night — mixed conditions",
        "description": "Heterogeneous evening pattern (tc_008 ~19:41).",
        "default_origin": "402365",
        "default_destination": "401129",
        "time_context": "19:41",
    },
]


@router.get("")
async def list_scenarios() -> dict:
    """Return preset scenario metadata for the route UI."""
    return {
        "scenarios": _SCENARIOS,
        "count": len(_SCENARIOS),
        "note": "time_context is for display and demo only; forecasts are limited to 60 minutes (12×5 min steps).",
    }
