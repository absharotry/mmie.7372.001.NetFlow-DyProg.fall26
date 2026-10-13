"""Toolchain demo: run one hand-checkable graph through every library the project uses.

This uses only *library* implementations (scipy, networkx). Our own from-scratch Dijkstra and
Floyd-Warshall are written in Phase 1. Run with:

    python scripts/demo_toolchain.py
"""

import os

# Pin BLAS/OpenMP threads BEFORE numpy is imported (CLAUDE.md, benchmark methodology).
# Once numpy has loaded its BLAS library, changing these variables has no effect.
for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(var, "1")

import math
import resource
import statistics
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to a file; no GUI window needed
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import psutil
from scipy.sparse import coo_array
from scipy.sparse.csgraph import dijkstra, floyd_warshall

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

# --- 1. The toy graph --------------------------------------------------------------------------

NODES = ["A", "B", "C", "D", "E"]
IDX = {name: i for i, name in enumerate(NODES)}
INF = math.inf

# Directed edges (u, v, weight). A->B appears twice on purpose: a multi-edge.
EDGES = [
    ("A", "B", 4),
    ("A", "C", 1),
    ("C", "B", 2),
    ("B", "D", 1),
    ("C", "D", 5),
    ("D", "E", 3),
    ("A", "B", 10),  # duplicate of A->B with a worse weight
]

# Distances worked out by hand (row = source, column = target).
# A->B = 3 via A->C->B (2 hops) beats the direct edge (1 hop, weight 4).
EXPECTED = np.array(
    [
        [0, 3, 1, 4, 7],
        [INF, 0, INF, 1, 4],
        [INF, 2, 0, 3, 6],
        [INF, INF, INF, 0, 3],
        [INF, INF, INF, INF, 0],
    ]
)


def to_sparse(edges, n):
    """Build an n x n CSR matrix straight from an edge list (no dense intermediate).

    Building from (row, col, value) triples avoids the dense-input pitfall: in a dense array
    scipy's csgraph reads 0 as "no edge", so a real zero-weight edge would vanish.
    """
    rows = [IDX[u] for u, _, _ in edges]
    cols = [IDX[v] for _, v, _ in edges]
    vals = [w for _, _, w in edges]
    # PITFALL: COO -> CSR conversion SUMS duplicate (row, col) entries.
    return coo_array((vals, (rows, cols)), shape=(n, n)).tocsr()


def dedup_keep_min(edges):
    """Collapse multi-edges, keeping the smallest weight (the only one a shortest path would use).

    Keeping the minimum is a modeling decision; for the real datasets it is still an open question
    in CLAUDE.md.
    """
    best = {}
    for u, v, w in edges:
        best[(u, v)] = min(w, best.get((u, v), INF))
    return [(u, v, w) for (u, v), w in best.items()]


def networkx_apsp(edges, n):
    """Reference answer from networkx (the correctness oracle), as an n x n matrix with inf gaps."""
    g = nx.DiGraph()
    g.add_nodes_from(NODES)
    g.add_weighted_edges_from(edges)
    dist = np.full((n, n), INF)
    for src, lengths in nx.all_pairs_dijkstra_path_length(g):
        for dst, d in lengths.items():
            dist[IDX[src], IDX[dst]] = d
    return dist


def time_it(fn, repeats=5):
    """1 warm-up run (discarded), then `repeats` timed runs. Returns (result, median s, min s)."""
    result = fn()  # warm-up: first call can pay one-off costs (imports, caches)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - t0)
    return result, statistics.median(times), min(times)


def peak_rss_mib():
    """Peak resident memory of THIS process so far, in MiB.

    ru_maxrss is in bytes on macOS but KiB on Linux. This is the whole process's peak (imports
    included), so it is not a per-algorithm number; the Phase 3 harness gets those by running each
    algorithm in a fresh subprocess.
    """
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    bytes_ = raw if sys.platform == "darwin" else raw * 1024
    return bytes_ / 2**20


