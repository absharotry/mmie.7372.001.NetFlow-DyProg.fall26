"""Phase 6: apply the winner rule to the 30 shuffled door orders, gather the prediction evidence, draw R6.

Run from the project folder after scripts/run_shuffles.py:

    python scripts/compare_orders.py

Writes results/winners.csv (13 cases x 2 pairs x 2 measures = 52 verdicts),
results/prediction_evidence.csv (the numbers behind P1 to P7) and docs/figures/r6_shuffle_ratios.png.
The traced runs for P2 and P5 are separate, untimed runs; they do not touch the timing results.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from maxflow.instance import DENSE, DIRECTED, SPARSE, TWO_WAY, read_instance  # noqa: E402
from maxflow.preflow import FIFO, HIGHEST, preflow_push  # noqa: E402
from maxflow.residual import build_residual, shuffle_rooms  # noqa: E402
from maxflow.sap import shortest_augmenting_path  # noqa: E402
from maxflow.winners import decide  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
FLOW_CASES = [(name, DIRECTED) for name in DENSE] + [(name, TWO_WAY) for name in SPARSE]
PAIRS = {"headline": ("SAP", "PP-FIFO"), "tuned": ("SAP+numb", "PP-FIFO+h")}
MEASURES = {"time": "time_median_s", "work": "total_work"}
BLUE, ORANGE, INK, INK2, GRID, BAND = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e1e0d9", "#f1efe8"


def read_rows(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def label(name: str, reading: str) -> str:
    return name if reading == DIRECTED else f"{name} (two-way)"


class Results:
    """Look up one number for (file, reading, setting[, order])."""

    def __init__(self, shuffled: list[dict], baseline: list[dict]):
        self.shuffled = {(r["file"], r["reading"], r["setting"], int(r["arc_order"])): r for r in shuffled}
        self.baseline = {(r["file"], r["reading"], r["setting"]): r for r in baseline}
        self.orders = sorted({int(r["arc_order"]) for r in shuffled})

    def per_order(self, name, reading, setting, column) -> list[float]:
        return [float(self.shuffled[(name, reading, setting, k)][column]) for k in self.orders]

    def base(self, name, reading, setting, column) -> float:
        return float(self.baseline[(name, reading, setting)][column])


def winner_rows(res: Results) -> list[dict]:
    rows = []
    for name, reading in FLOW_CASES:
        for pair, (a, b) in PAIRS.items():
            for measure, column in MEASURES.items():
                v = decide(a, b, res.per_order(name, reading, a, column), res.per_order(name, reading, b, column))
                rows.append({
                    "file": name, "reading": reading, "pair": pair, "measure": measure, "a": a, "b": b,
                    "orders": v.orders, "a_wins": v.a_wins, "b_wins": v.b_wins, "ties": v.ties,
                    "median_ratio_a_over_b": f"{v.median_ratio:.4f}",
                    "file_order_ratio_a_over_b": f"{res.base(name, reading, a, column) / res.base(name, reading, b, column):.4f}",
                    "wilcoxon_p": "" if v.p_value is None else f"{v.p_value:.2e}", "verdict": v.verdict,
                })
    return rows


def evidence(res: Results, winners: list[dict], cards: dict, data_dir: Path) -> list[dict]:
    rows = []

    def add(prediction, name, reading, quantity, value):
        rows.append({"prediction": prediction, "file": name, "reading": reading, "quantity": quantity,
                     "value": value if isinstance(value, str) else f"{value:.4g}"})

    # P1: FIFO beats SAP by a factor rising with m/n (dense files, headline pair, median over orders).
    m_per_n, time_ratio = [], []
    for name in DENSE:
        card = cards[(name, DIRECTED)]
        for measure in MEASURES:
            w = next(r for r in winners if (r["file"], r["reading"], r["pair"], r["measure"]) ==
                     (name, DIRECTED, "headline", measure))
            add("P1", name, DIRECTED, f"{measure}_ratio_SAP_over_FIFO", float(w["median_ratio_a_over_b"]))
            add("P1", name, DIRECTED, f"{measure}_verdict", w["verdict"])
            if measure == "time":
                time_ratio.append(float(w["median_ratio_a_over_b"]))
        m_per_n.append(float(card["m_per_n"]))
        add("P1", name, DIRECTED, "m_per_n", float(card["m_per_n"]))
    add("P1", "all dense", DIRECTED, "spearman_m_per_n_vs_time_ratio", spearmanr(m_per_n, time_ratio).statistic)

    # P2: every SAP group walks at least the shortest route (traced, untimed, file order and all orders).
    for name in DENSE:
        inst = read_instance(data_dir / f"{name}.txt")
        base = build_residual(inst)
        lengths, firsts = [], []
        for order in [None, *res.orders]:
            residual = base if order is None else shuffle_rooms(base, order)
            trace = []
            shortest_augmenting_path(residual, residual.fresh(), trace=trace)
            routes = [len(e[1]) - 1 for e in trace if e[0] == "augment"]
            lengths += routes
            firsts.append(routes[0])
        add("P2", name, DIRECTED, "shortest_route", float(cards[(name, DIRECTED)]["shortest_route"]))
        add("P2", name, DIRECTED, "shortest_group_route_any_order", min(lengths))
        add("P2", name, DIRECTED, "first_group_route_all_orders", "/".join(sorted({str(x) for x in firsts})))
        add("P2", name, DIRECTED, "mean_group_route", statistics.mean(lengths))

    # P3: walk-back work is a large share of preflow-push's effort (dense files, median over orders).
    for name in DENSE:
        card = cards[(name, DIRECTED)]
        flood, flow = float(card["source_flood"]), float(card["max_flow"])
        add("P3", name, DIRECTED, "share_of_flood_walking_back", (flood - flow) / flood)
        for setting in ("PP-FIFO", "PP-FIFO+h"):
            get = lambda column: res.per_order(name, DIRECTED, setting, column)  # noqa: E731
            pushes = [s + n for s, n in zip(get("saturating_pushes"), get("nonsaturating_pushes"))]
            shares = {
                "walkback_share_of_pushes": [w / p for w, p in zip(get("walkback_pushes"), pushes)],
                "walkback_share_of_relabels": [w / r for w, r in zip(get("walkback_relabels"), get("relabels"))],
                "share_of_checks_after_max_preflow": [a / c for a, c in zip(get("checks_after_max_preflow"),
                                                                            get("passages_checked"))],
            }
            for quantity, values in shares.items():
                add("P3", name, DIRECTED, f"{setting} {quantity}", statistics.median(values))

    # P4 and P5: the 8 zero-flow files, at file order.
    zero = [(r["file"], r["reading"]) for r in res.baseline.values() if r["group"] == "zero flow"]
    for name, reading in dict.fromkeys(zero):
        for setting in ("SAP", "SAP+numb"):
            row = res.baseline[(name, reading, setting)]
            held = (row["augmentations"], row["relabels"]) == ("0", "0") and \
                row["passages_checked"] == row["passages_checked_start_search"]
            add("P4", name, reading, f"{setting} no groups, no relabels, only the backward search", str(held))
        inst = read_instance(data_dir / f"{name}.txt")
        neighbours = {inst.s} | {a.head for a in inst.arcs if a.tail == inst.s}
        residual = build_residual(inst)
        for setting, rule, heuristics in (("PP-FIFO", FIFO, False), ("PP-FIFO+h", FIFO, True),
                                          ("PP-HL", HIGHEST, False), ("PP-HL+h", HIGHEST, True)):
            trace = []
            preflow_push(residual, residual.fresh(), rule=rule, heuristics=heuristics, trace=trace)
            touched = {e[1] for e in trace if e[0] in ("push", "relabel")} | \
                      {e[2] for e in trace if e[0] == "push"}
            add("P5", name, reading, f"{setting} rooms worked on", len(touched))
            add("P5", name, reading, f"{setting} only start and its neighbours", str(touched <= neighbours))
        add("P5", name, reading, "start and its neighbours", len(neighbours))

    # P6: highest-label makes fewer non-saturating pushes than FIFO (file order only, as decided).
    for name, reading in FLOW_CASES:
        for fifo, hl in (("PP-FIFO", "PP-HL"), ("PP-FIFO+h", "PP-HL+h")):
            f, h = res.base(name, reading, fifo, "nonsaturating_pushes"), res.base(name, reading, hl, "nonsaturating_pushes")
            add("P6", name, reading, f"{hl} / {fifo} non-saturating pushes", h / f)

    # P7: speed-ups help preflow-push more than SAP (median over orders of as-taught / tuned).
    for name, reading in FLOW_CASES:
        for measure, column in MEASURES.items():
            sap = [x / y for x, y in zip(res.per_order(name, reading, "SAP", column),
                                         res.per_order(name, reading, "SAP+numb", column))]
            pp = [x / y for x, y in zip(res.per_order(name, reading, "PP-FIFO", column),
                                        res.per_order(name, reading, "PP-FIFO+h", column))]
            add("P7", name, reading, f"{measure} speed-up SAP (SAP / SAP+numb)", statistics.median(sap))
            add("P7", name, reading, f"{measure} speed-up PP (PP-FIFO / PP-FIFO+h)", statistics.median(pp))
            add("P7", name, reading, f"{measure} orders where PP gains more", sum(p > s for p, s in zip(pp, sap)))
    return rows


def figure_r6(res: Results, winners: list[dict], out: Path) -> None:
    """R6: for each building, the 30 time ratios SAP / preflow-push, one dot per door order."""
    verdict = {(r["file"], r["reading"], r["pair"]): r["verdict"] for r in winners if r["measure"] == "time"}
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 7.2), sharey=True)
    ys = {case: k + (1 if case[1] == TWO_WAY else 0) for k, case in enumerate(FLOW_CASES)}
    lows, highs = [], []
    for ax, (pair, (a, b)) in zip(axes, PAIRS.items()):
        counts = {"SAP": 0, "PP": 0, "none": 0}
        for case in FLOW_CASES:
            name, reading = case
            ratios = [x / y for x, y in zip(res.per_order(name, reading, a, "time_median_s"),
                                            res.per_order(name, reading, b, "time_median_s"))]
            lows.append(min(ratios))
            highs.append(max(ratios))
            y = ys[case]
            sap_faster = [r for r in ratios if r < 1]
            pp_faster = [r for r in ratios if r >= 1]
            ax.scatter(sap_faster, [y] * len(sap_faster), s=22, color=BLUE, marker="o", alpha=0.75, lw=0, zorder=3)
            ax.scatter(pp_faster, [y] * len(pp_faster), s=22, color=ORANGE, marker="s", alpha=0.75, lw=0, zorder=3)
            base = res.base(name, reading, a, "time_median_s") / res.base(name, reading, b, "time_median_s")
            ax.scatter([base], [y], s=46, facecolor="none", edgecolor=INK, marker="D", lw=1, zorder=4)
            text = verdict[(name, reading, pair)]
            key = "SAP" if text.startswith("SAP") else "PP" if text.startswith("PP") else "none"
            counts[key] += 1
            short = {"SAP": f"{a} wins", "PP": f"{b} wins", "none": "no clear winner"}[key]
            ax.text(1.02, y, short, transform=ax.get_yaxis_transform(), va="center", fontsize=8.5,
                    color=INK if key != "none" else INK2, fontweight="bold" if key != "none" else "normal")
        ax.axvspan(1 / 1.05, 1.05, color=BAND, zorder=0)
        ax.axvline(1, color=INK2, lw=0.8, zorder=1)
        ax.set_xscale("log")
        ax.set_title(f"{'As taught' if pair == 'headline' else 'With speed-ups'}: {a} against {b}\n"
                     f"{a} wins {counts['SAP']}, {b} wins {counts['PP']}, no clear winner {counts['none']} of 13",
                     loc="left", fontsize=10.5)
        ax.xaxis.grid(True, color=GRID, which="both", zorder=0)
        ax.tick_params(length=0, which="both")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_xlabel(f"Time ratio {a} ÷ {b}, one dot per door order (log scale)\n"
                      f"left of 1: {a} faster; right of 1: {b} faster")
    lo, hi = min(lows) / 1.15, max(highs) * 1.15
    ticks = [t for t in (0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20) if lo <= t <= hi]
    for ax in axes:
        ax.set_xlim(lo, hi)
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{t:g}" for t in ticks])
        ax.minorticks_off()
    axes[0].set_yticks(list(ys.values()))
    axes[0].set_yticklabels([label(*case) for case in FLOW_CASES])
    axes[0].invert_yaxis()
    handles = [plt.Line2D([], [], ls="", marker="o", color=BLUE, label="SAP faster at that door order"),
               plt.Line2D([], [], ls="", marker="s", color=ORANGE, label="Preflow-push faster"),
               plt.Line2D([], [], ls="", marker="D", markerfacecolor="none", markeredgecolor=INK,
                          label="File order (Phase 5)"),
               plt.Rectangle((0, 0), 1, 1, color=BAND, label="Within 5%")]
    fig.legend(handles=handles, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.02), frameon=False)
    fig.tight_layout(rect=(0, 0.05, 0.93, 1), w_pad=6)
    fig.savefig(out, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=PROJECT / "Data")
    parser.add_argument("--results", type=Path, default=PROJECT / "results")
    parser.add_argument("--figures", type=Path, default=PROJECT / "docs" / "figures")
    args = parser.parse_args()

    res = Results(read_rows(args.results / "runs_shuffled.csv"), read_rows(args.results / "runs_baseline.csv"))
    cards = {(r["file"], r["reading"]): r for r in read_rows(args.results / "data_cards.csv")}
    winners = winner_rows(res)
    write(args.results / "winners.csv", winners)
    write(args.results / "prediction_evidence.csv", evidence(res, winners, cards, args.data))
    figure_r6(res, winners, args.figures / "r6_shuffle_ratios.png")

    print(f"{len(res.orders)} door orders. Verdicts (time | work):")
    for pair in PAIRS:
        print(f"\n{pair}: {' against '.join(PAIRS[pair])}")
        for name, reading in FLOW_CASES:
            cells = [r for r in winners if (r["file"], r["reading"], r["pair"]) == (name, reading, pair)]
            print(f"  {label(name, reading):<22}" + " | ".join(
                f"{r['verdict']:<18} {r['a_wins']:>2}-{r['b_wins']:<2} ratio {float(r['median_ratio_a_over_b']):6.3f}"
                for r in cells))
    print(f"\nWrote {args.results / 'winners.csv'}, {args.results / 'prediction_evidence.csv'} and "
          f"{args.figures / 'r6_shuffle_ratios.png'}")


if __name__ == "__main__":
    main()
