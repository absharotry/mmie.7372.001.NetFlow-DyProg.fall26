"""Benchmark runner: feasibility pre-check, one fresh worker process per measurement, CSV output.

The measurement itself lives in apsp.bench_worker. This module decides WHETHER to run it, runs it
with a time limit, and records the outcome:
    ok          measured
    infeasible  not attempted: the memory estimate exceeds the budget (reason says by how much)
    timeout     stopped at the time limit
    error       the worker failed (reason holds the last line of its error output)
"""

import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import scipy

from apsp.preprocess import PROCESSED_DIR, load_processed

RESULTS_CSV = Path(__file__).resolve().parents[2] / "results" / "benchmarks.csv"
MEMORY_FRACTION = 0.6  # use at most 60% of RAM, leaving room for the OS and the input data
GIB = 2**30

# Bytes needed per cell of the n x n distance table, by implementation (Floyd-Warshall only;
# Dijkstra streams, so it never holds the full table).
FW_BYTES_PER_CELL = {
    "scipy": 8,  # one float64 table
    "numpy": 16,  # the table plus one temporary table per sweep (via_k)
    "pure": 32,  # Python list slot (8) + a float object (24) per cell, worst case
}


def estimate_memory_bytes(tier, algo, n, m):
    """Rough peak-memory model. Checked against measured peak RSS on the small datasets."""
    if algo == "floyd_warshall":
        return FW_BYTES_PER_CELL[tier] * n * n
    # Dijkstra: the graph (generous ~250 bytes per edge, covering the Python edge list built while
    # loading) plus one streamed batch of rows (at most 256 MiB).
    return 250 * m + 256 * 2**20


def feasibility(tier, algo, n, m, ram_bytes):
    """Return (feasible, estimate_bytes, reason)."""
    need = estimate_memory_bytes(tier, algo, n, m)
    budget = MEMORY_FRACTION * ram_bytes
    if need <= budget:
        return True, need, ""
    return False, need, (f"needs ~{need / GIB:,.1f} GiB, budget {budget / GIB:,.1f} GiB "
                         f"({MEMORY_FRACTION:.0%} of {ram_bytes / GIB:,.0f} GiB RAM)")


def machine_info():
    cpu = platform.processor()
    if sys.platform == "darwin":
        try:
            cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True,
                                 text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    return {"cpu": cpu, "ram_gib": round(psutil.virtual_memory().total / GIB, 1),
            "os": platform.platform(), "python": platform.python_version(),
            "numpy": np.__version__, "scipy": scipy.__version__}


def run_one(slug, tier, algo, timeout_s, processed_dir=PROCESSED_DIR, ram_bytes=None):
    """Run (or refuse) one measurement and return one result row as a dict."""
    ds = load_processed(slug, processed_dir)
    n, m = ds.n, int(len(ds.u))
    ram_bytes = ram_bytes or psutil.virtual_memory().total
    ok, need, reason = feasibility(tier, algo, n, m, ram_bytes)
    row = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "dataset": slug, "n": n, "m": m,
           "tier": tier, "algo": algo, "status": "infeasible", "reason": reason,
           "est_memory_gib": round(need / GIB, 3), "timeout_s": timeout_s}
    if ok:
        row |= _run_worker(slug, tier, algo, timeout_s, processed_dir)
    return row | machine_info()


def _run_worker(slug, tier, algo, timeout_s, processed_dir):
    cmd = [sys.executable, "-m", "apsp.bench_worker", slug, tier, algo,
           "--processed-dir", str(processed_dir)]
    env = os.environ | {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, env=env)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "reason": f"stopped after {timeout_s:,} s",
                "wall_s": round(time.perf_counter() - t0, 1)}
    wall = round(time.perf_counter() - t0, 1)
    if proc.returncode != 0:
        last = (proc.stderr.strip().splitlines() or ["(no error output)"])[-1]
        return {"status": "error", "reason": last[:300], "wall_s": wall}
    r = json.loads(proc.stdout.strip().splitlines()[-1])
    algo_t, total_t = r.pop("algo_times_s"), r.pop("total_times_s")
    r.pop("n"), r.pop("m")
    return r | {
        "reason": "", "wall_s": wall,
        "algo_median_s": statistics.median(algo_t), "algo_min_s": min(algo_t),
        "total_median_s": statistics.median(total_t),
        "algo_times_s": " ".join(f"{t:.6g}" for t in algo_t),
        "peak_rss_mib": round(r.pop("peak_rss_bytes") / 2**20, 1),
        "baseline_rss_mib": round(r.pop("baseline_rss_bytes") / 2**20, 1),
    }


def append_row(row, path=RESULTS_CSV):
    """Append one row to the results CSV (header written on first use). Rows are appended one at a
    time so a long batch keeps everything finished so far, even if it is interrupted."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([row])
    if path.exists():
        existing = pd.read_csv(path, nrows=0).columns.tolist()
        frame = frame.reindex(columns=existing + [c for c in frame.columns if c not in existing])
        if list(frame.columns) != existing:  # new column appeared: rewrite with the wider header
            pd.concat([pd.read_csv(path), frame]).to_csv(path, index=False)
            return
        frame.to_csv(path, mode="a", header=False, index=False)
    else:
        frame.to_csv(path, index=False)
