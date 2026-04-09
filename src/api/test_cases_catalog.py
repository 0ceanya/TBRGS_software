"""Catalog of ``test_cases/tc_*.json`` fixtures for the route UI.

Reads only the leading bytes of each file to extract ``sensor_id_start`` /
``sensor_id_end`` without loading multi-megabyte ``window`` payloads.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/test-cases", tags=["test-cases"])

# Mirrors test_cases/README.md matrix (scenario title + optional HH:MM for the time picker).
_PEMS_CASE_META: dict[str, dict[str, str | None]] = {
    "tc_001": {"title": "Edge case / reference routing", "time": None},
    "tc_002": {"title": "Bottleneck incident", "time": "10:00"},
    "tc_003": {"title": "Network congestion", "time": "13:54"},
    "tc_004": {"title": "Congestion clearing trend", "time": "17:32"},
    "tc_005": {"title": "Free flow baseline", "time": "06:00"},
    "tc_006": {"title": "Urban–highway mix", "time": "16:16"},
    "tc_007": {"title": "Congestion building", "time": "09:07"},
    "tc_008": {"title": "Evening mixed", "time": "19:41"},
    "tc_009": {"title": "Moderate change", "time": "10:48"},
    "tc_010": {"title": "Uniform network", "time": "13:12"},
}

_START_RE = re.compile(r'"sensor_id_start"\s*:\s*"([^"]+)"')
_END_RE = re.compile(r'"sensor_id_end"\s*:\s*"([^"]+)"')


def _peek_endpoints(path: Path) -> tuple[str, str]:
    """Read the start of a JSON file and extract endpoint sensor IDs."""
    raw = path.read_text(encoding="utf-8", errors="replace")[:24_576]
    m1 = _START_RE.search(raw)
    m2 = _END_RE.search(raw)
    if not m1 or not m2:
        return "", ""
    return m1.group(1), m2.group(1)


def _discover_cases(repo_root: Path) -> list[dict[str, str | None]]:
    out: list[dict[str, str | None]] = []
    tc_dir = repo_root / "test_cases"
    if not tc_dir.is_dir():
        return out
    for path in sorted(tc_dir.glob("tc_*.json")):
        case_id = path.stem
        meta = _PEMS_CASE_META.get(
            case_id,
            {"title": case_id, "time": None},
        )
        origin, dest = _peek_endpoints(path)
        if not origin or not dest:
            continue
        title = str(meta["title"])
        time_val = meta.get("time")
        out.append({
            "id": case_id,
            "file": path.name,
            "title": title,
            "label": f"{case_id} — {title}",
            "default_origin": origin,
            "default_destination": dest,
            "time_context": time_val,
            "note": "Endpoints come from the JSON file; full time series stays offline (not sent to the API).",
        })
    return out


@router.get("")
async def list_test_cases() -> dict:
    """List PEMS-BAY JSON test cases with routable origin/destination IDs."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    cases = _discover_cases(repo_root)
    return {
        "test_cases": cases,
        "count": len(cases),
    }