"""Tier 2 ("numpy"): from-scratch Floyd-Warshall, vectorized with numpy.

Same algorithm and same Theta(n^3) work as apsp.pure.apsp_floyd_warshall. The difference is WHO
runs the two inner loops: here numpy does them in compiled C code, one whole n x n table per sweep,
instead of the Python interpreter doing them one cell at a time.
"""

import numpy as np


def edges_to_dense(n, edges):
    """Starting table for Floyd-Warshall: dist[u, v] = weight of edge u -> v, inf if none, 0 on
    the diagonal. Multi-edges keep the smallest weight."""
    dist = np.full((n, n), np.inf)
    np.fill_diagonal(dist, 0.0)
    if edges:
        u, v, w = (np.asarray(col) for col in zip(*edges))
        # np.minimum.at handles repeated (u, v) pairs correctly (keeps the min). Plain fancy
        # assignment dist[u, v] = w would silently keep whichever duplicate came LAST.
        np.minimum.at(dist, (u, v), w.astype(float))
    return dist


def floyd_warshall_sweeps_numpy(dist):
    """The vectorized Floyd-Warshall loop, updating the float array `dist` in place. This is the part
    the benchmark times. Peak extra memory: one temporary n x n table (via_k)."""
    n = dist.shape[0]
    for k in range(n):  # the k-th intermediate-vertex sweep (still a Python loop: n iterations)
        # Column k as shape (n, 1) and row k as shape (1, n). Adding them "broadcasts" to an
        # (n, n) table whose cell [i, j] = dist[i, k] + dist[k, j], i.e. the cost of i -> k -> j
        # for EVERY pair at once. This replaces the pure version's i and j loops.
        via_k = dist[:, k, np.newaxis] + dist[np.newaxis, k, :]
        # Relaxation for all pairs at once: keep whichever is shorter, direct or via k.
        # out=dist writes in place, so we don't allocate a third n x n array each sweep.
        np.minimum(dist, via_k, out=dist)


def check_no_negative_cycle_numpy(dist):
    """Negative-cycle check: a node that can return to itself for less than 0."""
    bad = np.flatnonzero(np.diagonal(dist) < 0)
    if bad.size:
        raise ValueError(f"graph contains a negative cycle through node {bad[0]}")


def apsp_floyd_warshall_numpy(n, edges):
    """All-pairs shortest paths by vectorized Floyd-Warshall. Returns an n x n float64 array.

    Negative edge weights are allowed; a negative cycle raises ValueError.
    """
    dist = edges_to_dense(n, edges)
    floyd_warshall_sweeps_numpy(dist)
    check_no_negative_cycle_numpy(dist)
    return dist
