"""Tier 1 ("pure"): from-scratch, pure-Python shortest-path algorithms.

For learning and correctness checks on small graphs only; never used for the real benchmarks.

Graph convention used throughout this module:
    nodes are integers 0 .. n-1
    edges is a list of (u, v, w) triples meaning a directed edge u -> v with weight w
"""

import heapq
import math


def adjacency_list(n, edges):
    """Turn an edge list into an adjacency list: adj[u] = [(v, w), ...] for each edge u -> v.

    Multi-edges are kept as-is. Dijkstra does not need them removed: relaxing a parallel edge
    with a larger weight simply never improves anything, so the smallest one wins automatically.
    """
    adj = [[] for _ in range(n)]
    for u, v, w in edges:
        if w < 0:
            # Dijkstra's "settled means final" argument needs every weight >= 0.
            raise ValueError(f"Dijkstra requires nonnegative weights; edge {u}->{v} has {w}")
        adj[u].append((v, w))
    return adj


def dijkstra(adj, source):
    """Single-source shortest distances from `source`. Returns a list; unreachable nodes are inf.

    Uses a binary heap (heapq) as the priority queue, with "lazy deletion": instead of lowering a
    node's key inside the heap (heapq can't do that), we push a NEW (distance, node) entry and skip
    stale entries when they are popped. The heap then holds at most m + 1 entries, so each push or
    pop costs O(log m) = O(log n), and the whole run is O(m log n).
    """
    dist = [math.inf] * len(adj)
    dist[source] = 0
    heap = [(0, source)]  # (best distance found so far, node)

    while heap:
        d, u = heapq.heappop(heap)  # the unsettled node with the smallest tentative distance
        if d > dist[u]:
            continue  # stale entry: u was already settled with a smaller distance
        # u is now settled: dist[u] is final, because every other route to u must pass through a
        # node that is at least as far away, and nonnegative weights can't make it shorter.
        for v, w in adj[u]:
            # Relaxation step: is "source -> ... -> u -> v" shorter than the best known route to v?
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(heap, (dist[v], v))
    return dist


def apsp_dijkstra(n, edges):
    """All-pairs shortest paths by running Dijkstra once from every node: O(n * m log n).

    Returns an n x n list of lists; row i holds the distances from node i.
    """
    adj = adjacency_list(n, edges)  # built once, reused by all n runs
    return [dijkstra(adj, s) for s in range(n)]


def apsp_floyd_warshall(n, edges):
    """All-pairs shortest paths by Floyd-Warshall: Theta(n^3) time, Theta(n^2) memory.

    Negative edge weights are allowed; a negative cycle raises ValueError.
    Returns an n x n list of lists; row i holds the distances from node i.
    """
    # Start: only direct edges are known. dist[i][j] = weight of edge i -> j, inf if none.
    dist = [[math.inf] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0  # staying put costs nothing
    for u, v, w in edges:
        # Multi-edges: a shortest path can only ever use the cheapest parallel edge.
        dist[u][v] = min(dist[u][v], w)

    # Invariant: after sweep k, dist[i][j] is the shortest i -> j path whose intermediate stops
    # are all among nodes 0..k. The k loop MUST be the outermost loop for this to hold.
    for k in range(n):  # the k-th intermediate-vertex sweep: now node k may be used as a stop
        dist_k = dist[k]
        for i in range(n):
            d_ik = dist[i][k]
            if d_ik == math.inf:
                continue  # i can't reach k, so no route i -> k -> j exists for any j
            dist_i = dist[i]
            for j in range(n):
                # Same relaxation idea as Dijkstra: is "i -> k -> j" shorter than the best i -> j?
                if d_ik + dist_k[j] < dist_i[j]:
                    dist_i[j] = d_ik + dist_k[j]

    # Negative-cycle check: if some node can get back to itself for less than 0, then going round
    # that loop again and again makes paths arbitrarily short, so "shortest" has no meaning.
    for i in range(n):
        if dist[i][i] < 0:
            raise ValueError(f"graph contains a negative cycle through node {i}")
    return dist
