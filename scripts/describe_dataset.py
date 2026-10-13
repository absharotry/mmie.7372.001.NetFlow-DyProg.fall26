"""Describe a dataset: characteristics table, busiest nodes/edges, degree and weight distributions.

    python scripts/describe_dataset.py

Writes results/characteristics_<name>.csv and results/distributions_<name>.png.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from apsp.characteristics import describe, structure_matrix
from apsp.loaders import load_usairport

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def ccdf(x):
    """Complementary CDF: for each value k, the fraction of items with value >= k.
    On log-log axes a straight-ish line suggests a heavy tail (a few huge hubs)."""
    xs = np.sort(x[x > 0])
    return xs, 1.0 - np.arange(len(xs)) / len(xs)


def main():
    ds = load_usairport()
    slug = "usairport"
    info = describe(ds)

    print(f"=== {ds.name} ===")
    print(f"source: {ds.source}")
    print(f"weight: {ds.weight_meaning}\n")
    for key, val in info.items():
        if isinstance(val, bool):  # check bool first: in Python, True is also an int
            shown = "yes" if val else "no"
        elif isinstance(val, float):
            shown = f"{val:,.4g}"
        elif isinstance(val, (int, np.integer)):
            shown = f"{val:,}"
        else:
            shown = val
        print(f"  {key:<26} {shown}")

    labels = np.array(ds.labels)
    adj = structure_matrix(ds.n, ds.u, ds.v)
    out_deg = np.diff(adj.indptr)
    passengers_out = np.bincount(ds.u, weights=ds.w, minlength=ds.n)  # "strength" of each node

    print("\nTop 10 airports by number of destinations (out-degree) and by passengers departing:")
    top = pd.DataFrame({
        "by destinations": [f"{labels[i]} ({out_deg[i]})" for i in np.argsort(-out_deg)[:10]],
        "by passengers": [f"{labels[i]} ({passengers_out[i] / 1e6:.1f}M)"
                          for i in np.argsort(-passengers_out)[:10]],
    }, index=range(1, 11))
    print(top.to_string())

    print("\nTop 5 routes by passengers:")
    for e in np.argsort(-ds.w)[:5]:
        print(f"  {labels[ds.u[e]]} -> {labels[ds.v[e]]}: {ds.w[e]:,.0f}")

    print("\nAirports with no departing routes (first 10):",
          ", ".join(labels[out_deg == 0][:10]))

    # --- Figure: degree and weight distributions -------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for deg, name in [(out_deg, "out-degree"), (np.bincount(adj.indices, minlength=ds.n), "in-degree")]:
        axes[0].loglog(*ccdf(deg), marker=".", linestyle="none", label=name, alpha=0.7)
    axes[0].set(xlabel="degree k", ylabel="fraction of airports with degree >= k",
                title="Degree distribution (CCDF)")
    axes[0].legend()
    axes[1].hist(np.log10(ds.w), bins=40, color="#4c72b0")
    axes[1].set(xlabel="log10(passengers on route)", ylabel="number of routes",
                title="Edge weight distribution")
    fig.suptitle(ds.name)
    fig.tight_layout()

    RESULTS_DIR.mkdir(exist_ok=True)
    fig.savefig(RESULTS_DIR / f"distributions_{slug}.png", dpi=150)
    pd.Series(info).to_csv(RESULTS_DIR / f"characteristics_{slug}.csv", header=["value"])
    print(f"\nSaved results/characteristics_{slug}.csv and results/distributions_{slug}.png")


if __name__ == "__main__":
    main()
