"""Resolve route endpoints from coordinates or sensor IDs.

Handles snapping WGS84 coordinates to the nearest graph sensor and
validating explicit sensor ID references.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.routing.haversine import haversine_km


def snap_to_nearest_sensor(
    npz_data: dict, lat: float, lon: float
) -> Tuple[str, float, float]:
    """Return the sensor ID and position closest to the given WGS84 coordinates."""
    sensor_ids = [str(s) for s in npz_data["sensor_ids"]]
    lats = npz_data["lats"]
    lons = npz_data["lons"]
    best_sid: str = sensor_ids[0]
    best_la = float(lats[0])
    best_lo = float(lons[0])
    best_km = float("inf")
    for sid, la, lo in zip(sensor_ids, lats, lons):
        d = haversine_km(float(lat), float(lon), float(la), float(lo))
        if d < best_km:
            best_km = d
            best_sid = sid
            best_la = float(la)
            best_lo = float(lo)
    return best_sid, best_la, best_lo


def resolve_endpoint(
    npz_data: dict,
    sensor_ids: List[str],
    label: str,
    sensor_arg: str,
    lat: Optional[float],
    lon: Optional[float],
) -> Tuple[str, Dict[str, Any]]:
    """Pick graph node from explicit coordinates (snap) or sensor ID.

    Args:
        npz_data: loaded graph data from ``load_npz``.
        sensor_ids: list of all sensor ID strings in the graph.
        label: human-readable endpoint name for error messages (e.g. "Origin").
        sensor_arg: explicit sensor ID string, or empty/None.
        lat: optional WGS84 latitude for coordinate-based resolution.
        lon: optional WGS84 longitude for coordinate-based resolution.

    Returns:
        Tuple of (resolved_sensor_id, metadata_dict).

    Raises:
        ValueError: when inputs are invalid or insufficient.
    """
    has_coords = lat is not None and lon is not None
    has_sensor = bool(sensor_arg and sensor_arg.strip())

    if has_coords:
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValueError(f"{label}: latitude/longitude out of range")
        snapped, la, lo = snap_to_nearest_sensor(npz_data, lat, lon)
        return snapped, {
            "source": "coordinates",
            "sensor_id": snapped,
            "requested_lat": float(lat),
            "requested_lon": float(lon),
            "snapped_lat": la,
            "snapped_lon": lo,
        }
    elif has_sensor:
        sid = sensor_arg.strip()
        if sid not in sensor_ids:
            raise ValueError(f"{label} sensor '{sid}' not in graph")
        idx = sensor_ids.index(sid)
        return sid, {
            "source": "sensor",
            "sensor_id": sid,
            "lat": float(npz_data["lats"][idx]),
            "lon": float(npz_data["lons"][idx]),
        }
    else:
        raise ValueError(
            f"{label}: provide a sensor ID or both latitude and longitude"
        )
