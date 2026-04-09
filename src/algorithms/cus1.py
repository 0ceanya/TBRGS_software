"""Adaptive Survivor Search (CUS1) -- uninformed custom algorithm.

Ported from Part A (cos30019-Assignment2A) as a standalone copy.
Cost-limited DFS with self-calibrating limit updates, MAD filtering,
reservoir sampling, and a multi-level escalation ladder.

NOTE: This algorithm uses graph.origin and graph.destinations directly
rather than taking them as parameters. The registry wrapper handles this.
"""

import math
import random
import sys
from typing import List, Optional, Tuple

from src.core.graph import Graph

_RESERVOIR_MAX_SIZE: int = 10_000
_FAST_PATH_CV_THRESHOLD: float = 0.3
_FAST_PATH_COUNT_THRESHOLD: int = 50
_STAGNATION_THRESHOLDS: Tuple[int, ...] = (3, 2, 2, 1)
_RECOVERY_STREAK_NEEDED: int = 3
_MAX_ESCALATION_LEVEL: int = 4
_DELTA_SCALE_FACTOR: float = 0.1
_LOG_DAMPENING_BASE: float = 10.0
_GROWTH_CAP_MULTIPLIER: float = 2.0
_MAD_THRESHOLD: float = 3.0
_PROGRESS_RECOVERY_THRESHOLD: float = 0.05
_RTOL: float = 1e-9
_ATOL: float = 1e-9
_EPSILON_STABILITY: float = sys.float_info.epsilon * 1000


