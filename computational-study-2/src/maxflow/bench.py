"""Benchmark harness (Phase 5): time every setting on every data case, after checking every answer.

Building language: a stopwatch around each evacuation, repeated many times, with every evacuation
checked before its times count.

Protocol (docs/data_modeling.md, Section 10.3):
- Build each building once, untimed.
- Warm-up: one untimed run per (case, setting). It must pass every entry check (Section 10.2):
  passage limits, conservation and the min-cut certificate (verify.check_flow), bookkeeping
  (verify.check_residual), the NetworkX value recorded in results/data_cards.csv, the stair sum on
  the dense files, and all settings agreeing. Its operation counts are the ones reported: with a
  fixed passage order the algorithms are deterministic, and every timed repeat is checked to give
  exactly the same result.
- Timed repeats: all (case, setting, repeat) runs in one shuffled order with a fixed seed, so that a
  slow moment of the machine spreads over all settings. Each repeat starts from fresh residual values
  (untimed); the stopwatch wraps only the solver call, which includes its starting backward search.
  Garbage collection is off while timing.
- Report the median, quartiles, minimum and maximum of the repeats.

Any failed check stops the benchmark with a BenchmarkError, so no unchecked row is ever written.
This module is analysis code, not a solver, so it may use verify (decision DM7 applies to solvers).
"""

from __future__ import annotations

import csv
import gc
import hashlib
import platform
import random
import statistics
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from importlib.metadata import version
from pathlib import Path

from .instance import Instance, parse_capacity, read_instance, to_text
from .preflow import FIFO, HIGHEST, preflow_push
from .residual import Residual, arc_flows, build_residual, shuffle_rooms
from .sap import shortest_augmenting_path
from .verify import check_flow, check_residual

# The six settings of docs/data_modeling.md, Section 10.1, in the order the report uses.
SETTINGS = {
    "SAP": partial(shortest_augmenting_path, numb=False),
    "PP-FIFO": partial(preflow_push, rule=FIFO, heuristics=False),
    "SAP+numb": partial(shortest_augmenting_path, numb=True),
    "PP-FIFO+h": partial(preflow_push, rule=FIFO, heuristics=True),
    "PP-HL": partial(preflow_push, rule=HIGHEST, heuristics=False),
    "PP-HL+h": partial(preflow_push, rule=HIGHEST, heuristics=True),
}

CHECKS = "limits,conservation,min-cut,bookkeeping,networkx,stair-sum,agree"  # stair-sum on dense only

COLUMNS = [
    # identity
    "timestamp", "file", "reading", "group", "n", "m", "density", "setting", "arc_order", "schedule_seed",
    # answer
    "max_flow_scaled", "max_flow", "stop", "checks_passed",
    # time (seconds)
    "time_median_s", "time_q1_s", "time_q3_s", "time_min_s", "time_max_s", "repeats",
    # work shared by both algorithms
    "passages_checked", "passages_checked_start_search", "passages_checked_global", "relabels",
    "label_raises", "gaps", "global_relabels", "people_movements", "total_work",
    # shortest augmenting path only
    "augmentations", "advances", "retreats", "route_length_total", "checks_after_last_group",
    "relabels_after_last_group",
    # preflow-push only
    "saturating_pushes", "nonsaturating_pushes", "flood_pushes", "room_visits", "walkback_pushes",
    "walkback_relabels", "max_label", "checks_after_max_preflow", "relabels_after_max_preflow",
    "pushes_after_max_preflow",
    # machine
    "cpu", "ram_gib", "os", "python", "networkx",
]
TIME_COLUMNS = ["position", "file", "reading", "setting", "repeat", "time_s"]


class BenchmarkError(RuntimeError):
    """A run failed an entry check, or the references do not match the data. The message says which."""


