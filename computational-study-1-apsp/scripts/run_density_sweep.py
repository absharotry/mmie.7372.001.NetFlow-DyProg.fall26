"""Density experiment (Phase 5): fixed n, increasing density, both algorithms.

    python scripts/run_density_sweep.py          # generate graphs + run (about 15-20 min)
    python scripts/run_density_sweep.py --plot   # only redraw the figure from the CSV

Each measurement uses the same harness as the real datasets (apsp.bench: fresh process, warm-up +
5 repeats for short runs, single thread). Graphs are saved to data/processed/ (regenerated
deterministically from the seed, so not committed). Results: results/density_sweep.csv,
results/fig_density_crossover.png.
"""

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from apsp.bench import append_row, run_one
from apsp.preprocess import save_processed
from apsp.synthetic import random_digraph, slug

RESULTS = Path(__file__).resolve().parent.parent / "results"
CSV = RESULTS / "density_sweep.csv"
SEED = 2026
TIMEOUT_S = 1800
DENSITIES = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
# (tier, n): scipy at two sizes; pure Python at a small size because it is ~100x slower.
SETTINGS = [("scipy", 1000), ("scipy", 2000), ("pure", 400)]

BLUE, ORANGE, AQUA, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b", "#52514e", "#e4e3df"


def run():
    for tier, n in SETTINGS:
        for p in DENSITIES:
            s = slug(n, p)
            save_processed(random_digraph(n, p, seed=SEED), s)
            for algo in ("dijkstra", "floyd_warshall"):
                print(f"{tier:<6} n={n:<5} p={p:<6} {algo:<15}", end=" ", flush=True)
                row = run_one(s, tier, algo, TIMEOUT_S) | {"density_target": p, "seed": SEED}
                append_row(row, CSV)
                if row["status"] == "ok":
                    print(f"{row['algo_median_s']:9.3f} s  (m={row['m']:,}, median of {row['repeats']})",
                          flush=True)
                else:
                    print(f"{row['status'].upper()}: {row['reason']}", flush=True)


def crossover(d):
    """Density where FW/Dijkstra crosses 1, by log-log interpolation between neighbouring points."""
    d = d.sort_values("density")
    x, r = np.log(d.density.to_numpy()), np.log(d.ratio.to_numpy())
    for i in range(len(r) - 1):
        if r[i] > 0 >= r[i + 1]:
            return float(np.exp(x[i] + (0 - r[i]) * (x[i + 1] - x[i]) / (r[i + 1] - r[i])))
    return None


def ratios():
    df = pd.read_csv(CSV)
    df = df[df.status == "ok"].sort_values("timestamp")
    df = df.groupby(["tier", "n", "density_target", "algo"], as_index=False).last()
    wide = df.pivot_table(index=["tier", "n", "density_target"], columns="algo",
                          values="algo_median_s").reset_index()
    m = df[df.algo == "dijkstra"].set_index(["tier", "n", "density_target"]).m
    wide["m"] = wide.set_index(["tier", "n", "density_target"]).index.map(m)
    wide["density"] = wide.m / (wide.n * (wide.n - 1))  # actual, not target
    wide["ratio"] = wide.floyd_warshall / wide.dijkstra
    return wide


def plot():
    w = ratios()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    styles = {("scipy", 1000): (BLUE, "-", "o"), ("scipy", 2000): (ORANGE, "-", "s"),
              ("pure", 400): (AQUA, ":", "^")}
    lines = []
    for (tier, n), (color, ls, mk) in styles.items():
        d = w[(w.tier == tier) & (w.n == n)].sort_values("density")
        if d.empty:
            continue
        c = crossover(d)
        label = f"{tier}, n = {n:,}" + (f": crossover at {c:.0%} density" if c else "")
        ax.plot(d.density, d.ratio, color=color, linestyle=ls, marker=mk, linewidth=2, markersize=8,
                markeredgecolor="white", markeredgewidth=1.5, label=label)
        if c:  # hollow marker where the line crosses "equal speed"
            ax.plot([c], [1], marker="o", markersize=11, markerfacecolor="none",
                    markeredgecolor=color, markeredgewidth=2, linestyle="none")
        lines.append((tier, n, c))
    # Step-count theory for n = 2000 with a binary heap: n^3 / (n m log2 n) = 1 / (p log2 n).
    p = np.logspace(-3, 0, 50)
    ax.plot(p, 1 / (p * math.log2(2000)), color=MUTED, linestyle="--", linewidth=1.5,
            label="step-count theory, n = 2,000: 1 / (p log2 n)")
    ax.axhline(1, color=MUTED, linewidth=1)
    ax.annotate("Dijkstra faster", (1.1e-3, 1), xytext=(0, 6), textcoords="offset points",
                color=MUTED, fontsize=8)
    ax.annotate("Floyd-Warshall faster", (1.1e-3, 1), xytext=(0, -12), textcoords="offset points",
                color=MUTED, fontsize=8)
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 0.08), frameon=False, fontsize=9)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(8e-4, 1.3)
    ax.set_xlabel("density m / (n(n-1))  (log scale)", color=INK)
    ax.set_ylabel("Floyd-Warshall time / Dijkstra time  (log scale)", color=INK)
    ax.set_title("Random networks, fixed n: where does Floyd-Warshall start to win?",
                 color=INK, fontsize=11, loc="left")
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_density_crossover.png", dpi=150)
    plt.close(fig)
    w.to_csv(RESULTS / "density_ratios.csv", index=False)
    for tier, n, c in lines:
        print(f"{tier:<6} n={n:<5} crossover density: {'none in range' if c is None else f'{c:.2%}'}")


if __name__ == "__main__":
    if "--plot" not in sys.argv:
        run()
    plot()
