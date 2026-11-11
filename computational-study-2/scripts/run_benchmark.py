"""Phase 5: check and time all six settings on all 21 data cases, at the file's own passage order.

Run from the project folder, with the machine otherwise idle (about 8 minutes):

    python scripts/run_benchmark.py

Writes results/runs_baseline.csv (one row per case and setting) and results/times_baseline.csv (every
timed repeat). The protocol is in src/maxflow/bench.py and docs/data_modeling.md, Section 10.3.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from maxflow.bench import COLUMNS, SETTINGS, TIME_COLUMNS, load_cases, run_benchmark, write_csv
from maxflow.instance import DATASETS, DIRECTED, SPARSE, TWO_WAY

PROJECT = Path(__file__).resolve().parents[1]
CASES = [(name, DIRECTED) for name in DATASETS] + [(name, TWO_WAY) for name in SPARSE]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=PROJECT / "Data")
    parser.add_argument("--cards", type=Path, default=PROJECT / "results" / "data_cards.csv")
    parser.add_argument("--out", type=Path, default=PROJECT / "results")
    parser.add_argument("--repeats", type=int, default=31)
    parser.add_argument("--seed", type=int, default=7372)
    args = parser.parse_args()

    cases = load_cases(args.data, args.cards, CASES)
    total = len(cases) * len(SETTINGS) * args.repeats
    print(f"{len(cases)} cases x {len(SETTINGS)} settings x {args.repeats} repeats = {total} timed runs, "
          f"seed {args.seed}", flush=True)
    started = time.perf_counter()

    def progress(done: int, all_runs: int) -> None:
        if done % max(all_runs // 20, 1) == 0 or done == all_runs:
            print(f"  {done:5d}/{all_runs} timed runs, {time.perf_counter() - started:5.0f} s", flush=True)

    summary, times = run_benchmark(cases, repeats=args.repeats, seed=args.seed, progress=progress)
    write_csv(args.out / "runs_baseline.csv", summary, COLUMNS)
    write_csv(args.out / "times_baseline.csv", times, TIME_COLUMNS)

    print(f"\nMedian time in milliseconds (every answer checked; machine: {summary[0]['cpu']})")
    print(f"{'case':<21}" + "".join(f"{s:>11}" for s in SETTINGS))
    for k in range(0, len(summary), len(SETTINGS)):
        rows = summary[k:k + len(SETTINGS)]
        label = f"{rows[0]['file']} {'2-way' if rows[0]['reading'] == TWO_WAY else ''}"
        print(f"{label:<21}" + "".join(f"{float(r['time_median_s']) * 1000:11.2f}" for r in rows))
    print(f"\nWrote {len(summary)} rows to {args.out / 'runs_baseline.csv'} and {len(times)} times to "
          f"{args.out / 'times_baseline.csv'} in {time.perf_counter() - started:.0f} s")


if __name__ == "__main__":
    sys.exit(main())