@dataclass(eq=False)
class Case:
    """One data case, built once: the instance, its residual network, and its reference answers."""

    instance: Instance
    group: str  # "carries flow", "zero flow" or "two-way supplement"
    expected: int  # max flow from NetworkX (results/data_cards.csv), scaled
    stair_sum: int | None  # the floor proposition's value on the dense files, else None
    arc_order: int | None = None  # None: the file's own passage order; a number: shuffle_rooms seed
    residual: Residual | None = None

    def __post_init__(self) -> None:
        if self.residual is None:
            self.residual = build_residual(self.instance)
            if self.arc_order is not None:
                self.residual = shuffle_rooms(self.residual, self.arc_order)

    def with_order(self, seed: int) -> "Case":
        """The same case with each room's door list shuffled by `seed`."""
        return Case(self.instance, self.group, self.expected, self.stair_sum, seed,
                    shuffle_rooms(self.residual, seed))

    @property
    def label(self) -> str:
        order = "" if self.arc_order is None else f", order {self.arc_order}"
        return f"{self.instance.name} ({self.instance.reading}{order})"


def load_cases(data_dir: Path, cards_path: Path, names: list[tuple[str, str]]) -> list[Case]:
    """Read the data cases and their references, after confirming each file's checksum matches its card."""
    cards = {(row["file"], row["reading"]): row for row in csv.DictReader(cards_path.open())}
    cases = []
    for name, reading in names:
        card = cards.get((name, reading))
        if card is None:
            raise BenchmarkError(f"{name} ({reading}) has no data card; run scripts/survey_data.py")
        path = data_dir / f"{name}.txt"
        if hashlib.sha256(path.read_bytes()).hexdigest() != card["sha256"]:
            raise BenchmarkError(f"{name}: checksum differs from its data card; run scripts/survey_data.py")
        stair_sum = parse_capacity(card["stair_sum_max_flow"]) if card["stair_sum_max_flow"] else None
        cases.append(Case(read_instance(path, reading), card["group"], int(card["max_flow_scaled"]), stair_sum))
    return cases


def checked_run(case: Case, setting: str):
    """One untimed run that must pass every entry check. Returns the solver's result."""
    residual = case.residual
    res = residual.fresh()
    result = SETTINGS[setting](residual, res)
    where = f"{case.label}, {setting}"
    try:
        check_residual(residual, res)
        check_flow(case.instance, arc_flows(residual, res), result.value)
    except ValueError as err:
        raise BenchmarkError(f"{where}: {err}") from None
    if result.value != case.expected:
        raise BenchmarkError(f"{where}: answer {to_text(result.value)} differs from NetworkX's "
                             f"{to_text(case.expected)}")
    if case.stair_sum is not None and result.value != case.stair_sum:
        raise BenchmarkError(f"{where}: answer {to_text(result.value)} differs from the stair sum "
                             f"{to_text(case.stair_sum)}")
    return result


def timed_run(case: Case, setting: str) -> tuple[float, object]:
    """One timed run: fresh values first (untimed), then the stopwatch around the solver call only."""
    run, residual = SETTINGS[setting], case.residual
    res = residual.fresh()
    start = time.perf_counter()
    result = run(residual, res)
    return time.perf_counter() - start, result


def machine_info() -> dict:
    """The computer the times come from (processor, memory, system), for every results row."""

    def sysctl(key: str) -> str:
        try:
            return subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""

    memory = sysctl("hw.memsize")
    return {
        "cpu": sysctl("machdep.cpu.brand_string") or platform.processor() or platform.machine(),
        "ram_gib": f"{int(memory) / 2**30:.0f}" if memory.isdigit() else "",
        "os": platform.platform(),
        "python": platform.python_version(),
        "networkx": version("networkx"),
    }


