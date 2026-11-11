"""Tests for the benchmark harness: the schedule, the rows, and every check that must stop a run."""

import csv
import gc
import hashlib
import shutil
from pathlib import Path

import pytest
from conftest import CASES, MINI_BUILDING

from maxflow.bench import (
    COLUMNS, SETTINGS, TIME_COLUMNS, BenchmarkError, Case, load_cases, machine_info, run_benchmark, write_csv,
)
from maxflow.instance import SCALE, read_instance

DATA = Path(__file__).resolve().parent / "data"


@pytest.fixture
def small_cases():
    mini = Case(read_instance(MINI_BUILDING), "carries flow", 9 * SCALE, 9 * SCALE)  # with a stair sum
    amo = Case(read_instance(DATA / "amo_figure_7_4.txt"), "carries flow", 5 * SCALE, None)
    return [mini, amo]


def test_six_settings_in_report_order():
    assert list(SETTINGS) == ["SAP", "PP-FIFO", "SAP+numb", "PP-FIFO+h", "PP-HL", "PP-HL+h"]


def test_small_benchmark(small_cases):
    summary, times = run_benchmark(small_cases, repeats=3, seed=1)
    assert gc.isenabled()  # switched back on after timing
    assert len(summary) == 2 * 6 and len(times) == 2 * 6 * 3

    # Every combination appears exactly `repeats` times, at distinct positions.
    assert sorted(row["position"] for row in times) == list(range(1, 37))
    for case in ("mini_building", "amo_figure_7_4"):
        for setting in SETTINGS:
            mine = [row for row in times if row["file"] == case and row["setting"] == setting]
            assert sorted(row["repeat"] for row in mine) == [1, 2, 3]
            assert all(float(row["time_s"]) > 0 for row in mine)

    for row in summary:
        assert set(row) <= set(COLUMNS)
        assert row["repeats"] == 3 and row["arc_order"] == "file"
        assert float(row["time_min_s"]) <= float(row["time_median_s"]) <= float(row["time_max_s"])
        assert row["total_work"] == row["passages_checked"] + row["people_movements"]
        sap = row["setting"].startswith("SAP")
        assert ("augmentations" in row) == sap and ("saturating_pushes" in row) == (not sap)
    mini_rows = [row for row in summary if row["file"] == "mini_building"]
    assert {row["max_flow"] for row in mini_rows} == {"9"}
    assert all("stair-sum" in row["checks_passed"] for row in mini_rows)
    assert not any("stair-sum" in row["checks_passed"] for row in summary if row["file"] == "amo_figure_7_4")
    # The counts match the hand traces (tests/test_sap.py and tests/test_preflow.py).
    by_setting = {row["setting"]: row for row in mini_rows}
    assert by_setting["SAP"]["relabels"] == 10 and by_setting["SAP+numb"]["relabels"] == 5
    assert by_setting["PP-FIFO"]["room_visits"] == 22 and by_setting["PP-FIFO+h"]["gaps"] == 1


def test_schedule_is_reproducible(small_cases):
    order = lambda times: [(row["file"], row["setting"]) for row in times]  # noqa: E731
    assert order(run_benchmark(small_cases, repeats=2, seed=5)[1]) == order(run_benchmark(small_cases, repeats=2, seed=5)[1])
    assert order(run_benchmark(small_cases, repeats=2, seed=5)[1]) != order(run_benchmark(small_cases, repeats=2, seed=6)[1])


def test_wrong_reference_stops_the_benchmark(small_cases):
    small_cases[1].expected = 4 * SCALE
    with pytest.raises(BenchmarkError, match="differs from NetworkX's 4"):
        run_benchmark(small_cases, repeats=1)
    assert gc.isenabled()


def test_wrong_stair_sum_stops_the_benchmark(small_cases):
    small_cases[0].stair_sum = 8 * SCALE
    with pytest.raises(BenchmarkError, match="differs from the stair sum 8"):
        run_benchmark(small_cases, repeats=1)


def write_cards(path, sha256):
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file", "reading", "group", "max_flow_scaled", "stair_sum_max_flow", "sha256"])
        writer.writerow(["mini", "directed", "carries flow", 9 * SCALE, "9", sha256])


def test_load_cases_checks_the_cards(tmp_path):
    shutil.copy(MINI_BUILDING, tmp_path / "mini.txt")
    cards = tmp_path / "cards.csv"
    write_cards(cards, hashlib.sha256(MINI_BUILDING.read_bytes()).hexdigest())
    (case,) = load_cases(tmp_path, cards, [("mini", "directed")])
    assert (case.expected, case.stair_sum, case.group) == (9 * SCALE, 9 * SCALE, "carries flow")
    assert case.residual.records == 28

    write_cards(cards, "0" * 64)
    with pytest.raises(BenchmarkError, match="checksum differs"):
        load_cases(tmp_path, cards, [("mini", "directed")])
    with pytest.raises(BenchmarkError, match="no data card"):
        load_cases(tmp_path, cards, [("mini", "two-way")])


def test_real_data_cards_match_the_files(data_dir):
    cases = load_cases(data_dir, data_dir.parent / "results" / "data_cards.csv", CASES)
    assert len(cases) == 21
    assert sum(case.stair_sum is not None for case in cases) == 6


def test_machine_info_and_csv(tmp_path, small_cases):
    info = machine_info()
    assert set(info) == {"cpu", "ram_gib", "os", "python", "networkx"} and info["python"]
    summary, times = run_benchmark(small_cases, repeats=1)
    write_csv(tmp_path / "runs.csv", summary, COLUMNS)
    write_csv(tmp_path / "times.csv", times, TIME_COLUMNS)
    with (tmp_path / "runs.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == COLUMNS and len(rows) == 12


def test_shuffled_cases_keep_their_answers(small_cases):
    shuffled = [case.with_order(seed) for case in small_cases for seed in (1, 2, 3)]
    assert [case.arc_order for case in shuffled] == [1, 2, 3, 1, 2, 3]
    assert shuffled[0].residual.out != small_cases[0].residual.out
    summary, _ = run_benchmark(shuffled, settings=["SAP", "PP-FIFO", "SAP+numb", "PP-FIFO+h"], repeats=2)
    assert len(summary) == 6 * 4
    assert {row["arc_order"] for row in summary} == {1, 2, 3}
    assert {row["max_flow"] for row in summary if row["file"] == "mini_building"} == {"9"}
