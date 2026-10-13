"""Turn results/benchmarks.csv into report tables and figures.

    python scripts/make_report.py

Writes results/report_tables.md, results/fig_time_vs_n.png, results/fig_ratio_vs_n.png.
Uses the latest row for each (dataset, tier, algo), so re-runs replace older measurements.
"""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

DATASETS = {"usairport": "US Airports", "health": "Adolescent Health", "advogato": "Advogato",
            "slashdot": "Slashdot Zoo", "wikiconflict": "Wiki Conflict"}
VERSIONS = [("scipy", "dijkstra"), ("scipy", "floyd_warshall"), ("numpy", "floyd_warshall"),
            ("pure", "dijkstra"), ("pure", "floyd_warshall")]
LABEL = {("scipy", "dijkstra"): "scipy Dijkstra", ("scipy", "floyd_warshall"): "scipy FW",
         ("numpy", "floyd_warshall"): "numpy FW", ("pure", "dijkstra"): "pure Dijkstra",
         ("pure", "floyd_warshall"): "pure FW"}

# Color = algorithm (identity), line style + marker = implementation tier.
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"
COLOR = {"dijkstra": BLUE, "floyd_warshall": ORANGE}
STYLE = {"scipy": ("-", "o"), "numpy": ("--", "s"), "pure": (":", "^")}
FIT_FROM = "advogato"  # largest dataset where every version ran: used to calibrate predictions


def load():
    """Latest FULL run per (dataset, tier, algo), plus the latest SAMPLED run (Dijkstra on a random
    subset of sources) separately. Rows from before sampling existed have no "sources": full runs."""
    df = pd.read_csv(RESULTS / "benchmarks.csv")
    if "sources" not in df:
        df["sources"] = np.nan
    sampled = df.sources.notna() & (df.sources < df.n)
    keys = ["dataset", "tier", "algo"]
    full = df[~sampled].sort_values("timestamp").groupby(keys, as_index=False).last()
    samples = df[sampled & (df.status == "ok")].sort_values("timestamp").groupby(keys, as_index=False).last()
    for frame in (full, samples):
        frame["order"] = frame["dataset"].map(list(DATASETS).index)
    return full.sort_values("order"), samples.sort_values("order")


def steps(algo, n, m):
    """Theoretical step counts: n^3 for FW, n * m * log2(n) for n x Dijkstra (binary heap)."""
    return n**3 if algo == "floyd_warshall" else n * m * math.log2(n)


def fmt_s(seconds):
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 120:
        return f"{seconds:.2f} s"
    if seconds < 7200:
        return f"{seconds / 60:.1f} min"
    if seconds < 3 * 86400:
        return f"{seconds / 3600:.1f} h"
    return f"{seconds / 86400:.0f} days"


def predictions(df):
    """Per version: seconds per theoretical step, calibrated on FIT_FROM, then predicted time
    = that constant x steps(n, m) for every dataset."""
    rows = []
    for tier, algo in VERSIONS:
        cal = df[(df.dataset == FIT_FROM) & (df.tier == tier) & (df.algo == algo) & (df.status == "ok")]
        if cal.empty:
            continue
        c = cal.algo_median_s.iloc[0] / steps(algo, cal.n.iloc[0], cal.m.iloc[0])
        for _, r in df[(df.tier == tier) & (df.algo == algo)].iterrows():
            rows.append({"dataset": r.dataset, "tier": tier, "algo": algo, "n": r.n, "m": r.m,
                         "ns_per_step": c * 1e9, "predicted_s": c * steps(algo, r.n, r.m),
                         "measured_s": r.algo_median_s if r.status == "ok" else np.nan,
                         "status": r.status})
    return pd.DataFrame(rows)