def summary_row(case: Case, setting: str, result, times: list[float], seed: int, stamp: str,
                machine: dict) -> dict:
    """One results row (docs/data_modeling.md, Section 10.7). Counters that do not apply stay empty."""
    inst, c = case.instance, result.counts
    q1, _, q3 = statistics.quantiles(times, n=4, method="inclusive") if len(times) > 1 else times * 3
    row = {
        "timestamp": stamp, "file": inst.name, "reading": inst.reading, "group": case.group,
        "n": inst.n, "m": inst.m, "density": f"{inst.m / (inst.n * (inst.n - 1)):.4f}", "setting": setting,
        "arc_order": "file" if case.arc_order is None else case.arc_order, "schedule_seed": seed,
        "max_flow_scaled": result.value, "max_flow": to_text(result.value),
        "checks_passed": CHECKS if case.stair_sum is not None else CHECKS.replace(",stair-sum", ""),
        "time_median_s": f"{statistics.median(times):.9f}", "time_q1_s": f"{q1:.9f}", "time_q3_s": f"{q3:.9f}",
        "time_min_s": f"{min(times):.9f}", "time_max_s": f"{max(times):.9f}", "repeats": len(times),
        "passages_checked": c.checks, "passages_checked_start_search": c.backward_checks,
        "relabels": c.relabels, "people_movements": c.movements, "total_work": c.checks + c.movements,
        **machine,
    }
    if setting.startswith("SAP"):
        row.update({
            "stop": result.stop, "augmentations": c.augmentations, "advances": c.advances,
            "retreats": c.retreats, "route_length_total": c.movements,
            "checks_after_last_group": c.checks_after_last, "relabels_after_last_group": c.relabels_after_last,
        })
    else:
        row.update({
            "passages_checked_global": c.global_checks, "label_raises": c.label_raises, "gaps": c.gaps,
            "global_relabels": c.global_relabels, "saturating_pushes": c.saturating,
            "nonsaturating_pushes": c.nonsaturating, "flood_pushes": c.source_pushes,
            "room_visits": c.examinations, "walkback_pushes": c.walkback_pushes,
            "walkback_relabels": c.walkback_relabels, "max_label": c.max_label,
            "checks_after_max_preflow": c.checks_after_max_preflow,
            "relabels_after_max_preflow": c.relabels_after_max_preflow,
            "pushes_after_max_preflow": c.pushes_after_max_preflow,
        })
    return row


def run_benchmark(cases: list[Case], settings: list[str] | None = None, repeats: int = 31,
                  seed: int = 7372, progress=None) -> tuple[list[dict], list[dict]]:
    """Check, then time, every (case, setting). Returns the summary rows and the individual times.

    `progress`, if given, is called as progress(done, total) during the timed runs.
    """
    settings = list(SETTINGS) if settings is None else settings
    rng = random.Random(seed)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    machine = machine_info()

    # Warm-ups: one checked run per combination, in shuffled order.
    combos = [(k, setting) for k in range(len(cases)) for setting in settings]
    rng.shuffle(combos)
    results = {(k, setting): checked_run(cases[k], setting) for k, setting in combos}
    for k, case in enumerate(cases):
        values = {results[(k, setting)].value for setting in settings}
        if len(values) != 1:
            raise BenchmarkError(f"{case.label}: settings disagree: {sorted(values)}")

    # Timed repeats: every run of every combination in one shuffled order.
    schedule = [combo for combo in combos for _ in range(repeats)]
    rng.shuffle(schedule)
    times: dict[tuple[int, str], list[float]] = {combo: [] for combo in combos}
    time_rows = []
    gc.collect()
    gc.disable()
    try:
        for position, (k, setting) in enumerate(schedule, start=1):
            elapsed, result = timed_run(cases[k], setting)
            if result != results[(k, setting)]:
                raise BenchmarkError(f"{cases[k].label}, {setting}: a timed repeat gave a different result")
            times[(k, setting)].append(elapsed)
            time_rows.append({"position": position, "file": cases[k].instance.name,
                              "reading": cases[k].instance.reading, "setting": setting,
                              "repeat": len(times[(k, setting)]), "time_s": f"{elapsed:.9f}"})
            if progress is not None:
                progress(position, len(schedule))
    finally:
        gc.enable()

    summary = [summary_row(cases[k], setting, results[(k, setting)], times[(k, setting)], seed, stamp, machine)
               for k in range(len(cases)) for setting in settings]
    return summary, time_rows


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, restval="")
        writer.writeheader()
        writer.writerows(rows)

