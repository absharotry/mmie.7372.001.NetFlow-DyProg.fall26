"""Phase 1: survey every data case and write one card per case to results/data_cards.csv.

There are 21 data cases: the 14 files read as directed (the main study), plus the 7 sparse files read
as two-way (the supplement). Run from the project folder:

    python scripts/survey_data.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from maxflow.instance import DATASETS, DIRECTED, SPARSE, TWO_WAY, read_instance, to_text
from maxflow.structure import characteristics, find_floors, reference_max_flow

PROJECT = Path(__file__).resolve().parents[1]

COLUMNS = [
    "file", "reading", "group", "n", "m", "density", "m_per_n", "two_way_pairs", "distinct_pairs",
    "out_arcs_s", "in_arcs_t", "capacity_min", "capacity_max", "rooms_reached_from_s",
    "rooms_reaching_t", "shortest_route", "max_flow", "max_flow_scaled", "floors", "rooms_per_floor",
    "up_stairs_per_room", "down_stairs_per_room", "corridor_capacity", "narrowest_gap",
    "stair_sum_max_flow", "source_flood", "sha256",
]


def card(path: Path, reading: str) -> dict:
    inst = read_instance(path, reading)
    c = characteristics(inst)
    flow = reference_max_flow(inst)
    if reading == TWO_WAY:
        group = "two-way supplement"
    else:
        group = "carries flow" if flow > 0 else "zero flow"
    row = {
        "file": inst.name, "reading": reading, "group": group, "n": c["n"], "m": c["m"],
        "density": f"{c['density']:.4f}", "m_per_n": f"{c['m_per_n']:.2f}",
        "two_way_pairs": c["two_way_pairs"], "distinct_pairs": c["distinct_pairs"],
        "out_arcs_s": c["out_arcs_s"], "in_arcs_t": c["in_arcs_t"],
        "capacity_min": to_text(c["capacity_min"]), "capacity_max": to_text(c["capacity_max"]),
        "rooms_reached_from_s": c["rooms_reached_from_s"], "rooms_reaching_t": c["rooms_reaching_t"],
        "shortest_route": "" if c["shortest_route"] is None else c["shortest_route"],
        "max_flow": to_text(flow), "max_flow_scaled": flow,
        "source_flood": to_text(c["source_flood"]),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    floors = find_floors(inst) if reading == DIRECTED else None
    if floors is not None:
        assert floors.proposition_holds and floors.stair_sum_max_flow == flow, inst.name
        row.update({
            "floors": floors.count, "rooms_per_floor": f"{floors.side}x{floors.side}",
            "up_stairs_per_room": f"{floors.up_per_room:g}",
            "down_stairs_per_room": f"{floors.down_per_room:g}",
            "corridor_capacity": to_text(floors.corridor_capacity),
            "narrowest_gap": f"{floors.narrowest_gap + 1}->{floors.narrowest_gap + 2}",
            "stair_sum_max_flow": to_text(floors.stair_sum_max_flow),
        })
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=PROJECT / "Data")
    parser.add_argument("--out", type=Path, default=PROJECT / "results" / "data_cards.csv")
    args = parser.parse_args()

    cases = [(name, DIRECTED) for name in DATASETS] + [(name, TWO_WAY) for name in SPARSE]
    rows = [card(args.data / f"{name}.txt", reading) for name, reading in cases]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, restval="")
        writer.writeheader()
        writer.writerows(rows)

    print(f"{'file':<11} {'reading':<9} {'group':<19} {'n':>5} {'m':>6} {'max flow':>10} {'floors':>6} "
          f"{'narrowest':>9} {'route':>5}")
    for r in rows:
        print(f"{r['file']:<11} {r['reading']:<9} {r['group']:<19} {r['n']:>5} {r['m']:>6} "
              f"{r['max_flow']:>10} {str(r.get('floors', '')):>6} {r.get('narrowest_gap', ''):>9} "
              f"{str(r['shortest_route']):>5}")
    print(f"\nWrote {len(rows)} cards to {args.out}")


if __name__ == "__main__":
    main()
