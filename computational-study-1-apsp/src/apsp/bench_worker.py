"""One benchmark measurement, run in a FRESH process by apsp.bench (never imported by it).

    python -m apsp.bench_worker <slug> <tier> <algo> [--processed-dir DIR]

Prints one JSON line to stdout. A fresh process per measurement means its peak memory (ru_maxrss)
belongs to this measurement alone, with no leftovers from earlier runs.

What is timed: only the shortest-path computation itself ("algo" time). Building the input
(sparse matrix, adjacency list, starting table) happens before the clock starts. Summarizing the
output (reachable pairs, mean and max distance) happens after, and is reported as "total" time.

Repeats: the first run is timed. If it took under SHORT_RUN_S seconds, it is treated as a warm-up
and discarded, and REPEATS more runs are timed. Otherwise that single run is the measurement.
"""

import os

# Single thread for every library, set BEFORE numpy is imported (CLAUDE.md, methodology).
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import functools
import json
import resource
import sys
import time

import numpy as np
from scipy.sparse.csgraph import dijkstra as scipy_dijkstra

from apsp import pure, scipy_tier, vectorized
from apsp.preprocess import PROCESSED_DIR, load_processed

SHORT_RUN_S = 10.0
REPEATS = 5
CHUNK_BYTES = 256 * 2**20  # rows of distances handled at once when streaming or summarizing


