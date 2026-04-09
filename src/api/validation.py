"""Shared request validation helpers for API endpoints."""

from __future__ import annotations

from typing import Optional


def validate_endpoints(
    origin: str,
    origin_lat: Optional[float],
    origin_lon: Optional[float],
    destination: str,
    dest_lat: Optional[float],
    dest_lon: Optional[float],
) -> None:
    """Validate that each endpoint has either a sensor ID or full lat/lon pair.

    Raises:
        ValueError: with a descriptive message on any invalid combination.
    """
    has_o_sensor = bool(origin and origin.strip())
    has_o_coords = origin_lat is not None and origin_lon is not None

    if origin_lat is not None or origin_lon is not None:
        if not has_o_coords:
            raise ValueError("origin_lat and origin_lon must be supplied together")
    if not has_o_sensor and not has_o_coords:
        raise ValueError(
            "Origin required: select a sensor or provide origin_lat and origin_lon"
        )

    has_d_sensor = bool(destination and destination.strip())
    has_d_coords = dest_lat is not None and dest_lon is not None

    if dest_lat is not None or dest_lon is not None:
        if not has_d_coords:
            raise ValueError("dest_lat and dest_lon must be supplied together")
    if not has_d_sensor and not has_d_coords:
        raise ValueError(
            "Destination required: select a sensor or provide dest_lat and dest_lon"
        )