def feasibility(n, m):
    """Back-of-envelope cost estimates, the same reasoning the Phase 3 pre-check will use."""
    return {
        "n": n,
        "m": m,
        "n^2 matrix (float64)": f"{n * n * 8 / 2**30:,.3g} GiB",
        "FW ops ~ n^3": f"{n**3:.2e}",
        "n x Dijkstra ops ~ n*m*log2(n)": f"{n * m * math.log2(max(n, 2)):.2e}",
    }


def draw(edges, path):
    g = nx.DiGraph()
    g.add_weighted_edges_from(edges)
    pos = {"A": (0, 1), "B": (1, 2), "C": (1, 0), "D": (2, 1), "E": (3, 1)}  # fixed, readable layout
    fig, ax = plt.subplots(figsize=(6, 3.5))
    nx.draw_networkx(g, pos, ax=ax, node_color="#cfe2f3", node_size=900, arrowsize=18)
    nx.draw_networkx_edge_labels(g, pos, ax=ax, edge_labels=nx.get_edge_attributes(g, "weight"))
    ax.set_title("Toy graph (after multi-edge dedup)")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    n = len(NODES)
    pd.set_option("display.width", 120)

    # --- 2. Multi-edge pitfall -----------------------------------------------------------------
    naive = to_sparse(EDGES, n)
    print(f"Naive COO->CSR, A->B weight = {naive[IDX['A'], IDX['B']]}  (4 + 10 summed: WRONG)")
    edges = dedup_keep_min(EDGES)
    graph = to_sparse(edges, n)
    print(f"Dedup keep-min,  A->B weight = {graph[IDX['A'], IDX['B']]}  (correct)\n")

    # --- 3. Three ways to compute all-pairs shortest paths -------------------------------------
    # n x Dijkstra: csgraph.dijkstra with no `indices` runs one single-source Dijkstra per node.
    d_dij, dij_med, dij_min = time_it(lambda: dijkstra(graph, directed=True))
    # Floyd-Warshall: n sweeps; sweep k allows vertex k as an intermediate stop.
    d_fw, fw_med, fw_min = time_it(lambda: floyd_warshall(graph, directed=True))
    d_nx = networkx_apsp(edges, n)

    # --- 4. Correctness: everything must match the hand-computed table -------------------------
    # np.allclose treats inf == inf as equal when both are in the same position.
    for name, d in [("scipy dijkstra", d_dij), ("scipy floyd_warshall", d_fw), ("networkx", d_nx)]:
        status = "OK" if np.allclose(d, EXPECTED) else "MISMATCH"
        print(f"{name:<22} vs hand table: {status}")

    # --- 5. Pretty table -----------------------------------------------------------------------
    print("\nAll-pairs distances (row = source, column = target):")
    print(pd.DataFrame(d_fw, index=NODES, columns=NODES))
    reachable = np.isfinite(d_fw).sum() - n  # exclude the n diagonal zeros
    print(f"Reachable ordered pairs (excluding self): {reachable} / {n * (n - 1)}")

    # --- 6. Timing + memory --------------------------------------------------------------------
    print("\nTiming (1 warm-up + 5 repeats; a toy graph only measures call overhead):")
    print(f"  scipy dijkstra       median {dij_med * 1e6:8.1f} us   min {dij_min * 1e6:8.1f} us")
    print(f"  scipy floyd_warshall median {fw_med * 1e6:8.1f} us   min {fw_min * 1e6:8.1f} us")
    print(f"Peak RSS of this process: {peak_rss_mib():.1f} MiB")

    # --- 7. Feasibility estimates --------------------------------------------------------------
    print(f"\nMachine RAM: {psutil.virtual_memory().total / 2**30:.1f} GiB")
    rows = [
        feasibility(n, graph.nnz),
        feasibility(1574, 28236),  # US Airports, from its KONECT header line
        feasibility(100_000, 1_000_000),  # hypothetical Slashdot/Wiki-scale graph
    ]
    table = pd.DataFrame(rows, index=["toy", "US Airports", "n=100k (hypothetical)"])
    print(table.to_string())

    # --- 8. Figure -----------------------------------------------------------------------------
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / "demo_graph.png"
    draw(edges, out)
    print(f"\nSaved figure: {out.relative_to(RESULTS_DIR.parent)}")


if __name__ == "__main__":
    main()
