"""Dataset characteristics: the numbers that explain WHY an algorithm is fast or slow on a graph.

describe() covers structure (which edges exist); describe_weights() covers the edge values. The
describe script reports structure of the PROCESSED graph (what the algorithms actually see) and
weights of both the raw and the processed data.
"""

import numpy as np
from scipy.sparse import csr_array
from scipy.sparse.csgraph import breadth_first_order, connected_components


def structure_matrix(n, u, v, directed=True):
    """0/1 adjacency matrix of the distinct pairs (weights ignored). Used for degrees, components
    and reachability, which only depend on WHICH edges exist. Undirected: both directions stored."""
    if not directed:
        u, v = np.concatenate([u, v]), np.concatenate([v, u])
    pairs = np.unique(np.column_stack([u, v]), axis=0)
    return csr_array((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))


def reachable_pairs_directed(adj):
    """Number of ordered pairs (i, j), i != j, with a directed path from i to j.

    Exact: one breadth-first search from every node, O(n * m) total. Fine for thousands of nodes.
    """
    return sum(len(breadth_first_order(adj, s, directed=True, return_predecessors=False)) - 1
               for s in range(adj.shape[0]))


def reachable_pairs_undirected(component_labels):
    """Undirected graphs: everyone in a connected component reaches everyone else in it, and nobody
    outside it. So a component of size s contributes s * (s - 1) ordered pairs. O(n), exact."""
    sizes = np.bincount(component_labels)
    return int((sizes * (sizes - 1)).sum())


def _stats(x):
    return {"min": x.min(), "median": float(np.median(x)), "mean": x.mean(), "max": x.max()}


def describe(ds):
    """Structural characteristics of a Dataset (see apsp.loaders.Dataset)."""
    n, u, v = ds.n, ds.u, ds.v
    adj = structure_matrix(n, u, v, ds.directed)
    out_deg = np.diff(adj.indptr)  # stored entries per row = out-degree (= degree if undirected)
    self_loops = int(adj.diagonal().sum())

    info = {"name": ds.name, "directed": ds.directed, "n": n, "m (edge rows)": len(u)}

    if ds.directed:
        pairs = set(zip(u.tolist(), v.tolist()))
        in_deg = np.bincount(adj.indices, minlength=n)
        n_wcc, wcc = connected_components(adj, directed=True, connection="weak")
        n_scc, scc = connected_components(adj, directed=True, connection="strong")
        info |= {
            "m (distinct pairs)": adj.nnz,
            "one-way edges (algorithms)": adj.nnz,
            "duplicate rows": len(u) - adj.nnz,
            "self-loops": self_loops,
            "density m/(n(n-1))": adj.nnz / (n * (n - 1)),
            "reciprocity": sum((b, a) in pairs for a, b in pairs) / len(pairs),
            "weak components": n_wcc,
            "largest weak comp.": int(np.bincount(wcc).max()),
            "strong components": n_scc,
            "largest strong comp.": int(np.bincount(scc).max()),
            "nodes with out-degree 0": int((out_deg == 0).sum()),
            "nodes with in-degree 0": int((in_deg == 0).sum()),
            "reachable pair fraction": reachable_pairs_directed(adj) / (n * (n - 1)),
        }
        degree_series = {"out-degree": out_deg, "in-degree": in_deg}
    else:
        n_pairs = (adj.nnz + self_loops) // 2  # each non-loop pair is stored twice
        n_cc, cc = connected_components(adj, directed=False)
        # A repeat = the same (u, v) row twice. Storing a pair as both (u, v) and (v, u) is not a
        # repeat; processed undirected graphs do that on purpose.
        distinct_rows = len(np.unique(np.column_stack([u, v]), axis=0))
        info |= {
            "m (distinct pairs)": n_pairs,
            "one-way edges (algorithms)": adj.nnz,
            "duplicate rows": len(u) - distinct_rows,
            "self-loops": self_loops,
            "density pairs/(n(n-1)/2)": n_pairs / (n * (n - 1) / 2),
            "components": n_cc,
            "largest component": int(np.bincount(cc).max()),
            "isolated nodes": int((out_deg == 0).sum()),
            "reachable pair fraction": reachable_pairs_undirected(cc) / (n * (n - 1)),
        }
        degree_series = {"degree": out_deg}

    for name, deg in degree_series.items():
        for key, val in _stats(deg).items():
            info[f"{name} {key}"] = val
    return info


def describe_weights(w, prefix):
    """Summary of edge values, keys prefixed (e.g. "raw weight", "distance")."""
    info = {
        f"{prefix} all equal": bool(len(np.unique(w)) == 1),
        f"{prefix} negative share": float((w < 0).mean()),
        f"{prefix} zero share": float((w == 0).mean()),
    }
    for key, val in _stats(w).items():
        info[f"{prefix} {key}"] = val
    return info
