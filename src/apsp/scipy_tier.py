"""Tier 3 ("scipy"): thin, guarded wrappers around scipy.sparse.csgraph. Used for the real benchmarks.

Building the graph (edges_to_csr) is kept separate from the algorithms so that the benchmark can
time the algorithm alone, not the data preparation.

scipy behavior verified on scipy 1.17.1 (see tests/test_scipy_tier.py):
- An explicit 0 stored in a sparse matrix IS an edge. But eliminate_zeros() and sparse arithmetic
  (e.g. g + g) silently drop stored zeros, and in a DENSE matrix 0 means "no edge".
- COO -> CSR conversion SUMS duplicate (row, col) entries.
- csgraph.dijkstra only WARNS on negative weights. It re-processes nodes whose distance drops,
  which gives correct distances without negative cycles but is no longer Dijkstra's algorithm
  (the O(m log n) bound is lost). We therefore reject negative weights ourselves.
- csgraph.floyd_warshall raises NegativeCycleError on a negative cycle.
"""

import numpy as np
from scipy.sparse import csr_array
from scipy.sparse.csgraph import NegativeCycleError, dijkstra, floyd_warshall


def edges_to_csr(n, edges):
    """Build an n x n CSR matrix from (u, v, w) triples, keeping the MIN weight of multi-edges.

    Duplicates must be removed BEFORE building the matrix, because COO -> CSR would sum them.
    """
    if not edges:
        return csr_array((n, n), dtype=float)
    u, v, w = (np.asarray(col) for col in zip(*edges))
    w = w.astype(float)
    # Sort by u, then v, then w (np.lexsort uses the LAST key as the primary one). Within each
    # (u, v) group the smallest weight now comes first; keep only that first row of each group.
    order = np.lexsort((w, v, u))
    u, v, w = u[order], v[order], w[order]
    first_of_group = np.ones(len(u), dtype=bool)
    first_of_group[1:] = (u[1:] != u[:-1]) | (v[1:] != v[:-1])
    u, v, w = u[first_of_group], v[first_of_group], w[first_of_group]
    # No duplicates remain, so nothing gets summed, and explicit zero weights are kept as edges.
    return csr_array((w, (u, v)), shape=(n, n))


def apsp_dijkstra_scipy(graph):
    """n x Dijkstra via scipy (C implementation, Fibonacci-heap priority queue). Returns n x n array.

    With no `indices` argument scipy runs Dijkstra from every node and returns the full n x n table.
    (For large n the benchmark will instead pass batches of sources; that comes in Phase 3.)
    """
    if graph.nnz and graph.data.min() < 0:
        raise ValueError("Dijkstra requires nonnegative weights; graph has negative edges")
    return dijkstra(graph, directed=True)


def apsp_floyd_warshall_scipy(graph):
    """Floyd-Warshall via scipy (C implementation, dense n x n table). Returns n x n array.

    Negative edge weights are allowed; a negative cycle raises ValueError, matching the other tiers.
    """
    try:
        return floyd_warshall(graph, directed=True)
    except NegativeCycleError as err:
        raise ValueError(f"graph contains a negative cycle ({err})") from err
