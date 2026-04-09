"""Bidirectional A* with Adaptive Landmark Triangulation (BALA*) -- CUS2.

Ported from Part A (cos30019-Assignment2A) as a standalone copy.
Informed custom search that searches from both origin and destinations
simultaneously, using landmark-enhanced heuristics.
"""

import heapq
import math
from typing import Dict, List, Tuple

from src.core.graph import Graph


def _euclidean(graph: Graph, a: int, b: int) -> float:
    ax, ay = graph.get_coords(a)
    bx, by = graph.get_coords(b)
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def _heuristic_to_nearest(graph: Graph, node: int, destinations: List[int]) -> float:
    return min(_euclidean(graph, node, d) for d in destinations)


def _dijkstra(graph: Graph, source: int, forward: bool = True) -> Dict[int, float]:
    dist: Dict[int, float] = {source: 0}
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float("inf")):
            continue
        nbrs = (
            graph.get_neighbors_with_costs(u)
            if forward
            else graph.get_reverse_neighbors_with_costs(u)
        )
        for v, w in nbrs:
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


def _select_landmarks(graph: Graph) -> List[int]:
    if len(graph.nodes) < 4:
        return list(graph.nodes.keys())
    nodes_list = list(graph.nodes.items())
    landmarks = set()
    landmarks.add(max(nodes_list, key=lambda x: x[1][0])[0])
    landmarks.add(min(nodes_list, key=lambda x: x[1][0])[0])
    landmarks.add(max(nodes_list, key=lambda x: x[1][1])[0])
    landmarks.add(min(nodes_list, key=lambda x: x[1][1])[0])
    return list(landmarks)


def bala_star(
    graph: Graph, origin: int, destinations: List[int]
) -> Tuple[List[int], int]:
    """BALA*: Bidirectional A* with landmark heuristic.

    Returns (path, nodes_created). path == [] if no goal found.
    """
    dest_set = set(destinations)
    nodes_created = 0

    # Phase 1: Precompute landmark distances
    was_tracking = graph._tracking
    graph.disable_tracking()
    landmarks = _select_landmarks(graph)
    lm_fwd: Dict[int, Dict[int, float]] = {}
    lm_bwd: Dict[int, Dict[int, float]] = {}
    for lm in landmarks:
        lm_fwd[lm] = _dijkstra(graph, lm, forward=True)
        lm_bwd[lm] = _dijkstra(graph, lm, forward=False)
    if was_tracking:
        graph.enable_tracking()

    def _lm_h_fwd(node: int) -> float:
        best = 0.0
        for d in destinations:
            for lm in landmarks:
                dn = lm_fwd[lm].get(node, float("inf"))
                dd = lm_fwd[lm].get(d, float("inf"))
                if dn < float("inf") and dd < float("inf"):
                    best = max(best, abs(dn - dd))
                bn = lm_bwd[lm].get(node, float("inf"))
                bd = lm_bwd[lm].get(d, float("inf"))
                if bn < float("inf") and bd < float("inf"):
                    best = max(best, abs(bn - bd))
        return best

    def _lm_h_bwd(node: int) -> float:
        best = 0.0
        for lm in landmarks:
            dn = lm_fwd[lm].get(node, float("inf"))
            do = lm_fwd[lm].get(origin, float("inf"))
            if dn < float("inf") and do < float("inf"):
                best = max(best, abs(dn - do))
            bn = lm_bwd[lm].get(node, float("inf"))
            bo = lm_bwd[lm].get(origin, float("inf"))
            if bn < float("inf") and bo < float("inf"):
                best = max(best, abs(bn - bo))
        return best

    def h_fwd(node: int) -> float:
        return max(_heuristic_to_nearest(graph, node, destinations), _lm_h_fwd(node))

    def h_bwd(node: int) -> float:
        return max(_euclidean(graph, node, origin), _lm_h_bwd(node))

    # Phase 2: Bidirectional A*
    ctr_f = 0
    nodes_created += 1
    open_f = [(h_fwd(origin), origin, ctr_f, origin, [origin], 0)]
    best_g_f: Dict[int, float] = {origin: 0}

    ctr_b = 0
    open_b: list = []
    best_g_b: Dict[int, float] = {}
    for d in destinations:
        ctr_b += 1
        nodes_created += 1
        heapq.heappush(open_b, (h_bwd(d), d, ctr_b, d, [d], 0))
        best_g_b[d] = 0

    expanded_f: Dict[int, Tuple[float, List[int]]] = {}
    expanded_b: Dict[int, Tuple[float, List[int]]] = {}

    mu = float("inf")
    best_path = None

    while open_f or open_b:
        min_f = open_f[0][0] if open_f else float("inf")
        min_b = open_b[0][0] if open_b else float("inf")
        if mu <= min(min_f, min_b):
            break

        if min_f <= min_b and open_f:
            graph.set_tracking_direction("f")
            _, _, _, node, path, g = heapq.heappop(open_f)
            if g > best_g_f.get(node, float("inf")):
                continue
            expanded_f[node] = (g, path)

            if node in expanded_b:
                g_b, path_b = expanded_b[node]
                if g + g_b < mu:
                    mu = g + g_b
                    best_path = path + list(reversed(path_b[:-1]))

            if node in dest_set and g < mu:
                mu = g
                best_path = path

            path_set = set(path)
            for nb, cost in sorted(
                graph.get_neighbors_with_costs(node), key=lambda x: x[0]
            ):
                if nb not in path_set:
                    g_new = g + cost
                    if g_new < best_g_f.get(nb, float("inf")):
                        best_g_f[nb] = g_new
                        ctr_f += 1
                        nodes_created += 1
                        heapq.heappush(
                            open_f,
                            (g_new + h_fwd(nb), nb, ctr_f, nb, path + [nb], g_new),
                        )
                        if nb in expanded_b:
                            g_b, path_b = expanded_b[nb]
                            if g_new + g_b < mu:
                                mu = g_new + g_b
                                best_path = (path + [nb]) + list(
                                    reversed(path_b[:-1])
                                )

        elif open_b:
            graph.set_tracking_direction("b")
            _, _, _, node, path, g = heapq.heappop(open_b)
            if g > best_g_b.get(node, float("inf")):
                continue
            expanded_b[node] = (g, path)

            if node in expanded_f:
                g_f, path_f = expanded_f[node]
                if g_f + g < mu:
                    mu = g_f + g
                    best_path = path_f + list(reversed(path[:-1]))

            if node == origin and g < mu:
                mu = g
                best_path = list(reversed(path))

            path_set = set(path)
            for nb, cost in sorted(
                graph.get_reverse_neighbors_with_costs(node), key=lambda x: x[0]
            ):
                if nb not in path_set:
                    g_new = g + cost
                    if g_new < best_g_b.get(nb, float("inf")):
                        best_g_b[nb] = g_new
                        ctr_b += 1
                        nodes_created += 1
                        heapq.heappush(
                            open_b,
                            (g_new + h_bwd(nb), nb, ctr_b, nb, path + [nb], g_new),
                        )
                        if nb in expanded_f:
                            g_f, path_f = expanded_f[nb]
                            if g_f + g_new < mu:
                                mu = g_f + g_new
                                best_path = path_f + list(
                                    reversed((path + [nb])[:-1])
                                )
        else:
            break

    return (best_path, nodes_created) if best_path else ([], nodes_created)
