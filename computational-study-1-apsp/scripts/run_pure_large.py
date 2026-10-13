"""Our own (pure Python) n x Dijkstra on the two large datasets, appended to results/benchmarks.csv.

    python scripts/run_pure_large.py --stages slashdot,sample        # the two short runs
    python scripts/run_pure_large.py --stages full --deadline 19:30  # the long run

1. Slashdot Zoo, all sources.
2. Wiki Conflict, a random sample of SAMPLE sources (fixed seed); time scaled by n / SAMPLE.
   This is the guaranteed fallback estimate.
3. Wiki Conflict, all sources, stopped at --deadline (local time) if not finished; the stop is
   recorded as status "timeout".
"""

import argparse
import datetime as dt

from apsp.bench import append_row, run_one

SAMPLE = 1000


def seconds_until(hhmm):
    now = dt.datetime.now()
    h, m = map(int, hhmm.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return max(60, int((target - now).total_seconds()))


def report(label, row):
    if row["status"] == "ok":
        extra = (f", full-run estimate {row['algo_full_estimate_s'] / 3600:.2f} h"
                 if row["sources"] != row["n"] else "")
        print(f"{label}: ok, {row['algo_median_s']:,.1f} s for {row['sources']:,} sources{extra}",
              flush=True)
    else:
        print(f"{label}: {row['status'].upper()}: {row['reason']}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deadline", default="19:30", help="stop the full Wiki run at HH:MM")
    parser.add_argument("--stages", default="slashdot,sample,full",
                        help="comma-separated subset of: slashdot, sample, full")
    args = parser.parse_args()
    stages = set(args.stages.split(","))

    if "slashdot" in stages:
        row = run_one("slashdot", "pure", "dijkstra", timeout_s=2 * 3600)
        append_row(row)
        report("slashdot pure dijkstra (all sources)", row)

    if "sample" in stages:
        row = run_one("wikiconflict", "pure", "dijkstra", timeout_s=3600, sample=SAMPLE)
        append_row(row)
        report(f"wikiconflict pure dijkstra ({SAMPLE} sources)", row)

    if "full" not in stages:
        return
    timeout = seconds_until(args.deadline)
    print(f"wikiconflict full run: time limit {timeout / 3600:.2f} h (until {args.deadline})", flush=True)
    row = run_one("wikiconflict", "pure", "dijkstra", timeout_s=timeout)
    append_row(row)
    report("wikiconflict pure dijkstra (all sources)", row)


if __name__ == "__main__":
    main()