def reachable_model(df, r):
    """FW time ~ c x n x (reachable ordered pairs), calibrated on FIT_FROM in the same tier."""
    if r.algo != "floyd_warshall":
        return "-"
    cal = df[(df.dataset == FIT_FROM) & (df.tier == r.tier) & (df.algo == r.algo) & (df.status == "ok")]
    dj = df[(df.dataset == r.dataset) & (df.algo == "dijkstra") & (df.status == "ok")]
    if cal.empty or dj.empty:
        return "-"
    c = cal.algo_median_s.iloc[0] / (cal.n.iloc[0] * cal.reachable_pairs.iloc[0])
    return fmt_s(c * r.n * dj.reachable_pairs.iloc[0])


def tables(df, pred, samples):
    out = []
    first = df.iloc[0]
    out.append("## Machine\n")
    out.append(f"{first.cpu}, {first.ram_gib:g} GiB RAM, {first.os}; Python {first.python}, "
               f"numpy {first.numpy}, scipy {first.scipy}. Single thread.\n")

    out.append("## Table 1. Algorithm time (median), by dataset and version\n")
    head = "| Dataset | n | m | " + " | ".join(LABEL[v] for v in VERSIONS) + " |"
    out += [head, "|" + "---|" * (3 + len(VERSIONS))]
    for slug, name in DATASETS.items():
        d = df[df.dataset == slug]
        if d.empty:
            continue
        cells = []
        for tier, algo in VERSIONS:
            r = d[(d.tier == tier) & (d.algo == algo)]
            smp = samples[(samples.dataset == slug) & (samples.tier == tier) & (samples.algo == algo)]
            if (r.empty or r.status.iloc[0] != "ok") and len(smp):
                k = int(smp.sources.iloc[0])
                cells.append(f"~{fmt_s(smp.algo_full_estimate_s.iloc[0])} (est. from {k:,} sources)")
            elif r.empty:
                cells.append("not run")
            elif r.status.iloc[0] == "ok":
                reps = int(r.repeats.iloc[0])
                cells.append(f"{fmt_s(r.algo_median_s.iloc[0])}" + ("" if reps > 1 else " (1 run)"))
            else:
                cells.append(f"**{r.status.iloc[0]}**")
        out.append(f"| {name} | {d.n.iloc[0]:,} | {d.m.iloc[0]:,} | " + " | ".join(cells) + " |")

    out.append("\n## Table 2. Floyd-Warshall time / Dijkstra time\n")
    out += ["| Dataset | Theory n^3 / (n m log2 n) | scipy (measured) | pure (measured) |",
            "|---|---|---|---|"]
    for slug, name in DATASETS.items():
        d = df[(df.dataset == slug) & (df.status == "ok")]
        if d.empty:
            continue
        n, m = d.n.iloc[0], d.m.iloc[0]
        cells = []
        for tier in ("scipy", "pure"):
            fw = d[(d.tier == tier) & (d.algo == "floyd_warshall")]
            dj = d[(d.tier == tier) & (d.algo == "dijkstra")]
            cells.append(f"{fw.algo_median_s.iloc[0] / dj.algo_median_s.iloc[0]:.1f}x"
                         if len(fw) and len(dj) else "-")
        out.append(f"| {name} | {steps('floyd_warshall', n, m) / steps('dijkstra', n, m):.1f}x | "
                   + " | ".join(cells) + " |")

    out.append("\n## Table 3. Peak memory (MiB): measured, and the n x n table it implies\n")
    out += ["| Dataset | Version | Peak RSS | Baseline (before algorithm) | Peak - baseline "
            "| n^2 x 8 bytes |", "|---|---|---|---|---|---|"]
    for _, r in df[df.status == "ok"].iterrows():
        out.append(f"| {DATASETS[r.dataset]} | {LABEL[(r.tier, r.algo)]} | {r.peak_rss_mib:,.0f} | "
                   f"{r.baseline_rss_mib:,.0f} | {r.peak_rss_mib - r.baseline_rss_mib:,.0f} | "
                   f"{8 * r.n**2 / 2**20:,.0f} |")

    out.append("\n## Table 4. Runs not performed\n")
    out.append("Predicted FW time, two models calibrated on " + DATASETS[FIT_FROM] + ": (1) n^3 steps; "
               "(2) n x reachable pairs, because scipy's FW skips node pairs (i, k) where i cannot "
               "reach k. Reachable pairs come from the Dijkstra run on the same dataset.\n")
    out += ["| Dataset | Version | Status | Reason | Predicted: n^3 model | Predicted: n x reachable model |",
            "|---|---|---|---|---|---|"]
    for _, r in df[df.status != "ok"].iterrows():
        p = pred[(pred.dataset == r.dataset) & (pred.tier == r.tier) & (pred.algo == r.algo)]
        guess = fmt_s(p.predicted_s.iloc[0]) if len(p) else "-"
        reach = reachable_model(df, r)
        out.append(f"| {DATASETS[r.dataset]} | {LABEL[(r.tier, r.algo)]} | {r.status} | "
                   f"{r.reason} | {guess} | {reach} |")

    out.append(f"\n## Table 5. Step-count model: calibrated on {DATASETS[FIT_FROM]}, "
               "checked on the others\n")
    out += ["| Version | ns per step | Dataset | Predicted | Measured | Measured / predicted |",
            "|---|---|---|---|---|---|"]
    for _, r in pred.iterrows():
        meas = "" if np.isnan(r.measured_s) else fmt_s(r.measured_s)
        ratio = "" if np.isnan(r.measured_s) else f"{r.measured_s / r.predicted_s:.2f}"
        out.append(f"| {LABEL[(r.tier, r.algo)]} | {r.ns_per_step:.3g} | {DATASETS[r.dataset]} | "
                   f"{fmt_s(r.predicted_s)} | {meas} | {ratio} |")

    out.append("\n## Table 6. Correctness: every version must agree\n")
    out += ["| Dataset | Versions run | Reachable pairs (all equal?) | Mean distance (max relative "
            "spread) | Max distance |", "|---|---|---|---|---|"]
    for slug, name in DATASETS.items():
        d = df[(df.dataset == slug) & (df.status == "ok")]
        if d.empty:
            continue
        same = d.reachable_pairs.nunique() == 1
        spread = (d.mean_distance.max() - d.mean_distance.min()) / d.mean_distance.mean()
        out.append(f"| {name} | {len(d)} | {int(d.reachable_pairs.iloc[0]):,} "
                   f"({'yes' if same else 'NO'}) | {d.mean_distance.iloc[0]:.6g} ({spread:.1e}) | "
                   f"{d.max_distance.iloc[0]:.6g} |")
    return "\n".join(out) + "\n"