def adaptive_survivor_search(
    graph: Graph, base_delta: float = 5.0
) -> Tuple[List[int], int]:
    nodes_generated: int = 0
    adj: dict = {u: {v: c for v, c in nbrs} for u, nbrs in graph.edges.items()}

    reservoir: List[float] = []
    reservoir_count: int = 0
    observed_max: float = 0.0
    iteration_history: List[Tuple[float, int]] = []

    escalation_level: int = 0
    stagnation_count: int = 0
    recovery_streak: int = 0

    binary_low: float = 0.0
    binary_high: float = 0.0

    def _median(values: List[float]) -> float:
        vals = sorted(values)
        n = len(vals)
        return vals[n // 2] if n % 2 == 1 else (vals[n // 2 - 1] + vals[n // 2]) / 2

    def _mad(values: List[float], med: float) -> float:
        return _median([abs(x - med) for x in values])

    def _cv(values: List[float]) -> float:
        n = len(values)
        mean = sum(values) / n
        if mean < _EPSILON_STABILITY:
            return 0.0
        std = (sum((x - mean) ** 2 for x in values) / n) ** 0.5
        return std / mean

    def _convergence_epsilon(high: float, low: float) -> float:
        return _ATOL + _RTOL * max(abs(high), abs(low))

    def _adaptive_delta(exceeded_costs: List[float]) -> float:
        cost_range = max(exceeded_costs) - min(exceeded_costs)
        if cost_range < _EPSILON_STABILITY:
            return base_delta
        log_damp = 1.0 + math.log(
            1.0 + math.log(max(1.0, cost_range), _LOG_DAMPENING_BASE),
            _LOG_DAMPENING_BASE,
        )
        scale = _DELTA_SCALE_FACTOR / log_damp
        return max(base_delta, cost_range * scale)

    def _mad_filter(exceeded_costs: List[float]) -> List[float]:
        if len(exceeded_costs) < 2:
            return exceeded_costs
        med = _median(exceeded_costs)
        mad_val = _mad(exceeded_costs, med)
        if mad_val < _EPSILON_STABILITY:
            return exceeded_costs
        return [x for x in exceeded_costs if abs(x - med) <= _MAD_THRESHOLD * mad_val]

    def _reservoir_insert(value: float) -> None:
        nonlocal reservoir_count
        reservoir_count += 1
        if len(reservoir) < _RESERVOIR_MAX_SIZE:
            reservoir.append(value)
        else:
            idx = random.randint(0, reservoir_count - 1)
            if idx < _RESERVOIR_MAX_SIZE:
                reservoir[idx] = value

    def _dfs(
        node: int,
        current_cost: float,
        limit: float,
        path: List[int],
        path_set: set,
        exceeded_costs: List[float],
    ) -> Optional[List[int]]:
        nonlocal nodes_generated
        if current_cost > limit:
            exceeded_costs.append(current_cost)
            return None
        nodes_generated += 1
        if node in graph.destinations:
            return list(path)
        for neighbor in sorted(adj.get(node, {})):
            if neighbor in path_set:
                continue
            path.append(neighbor)
            path_set.add(neighbor)
            result = _dfs(
                neighbor,
                current_cost + adj[node][neighbor],
                limit,
                path,
                path_set,
                exceeded_costs,
            )
            if result is not None:
                return result
            path.pop()
            path_set.discard(neighbor)
        return None

    def _is_fast_path(exceeded_costs: List[float]) -> bool:
        if len(exceeded_costs) > _FAST_PATH_COUNT_THRESHOLD:
            return False
        return _cv(exceeded_costs) < _FAST_PATH_CV_THRESHOLD

    def _compute_next_limit(
        limit: float, exceeded_costs: List[float]
    ) -> Tuple[float, bool]:
        smallest = min(exceeded_costs)
        if _is_fast_path(exceeded_costs):
            med = _median(exceeded_costs)
            delta = _adaptive_delta(exceeded_costs)
            new_limit = min(med, smallest + delta)
            if new_limit <= limit:
                new_limit = smallest
            return (
                min(new_limit, limit * _GROWTH_CAP_MULTIPLIER) if limit > 0 else new_limit,
                False,
            )
        filtered = _mad_filter(exceeded_costs)
        if len(filtered) < 2:
            return smallest, True
        med = _median(filtered)
        delta = _adaptive_delta(filtered)
        cv = _cv(filtered)
        mad_val = _mad(filtered, med)
        if mad_val < _EPSILON_STABILITY and len(filtered) > _FAST_PATH_COUNT_THRESHOLD:
            return smallest + delta, True
        if cv < 0.3:
            new_limit = min(med, smallest + delta)
        elif cv < 1.0:
            new_limit = min(med, smallest + delta * 0.75)
        else:
            p25_idx = max(0, int(len(filtered) * 0.25) - 1)
            p25 = sorted(filtered)[p25_idx]
            new_limit = min(p25 * 3, smallest + delta * 0.5)
        is_stagnating = new_limit <= limit
        if is_stagnating:
            new_limit = smallest
        if limit > 0:
            new_limit = min(new_limit, limit * _GROWTH_CAP_MULTIPLIER)
        return new_limit, is_stagnating

    def _escalated_limit(limit: float, exceeded_costs: List[float]) -> float:
        smallest = min(exceeded_costs)
        if escalation_level == 1:
            return smallest
        elif escalation_level == 2:
            return limit * 2.0
        elif escalation_level == 3:
            if len(reservoir) >= 4:
                p75_idx = int(len(reservoir) * 0.75)
                return sorted(reservoir)[p75_idx]
            return limit * 2.0
        elif escalation_level == 4:
            nonlocal binary_low, binary_high
            binary_low = limit
            binary_high = observed_max if observed_max > limit else limit * 2.0
            return (binary_low + binary_high) / 2.0
        return limit

    origin_costs = list(adj.get(graph.origin, {}).values())
    limit = min(origin_costs) if origin_costs else 0.0

    while True:
        nodes_generated = 0
        exceeded_costs: List[float] = []
        path = [graph.origin]
        path_set = {graph.origin}

        result = _dfs(graph.origin, 0.0, limit, path, path_set, exceeded_costs)
        if result is not None:
            return result, nodes_generated
        if not exceeded_costs:
            return [], nodes_generated

        for c in exceeded_costs:
            _reservoir_insert(c)
        observed_max = max(observed_max, max(exceeded_costs))
        iteration_history.append((limit, nodes_generated))

        if escalation_level == _MAX_ESCALATION_LEVEL:
            if binary_high - binary_low < _convergence_epsilon(binary_high, binary_low):
                return [], nodes_generated
            binary_low = limit
            limit = (binary_low + binary_high) / 2.0
            continue

        new_limit, is_stagnating = _compute_next_limit(limit, exceeded_costs)
        progress_ratio = (new_limit - limit) / max(_EPSILON_STABILITY, abs(limit))
        made_progress = progress_ratio >= _PROGRESS_RECOVERY_THRESHOLD

        if is_stagnating or not made_progress:
            stagnation_count += 1
            recovery_streak = 0
        else:
            stagnation_count = 0
            recovery_streak += 1

        threshold = _STAGNATION_THRESHOLDS[
            min(escalation_level, len(_STAGNATION_THRESHOLDS) - 1)
        ]
        if stagnation_count >= threshold:
            escalation_level = min(escalation_level + 1, _MAX_ESCALATION_LEVEL)
            stagnation_count = 0
            new_limit = _escalated_limit(limit, exceeded_costs)
        elif recovery_streak >= _RECOVERY_STREAK_NEEDED and escalation_level > 0:
            escalation_level -= 1
            recovery_streak = 0

        if new_limit <= limit:
            new_limit = min(exceeded_costs)
        limit = new_limit
