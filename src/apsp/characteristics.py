"""Dataset characteristics: the numbers that explain WHY an algorithm is fast or slow on a graph."""

import numpy as np
from scipy.sparse import csr_array
from scipy.sparse.csgraph import breadth_first_order, connected_components


def structure_matrix(n, u, v):
    """0/1 adjacency matrix of the distinct directed pairs (weights ignored). Used for degrees,
    components and reachability, which only depend on WHICH edges exist."""
    pairs = np.unique(np.column_stack([u, v]), axis=0)
    return csr_array((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))


def reachable_pairs(adj):
    """Number of ordered pairs (i, j), i != j, with a directed path from i to j.

    Exact: one breadth-first search from every node, O(n * m) total. Fine for thousands of nodes;
    the large datasets will need a cheaper method (to be decided in Phase 2).
    """
    return sum(len(breadth_first_order(adj, s, directed=True, return_predecessors=False)) - 1
               for s in range(adj.shape[0]))


def _stats(x):
    return {"min": x.min(), "median": float(np.median(x)), "mean": x.mean(), "max": x.max()}


def describe(ds):
    """Return a flat dict of characteristics for a Dataset (see apsp.loaders.Dataset)."""
    n, u, v, w = ds.n, ds.u, ds.v, ds.w
    adj = structure_matrix(n, u, v)
    m_distinct = adj.nnz
    pairs = set(zip(u.tolist(), v.tolist()))
    out_deg = np.diff(adj.indptr)  # number of stored entries per row = out-degree
    in_deg = np.bincount(adj.indices, minlength=n)
    n_wcc, wcc = connected_components(adj, directed=True, connection="weak")
    n_scc, scc = connected_components(adj, directed=True, connection="strong")
    reach = reachable_pairs(adj)

    info = {
        "name": ds.name,
        "directed": ds.directed,
        "n": n,
        "m (edge rows)": len(u),
        "m (distinct pairs)": m_distinct,
        "duplicate rows": len(u) - m_distinct,
        "self-loops": int((u == v).sum()),
        "density m/(n(n-1))": m_distinct / (n * (n - 1)),
        "reciprocity": sum((b, a) in pairs for a, b in pairs) / len(pairs),
        "weighted": bool(len(np.unique(w)) > 1),
        "signed (any w<0)": bool((w < 0).any()),
        "zero weights": int((w == 0).sum()),
        "weak components": n_wcc,
        "largest weak comp.": int(np.bincount(wcc).max()),
        "strong components": n_scc,
        "largest strong comp.": int(np.bincount(scc).max()),
        "nodes with out-degree 0": int((out_deg == 0).sum()),
        "nodes with in-degree 0": int((in_deg == 0).sum()),
        "reachable pair fraction": reach / (n * (n - 1)),
    }
    for key, val in _stats(out_deg).items():
        info[f"out-degree {key}"] = val
    for key, val in _stats(in_deg).items():
        info[f"in-degree {key}"] = val
    for key, val in _stats(w).items():
        info[f"weight {key}"] = val
    return info
