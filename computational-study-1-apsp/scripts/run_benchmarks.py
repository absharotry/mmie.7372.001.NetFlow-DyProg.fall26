"""Run the benchmark plan, smallest dataset first, appending each result to results/benchmarks.csv.

    python scripts/run_benchmarks.py                    # the whole plan
    python scripts/run_benchmarks.py usairport health   # only these datasets

Plan (2026-10-12, chosen by the user): the three small datasets in every implementation; the two
large ones in scipy only. Pure-Python runs on the large datasets are decided later.
Floyd-Warshall on the large datasets is still listed: the feasibility check records it as
"infeasible" with the memory it would need, instead of running it.
"""

import sys

from apsp.bench import RESULTS_CSV, append_row, run_one

TIMEOUT_S = 2 * 3600  # generous for this batch: the longest estimate is ~45 min

ALL = [("scipy", "dijkstra"), ("scipy", "floyd_warshall"), ("numpy", "floyd_warshall"),
       ("pure", "dijkstra"), ("pure", "floyd_warshall")]
SCIPY = [("scipy", "dijkstra"), ("scipy", "floyd_warshall")]

PLAN = [  # smallest -> largest (CLAUDE.md, Phase 4)
    ("usairport", ALL),
    ("health", ALL),
    ("advogato", ALL),
    ("slashdot", SCIPY),
    ("wikiconflict", SCIPY),
]


def main():
    only = set(sys.argv[1:])
    for slug, combos in PLAN:
        if only and slug not in only:
            continue
        for tier, algo in combos:
            print(f"{slug:<13} {tier:<6} {algo:<15}", end=" ", flush=True)
            row = run_one(slug, tier, algo, TIMEOUT_S)
            append_row(row)
            if row["status"] == "ok":
                print(f"ok   algo {row['algo_median_s']:>10.3f} s (median of {row['repeats']})"
                      f"   peak {row['peak_rss_mib']:>8,.0f} MiB"
                      f"   reachable {row['reachable_pairs']:,}", flush=True)
            else:
                print(f"{row['status'].upper()}: {row['reason']}", flush=True)
    print(f"\nResults appended to {RESULTS_CSV}")


if __name__ == "__main__":
    main()
