"""Traffic flow to travel time conversion.

Implements the simplified fundamental diagram from the assignment:
    flow = A * speed^2 + B * speed

Where:
    A = -1.4648375
    B = 93.75
    Turning point (capacity): flow=1500 veh/hr, speed=32 km/hr
    Speed limit: 60 km/hr, reached at flow <= 351 veh/hr

Rules:
    - flow <= 351 veh/hr  -> speed = 60 km/hr (capped at speed limit)
    - flow > 351          -> solve quadratic, use green line (under-capacity root)
    - Assume all segments are under capacity
    - travel_time = distance / speed (seconds) + 30s per intersection
"""

import math

# Quadratic coefficients: flow = A * speed^2 + B * speed
A: float = -1.4648375
B: float = 93.75

SPEED_LIMIT: float = 60.0          # km/hr
FLOW_AT_CAPACITY: float = 1500.0   # veh/hr (turning point)
FLOW_THRESHOLD: float = 351.0      # veh/hr -- below this, speed = speed limit
INTERSECTION_DELAY: float = 30.0   # seconds per controlled intersection


def flow_to_speed(flow: float) -> float:
    """Convert traffic flow (veh/hr) to speed (km/hr).

    Uses the green line (under-capacity / higher speed root) of the
    fundamental diagram quadratic.

    Args:
        flow: traffic flow in vehicles per hour (>= 0).

    Returns:
        Speed in km/hr, capped at SPEED_LIMIT (60).

    Raises:
        ValueError: if flow is negative.
    """
    if flow < 0:
        raise ValueError(f"Flow cannot be negative, got {flow}")

    if flow <= FLOW_THRESHOLD:
        return SPEED_LIMIT

    # Clamp flow at capacity to avoid negative discriminant
    flow = min(flow, FLOW_AT_CAPACITY)

    # Solve:  A*speed^2 + B*speed - flow = 0
    # Rearranged:  A*speed^2 + B*speed - flow = 0
    # Quadratic formula: speed = (-B +/- sqrt(B^2 + 4*A*flow)) / (2*A)
    # Note: A is negative, so discriminant = B^2 + 4*A*flow (the sign is correct
    # because the equation is A*s^2 + B*s - flow = 0, so disc = B^2 - 4*A*(-flow))
    discriminant = B * B + 4 * A * flow
    if discriminant < 0:
        # At or beyond capacity -- return capacity speed
        return 32.0

    sqrt_disc = math.sqrt(discriminant)

    # Green line (under-capacity) = higher speed root
    # Since A < 0, the higher root is: (-B - sqrt_disc) / (2*A)
    speed = (-B - sqrt_disc) / (2 * A)

    return min(speed, SPEED_LIMIT)


def compute_travel_time(
    distance_km: float,
    flow: float,
    num_intersections: int = 1,
) -> float:
    """Compute travel time in seconds for a single road segment.

    Args:
        distance_km: segment length in kilometers (must be > 0).
        flow: predicted traffic flow in veh/hr at the starting sensor.
        num_intersections: number of controlled intersections to pass (default 1).

    Returns:
        Travel time in seconds (drive time + intersection delays).
    """
    speed = flow_to_speed(flow)
    drive_time = (distance_km / speed) * 3600  # hours -> seconds
    return drive_time + INTERSECTION_DELAY * num_intersections