def style_axes(ax):
    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED)


def fig_time_vs_n(df, pred, samples):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for tier, algo in VERSIONS:
        d = df[(df.tier == tier) & (df.algo == algo) & (df.status == "ok")].sort_values("n")
        if d.empty:
            continue
        ls, mk = STYLE[tier]
        ax.plot(d.n, d.algo_median_s, linestyle=ls, marker=mk, color=COLOR[algo], linewidth=2,
                markersize=8, markeredgecolor="white", markeredgewidth=1.5)
        below = (tier, algo) == ("pure", "dijkstra")  # avoid colliding with the scipy Dijkstra label
        ax.annotate(LABEL[(tier, algo)], (d.n.iloc[-1], d.algo_median_s.iloc[-1]),
                    xytext=(0, -14) if below else (8, 0), textcoords="offset points",
                    ha="center" if below else "left", va="center", color=INK, fontsize=9)
    # Predicted (not measured) FW times for datasets where it could not run: hollow markers.
    p = pred[(pred.algo == "floyd_warshall") & (pred.tier == "scipy") & (pred.status != "ok")]
    if len(p):
        ax.plot(p.n, p.predicted_s, linestyle="none", marker="o", markersize=9,
                markerfacecolor="none", markeredgecolor=ORANGE, markeredgewidth=2)
        for _, r in p.iterrows():
            full = df[(df.dataset == r.dataset) & (df.tier == "scipy") & (df.algo == "floyd_warshall")].iloc[0]
            ax.annotate(f"scipy FW, predicted {fmt_s(r.predicted_s)} (n^3 model)\n"
                        f"or {reachable_model(df, full)} (reachable-pairs model); does not fit in RAM",
                        (r.n, r.predicted_s), xytext=(-10, 0), textcoords="offset points",
                        ha="right", va="center", color=MUTED, fontsize=8)
    for _, r in samples.iterrows():  # estimated from a sample of sources: hollow marker
        ls, mk = STYLE[r.tier]
        ax.plot([r.n], [r.algo_full_estimate_s], linestyle="none", marker=mk, markersize=10,
                markerfacecolor="none", markeredgecolor=COLOR[r.algo], markeredgewidth=2)
        ax.annotate(f"{LABEL[(r.tier, r.algo)]}, estimated\n(from {int(r.sources):,} sources: "
                    f"{fmt_s(r.algo_full_estimate_s)})", (r.n, r.algo_full_estimate_s),
                    xytext=(-10, 0), textcoords="offset points", ha="right", va="center",
                    color=MUTED, fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("number of nodes n (log scale)", color=INK)
    ax.set_ylabel("algorithm time, seconds (log scale)", color=INK)
    ax.set_title("All-pairs shortest paths: time vs network size\n"
                 "blue = n x Dijkstra, orange = Floyd-Warshall; solid scipy, dashed numpy, "
                 "dotted pure Python", color=INK, fontsize=11, loc="left")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_time_vs_n.png", dpi=150)
    plt.close(fig)


def fig_ratio_vs_n(df):
    fig, ax = plt.subplots(figsize=(8, 5))
    rows = []
    for slug in DATASETS:
        d = df[(df.dataset == slug) & (df.status == "ok")]
        if d.empty:
            continue
        n, m = d.n.iloc[0], d.m.iloc[0]
        row = {"n": n, "theory": steps("floyd_warshall", n, m) / steps("dijkstra", n, m)}
        for tier in ("scipy", "pure"):
            fw = d[(d.tier == tier) & (d.algo == "floyd_warshall")]
            dj = d[(d.tier == tier) & (d.algo == "dijkstra")]
            row[tier] = (fw.algo_median_s.iloc[0] / dj.algo_median_s.iloc[0]
                         if len(fw) and len(dj) else np.nan)
        rows.append(row)
    r = pd.DataFrame(rows).dropna(subset=["scipy"]).sort_values("n")
    series = [("theory", "theory: n^3 / (n m log2 n)", MUTED, "--", "D"),
              ("scipy", "measured, scipy", ORANGE, "-", "o"),
              ("pure", "measured, pure Python", ORANGE, ":", "^")]
    for key, label, color, ls, mk in series:
        ax.plot(r.n, r[key], linestyle=ls, marker=mk, color=color, linewidth=2, markersize=8,
                markeredgecolor="white", markeredgewidth=1.5)
        ax.annotate(label, (r.n.iloc[-1], r[key].iloc[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=9)
    ax.axhline(1, color=MUTED, linewidth=1)
    ax.annotate("above 1: Dijkstra is faster", (r.n.min(), 1), xytext=(0, 6),
                textcoords="offset points", color=MUTED, fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("number of nodes n (log scale)", color=INK)
    ax.set_ylabel("Floyd-Warshall time / Dijkstra time (log scale)", color=INK)
    ax.set_title("How many times slower Floyd-Warshall is, per implementation",
                 color=INK, fontsize=11, loc="left")
    ax.set_xlim(r.n.min() / 1.3, r.n.max() * 2.2)  # room for the direct labels
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(RESULTS / "fig_ratio_vs_n.png", dpi=150)
    plt.close(fig)


def main():
    df, samples = load()
    pred = predictions(df)
    (RESULTS / "report_tables.md").write_text(tables(df, pred, samples))
    fig_time_vs_n(df, pred, samples)
    fig_ratio_vs_n(df)
    print("Wrote results/report_tables.md, results/fig_time_vs_n.png, results/fig_ratio_vs_n.png")


if __name__ == "__main__":
    main()
