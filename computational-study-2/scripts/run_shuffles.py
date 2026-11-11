"""Phase 6: check and time the four headline and tuned settings at 30 shuffled door orders.

Run from the project folder, with the machine otherwise idle (about 30 minutes):

    python scripts/run_shuffles.py

Covers the 13 data cases that carry flow: the 6 dense files read as directed and the 7 sparse files
read as two-way. For each door-order seed, every room's passage list is shuffled (residual.shuffle_rooms)
and all four settings run on that same shuffled building, so each comparison is paired. Each seed is
its own timed block: 1 checked warm-up and 5 timed repeats per combination, in a shuffled order.

Writes results/runs_shuffled.csv (one row per case, setting and seed) and results/times_shuffled.csv.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from maxflow.bench import COLUMNS, TIME_COLUMNS, load_cases, run_benchmark, write_csv
from maxflow.instance import DENSE, DIRECTED, SPARSE, TWO_WAY

PROJECT = Path(__file__).resolve().parents[1]
FLOW_CASES = [(name, DIRECTED) for name in DENSE] + [(name, TWO_WAY) for name in SPARSE]
SETTINGS = ["SAP", "PP-FIFO", "SAP+numb", "PP-FIFO+h"]  # highest-label runs at file order only
SCHEDULE_SEED = 7372  # each block's schedule uses SCHEDULE_SEED + its door-order seed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=PROJECT / "Data")
    parser.add_argument("--cards", type=Path, default=PROJECT / "results" / "data_cards.csv")
    parser.add_argument("--out", type=Path, default=PROJECT / "results")
    parser.add_argument("--orders", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()

    cases = load_cases(args.data, args.cards, FLOW_CASES)
    print(f"{len(cases)} cases x {len(SETTINGS)} settings x {args.orders} door orders x {args.repeats} "
          f"repeats = {len(cases) * len(SETTINGS) * args.orders * args.repeats} timed runs", flush=True)
    started = time.perf_counter()
    summary, times = [], []
    for seed in range(1, args.orders + 1):
        rows, timed = run_benchmark([case.with_order(seed) for case in cases], settings=SETTINGS,
                                    repeats=args.repeats, seed=SCHEDULE_SEED + seed)
        summary += rows
        times += [{"arc_order": seed, **row} for row in timed]
        print(f"  door order {seed:2d}/{args.orders} done, {time.perf_counter() - started:5.0f} s", flush=True)

    write_csv(args.out / "runs_shuffled.csv", summary, COLUMNS)
    write_csv(args.out / "times_shuffled.csv", times, ["arc_order", *TIME_COLUMNS])
    print(f"\nWrote {len(summary)} rows to {args.out / 'runs_shuffled.csv'} and {len(times)} times to "
          f"{args.out / 'times_shuffled.csv'} in {time.perf_counter() - started:.0f} s")


if __name__ == "__main__":
    sys.exit(main())