def peak_rss_bytes():
    """Peak resident memory of this process so far. ru_maxrss is bytes on macOS, KiB on Linux."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw if sys.platform == "darwin" else raw * 1024


def rows_per_chunk(n):
    return max(1, CHUNK_BYTES // (8 * n))


class Summary:
    """Running totals over rows of the distance table, excluding each row's own diagonal cell.
    Every algorithm produces the same Summary, which is how results are cross-checked at full scale."""

    def __init__(self):
        self.reachable = 0
        self.total = 0.0
        self.max = 0.0

    def add_rows(self, d, sources):
        """d: (k, n) distances from the k nodes in `sources`."""
        finite = np.isfinite(d)
        finite[np.arange(len(sources)), sources] = False  # a node reaching itself doesn't count
        values = d[finite]
        self.reachable += int(values.size)
        self.total += float(values.sum())
        if values.size:
            self.max = max(self.max, float(values.max()))

    def add_table(self, d):
        """Whole n x n table, summarized in row chunks so no extra n x n temporary is created
        (that would inflate the peak-memory measurement)."""
        n = d.shape[0]
        step = rows_per_chunk(n)
        for start in range(0, n, step):
            rows = np.arange(start, min(start + step, n))
            self.add_rows(np.asarray(d[start:start + len(rows)]), rows)

    def as_dict(self):
        return {"reachable_pairs": self.reachable,
                "mean_distance": self.total / self.reachable if self.reachable else None,
                "max_distance": self.max}


def edge_list(ds):
    return list(zip(ds.u.tolist(), ds.v.tolist(), ds.w.tolist()))


# --- One "prepare" (untimed, once) and one "run" (one full APSP) per algorithm --------------------
# Each run returns (Summary, algo_seconds).

def prepare_scipy(ds):
    graph = scipy_tier.edges_to_csr(ds.n, edge_list(ds))
    return graph


def run_scipy_dijkstra(graph, sources=None):
    # Checked once here, so calling scipy's dijkstra directly below is genuine Dijkstra.
    scipy_tier.check_nonnegative(graph)
    n = graph.shape[0]
    all_sources = np.arange(n) if sources is None else np.asarray(sources)
    summary, algo = Summary(), 0.0
    step = rows_per_chunk(n)
    for start in range(0, len(all_sources), step):  # streaming: a batch, summarize, discard
        sources = all_sources[start:start + step]
        t0 = time.perf_counter()
        d = scipy_dijkstra(graph, directed=True, indices=sources)
        algo += time.perf_counter() - t0
        summary.add_rows(d, sources)
        del d
    return summary, algo


def run_scipy_floyd_warshall(graph):
    t0 = time.perf_counter()
    d = scipy_tier.apsp_floyd_warshall_scipy(graph)  # includes scipy's sparse -> dense conversion
    algo = time.perf_counter() - t0
    summary = Summary()
    summary.add_table(d)
    return summary, algo


def run_numpy_floyd_warshall(ds):
    dist = vectorized.edges_to_dense(ds.n, edge_list(ds))  # fresh starting table, untimed
    t0 = time.perf_counter()
    vectorized.floyd_warshall_sweeps_numpy(dist)
    algo = time.perf_counter() - t0
    vectorized.check_no_negative_cycle_numpy(dist)
    summary = Summary()
    summary.add_table(dist)
    return summary, algo


def prepare_pure_dijkstra(ds):
    return pure.adjacency_list(ds.n, edge_list(ds))


def run_pure_dijkstra(adj, sources=None):
    summary, algo = Summary(), 0.0
    for s in range(len(adj)) if sources is None else sources:  # one source at a time, then discard
        t0 = time.perf_counter()
        row = pure.dijkstra(adj, s)
        algo += time.perf_counter() - t0
        summary.add_rows(np.asarray(row, dtype=float)[np.newaxis, :], np.array([s]))
    return summary, algo


def run_pure_floyd_warshall(ds):
    dist = pure.initial_distance_table(ds.n, edge_list(ds))  # fresh starting table, untimed
    t0 = time.perf_counter()
    pure.floyd_warshall_sweeps(dist)
    algo = time.perf_counter() - t0
    pure.check_no_negative_cycle(dist)
    summary = Summary()
    for i, row in enumerate(dist):
        summary.add_rows(np.asarray(row, dtype=float)[np.newaxis, :], np.array([i]))
    return summary, algo


# (tier, algo) -> (prepare, run). prepare=None means run() takes the Dataset itself and builds its
# own starting table each time (Floyd-Warshall overwrites it, so it can't be reused).
ALGORITHMS = {
    ("scipy", "dijkstra"): (prepare_scipy, run_scipy_dijkstra),
    ("scipy", "floyd_warshall"): (prepare_scipy, run_scipy_floyd_warshall),
    ("numpy", "floyd_warshall"): (None, run_numpy_floyd_warshall),
    ("pure", "dijkstra"): (prepare_pure_dijkstra, run_pure_dijkstra),
    ("pure", "floyd_warshall"): (None, run_pure_floyd_warshall),
}


def measure(slug, tier, algo, processed_dir, sample=None, seed=0):
    """sample=K (Dijkstra only): solve K random sources (fixed seed) instead of all n. The caller
    scales the time by n / K to estimate the full run; the summary then covers the sample only."""
    ds = load_processed(slug, processed_dir)
    prepare, run = ALGORITHMS[(tier, algo)]
    state = prepare(ds) if prepare else ds
    if sample:
        if algo != "dijkstra":
            raise ValueError("sampling sources only makes sense for Dijkstra")
        chosen = np.sort(np.random.default_rng(seed).choice(ds.n, size=sample, replace=False))
        run = functools.partial(run, sources=chosen.tolist())
    baseline = peak_rss_bytes()  # data loaded and input built, before any algorithm run

    def timed_run():
        t0 = time.perf_counter()
        summary, algo_s = run(state)
        return summary, algo_s, time.perf_counter() - t0

    summary, algo_s, total_s = timed_run()
    algo_times, total_times, warmup = [algo_s], [total_s], False
    if total_s < SHORT_RUN_S:  # short: that run was the warm-up; now time REPEATS more
        warmup, algo_times, total_times = True, [], []
        for _ in range(REPEATS):
            summary, algo_s, total_s = timed_run()
            algo_times.append(algo_s)
            total_times.append(total_s)

    return {
        "status": "ok", "n": ds.n, "m": int(len(ds.u)), "sources": sample or ds.n,
        "warmup": warmup, "repeats": len(algo_times),
        "algo_times_s": algo_times, "total_times_s": total_times,
        "baseline_rss_bytes": baseline, "peak_rss_bytes": peak_rss_bytes(),
        **summary.as_dict(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("tier")
    parser.add_argument("algo")
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--sample", type=int, default=None, help="Dijkstra: solve K random sources")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    result = measure(args.slug, args.tier, args.algo, args.processed_dir, args.sample, args.seed)
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
