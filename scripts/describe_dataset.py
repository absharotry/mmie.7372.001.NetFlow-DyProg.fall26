"""Describe datasets: characteristics table, most connected nodes, degree and weight distributions.

    python scripts/describe_dataset.py               # all datasets
    python scripts/describe_dataset.py wikiconflict  # just one

Structure is measured on the PROCESSED graph (what the algorithms see); weights are summarized for
both the raw data and the processed distances. Writes results/characteristics_<slug>.csv and
results/distributions_<slug>.png.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from apsp.characteristics import describe, describe_weights, structure_matrix
from apsp.loaders import compact_ids
from apsp.preprocess import PIPELINES, build

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def ccdf(x):
    """Complementary CDF: for each value k, the fraction of items with value >= k.
    On log-log axes a straight-ish line suggests a heavy tail (a few huge hubs)."""
    xs = np.sort(x[x > 0])
    return xs, 1.0 - np.arange(len(xs)) / len(xs)


def fmt(val):
    if isinstance(val, bool):  # check bool first: in Python, True is also an int
        return "yes" if val else "no"
    if isinstance(val, (float, np.floating)):
        return f"{val:,.4g}"
    if isinstance(val, (int, np.integer)):
        return f"{val:,}"
    return val


def describe_one(slug):
    raw, ds = build(slug)
    info = describe(ds) | describe_weights(raw.w, "raw weight") | describe_weights(ds.w, "distance")

    print(f"\n=== {ds.name} ===")
    print(f"source:   {ds.source}")
    print(f"raw:      {raw.weight_meaning}  (n = {raw.n:,}, {len(raw.u):,} rows)")
    print(f"distance: {ds.weight_meaning}\n")
    for key, val in info.items():
        print(f"  {key:<30} {fmt(val)}")

    # --- Most connected nodes ---------------------------------------------------------------------
    adj = structure_matrix(ds.n, ds.u, ds.v, ds.directed)
    deg = np.diff(adj.indptr)
    names = np.array(ds.labels) if ds.labels is not None else np.array([f"#{i}" for i in range(ds.n)])
    top = np.argsort(-deg)[:10]
    table = pd.DataFrame({"node": names[top], "degree" if not ds.directed else "out-degree": deg[top]},
                         index=range(1, 11))
    if slug == "wikiconflict":
        # raw ids differ from processed ids (D2b renumbering), so match through the raw rows:
        # share of each top editor's interactions that were disagreements.
        share = negative_share_by_node(raw, ds.n)
        table["negative share"] = [f"{share[i]:.0%}" for i in top]
    print("\nMost connected nodes:")
    print(table.to_string())
    if ds.directed:
        in_deg = np.bincount(adj.indices, minlength=ds.n)
        top_in = np.argsort(-in_deg)[:10]
        print("\nMost pointed-to nodes:")
        print(pd.DataFrame({"node": names[top_in], "in-degree": in_deg[top_in]},
                           index=range(1, 11)).to_string())

    # --- Figure ---------------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    if ds.directed:
        series = [(deg, "out-degree"), (np.bincount(adj.indices, minlength=ds.n), "in-degree")]
    else:
        series = [(deg, "degree")]
    for d, label in series:
        axes[0].loglog(*ccdf(d), marker=".", linestyle="none", label=label, alpha=0.7)
    axes[0].set(xlabel="degree k", ylabel="fraction of nodes with degree >= k",
                title="Degree distribution (CCDF)")
    axes[0].legend()
    if (raw.w > 0).all() and raw.w.max() / raw.w.min() > 100:  # wide range: log scale
        axes[1].hist(np.log10(raw.w), bins=40, color="#4c72b0")
        axes[1].set(xlabel="log10(raw weight)")
    elif (raw.w > 0).all():  # a few small values (e.g. 1..6): one bar per value
        values, counts = np.unique(raw.w, return_counts=True)
        axes[1].bar(values, counts, color="#4c72b0")
        axes[1].set(xlabel=f"raw weight ({raw.weight_meaning})")
    else:
        axes[1].hist(raw.w, bins=80, color="#4c72b0")
        axes[1].axvline(0, color="black", linewidth=0.8)
        axes[1].set(xlabel=f"raw weight ({raw.weight_meaning})")
    axes[1].set(ylabel="number of edge rows", title="Raw weight distribution")
    fig.suptitle(ds.name)
    fig.tight_layout()

    RESULTS_DIR.mkdir(exist_ok=True)
    fig.savefig(RESULTS_DIR / f"distributions_{slug}.png", dpi=150)
    plt.close(fig)
    pd.Series({k: fmt(v) for k, v in info.items()}).to_csv(
        RESULTS_DIR / f"characteristics_{slug}.csv", header=["value"])
    print(f"\nSaved results/characteristics_{slug}.csv and results/distributions_{slug}.png")


def negative_share_by_node(raw, n):
    """For each PROCESSED node id: share of its raw interaction rows with a negative weight.

    drop_isolated numbers nodes by first appearance; calling compact_ids on the raw rows reproduces
    exactly that numbering, so the result lines up with the processed ids."""
    u, v, _ = compact_ids(raw.u, raw.v)
    neg = raw.w < 0
    total = np.bincount(u, minlength=n) + np.bincount(v, minlength=n)
    negative = np.bincount(u, weights=neg, minlength=n) + np.bincount(v, weights=neg, minlength=n)
    return negative / total


def main():
    for slug in sys.argv[1:] or PIPELINES:
        describe_one(slug)


if __name__ == "__main__":
    main()
