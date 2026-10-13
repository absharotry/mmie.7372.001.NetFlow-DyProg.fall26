"""Tests for the benchmark harness: every (tier, algo) runs end-to-end in a fresh process on the toy
graph and produces the same summary as the hand-computed table."""

import numpy as np
import pandas as pd
import pytest

from apsp.bench import append_row, feasibility, run_one
from apsp.bench_worker import ALGORITHMS, Summary
from apsp.loaders import Dataset
from apsp.preprocess import save_processed

GIB = 2**30


@pytest.fixture
def toy_processed_dir(tmp_path, toy_graph):
    n, edges, _ = toy_graph
    u, v, w = (np.array(col) for col in zip(*edges))
    save_processed(Dataset("toy", n, u, v, w.astype(float), True, "test"), "toy", folder=tmp_path)
    return tmp_path


def test_summary_excludes_diagonal_and_unreachable(toy_graph):
    _, _, expected = toy_graph
    s = Summary()
    s.add_table(np.array(expected, dtype=float))
    # Hand table: 10 reachable off-diagonal pairs, distances summing to 15 + 5 + 11 + 3 = 34.
    assert s.as_dict() == {"reachable_pairs": 10, "mean_distance": 3.4, "max_distance": 7.0}


@pytest.mark.parametrize("tier, algo", sorted(ALGORITHMS))
def test_every_algorithm_runs_in_a_fresh_process(toy_processed_dir, tier, algo):
    row = run_one("toy", tier, algo, timeout_s=120, processed_dir=toy_processed_dir)
    assert row["status"] == "ok", row.get("reason")
    assert row["reachable_pairs"] == 10
    assert row["mean_distance"] == pytest.approx(3.4)
    assert row["max_distance"] == 7
    assert row["warmup"] and row["repeats"] == 5  # toy runs are short: warm-up + 5 repeats
    assert row["peak_rss_mib"] >= row["baseline_rss_mib"] > 0


def test_floyd_warshall_on_wiki_scale_is_infeasible():
    ok, need, reason = feasibility("scipy", "floyd_warshall", 116_836, 4_055_742, 24 * GIB)
    assert not ok and need > 100 * GIB and "budget" in reason
    ok, _, _ = feasibility("scipy", "dijkstra", 116_836, 4_055_742, 24 * GIB)
    assert ok  # Dijkstra streams, so it never needs the n x n table


def test_infeasible_run_is_recorded_not_attempted(toy_processed_dir):
    row = run_one("toy", "pure", "floyd_warshall", timeout_s=120,
                  processed_dir=toy_processed_dir, ram_bytes=1)  # pretend RAM is 1 byte
    assert row["status"] == "infeasible" and "wall_s" not in row


def test_timeout_is_recorded(toy_processed_dir):
    row = run_one("toy", "scipy", "dijkstra", timeout_s=0.01, processed_dir=toy_processed_dir)
    assert row["status"] == "timeout"


def test_error_is_recorded(tmp_path):
    # Negative weight: our Dijkstra guard must refuse, and the runner must record an error.
    save_processed(Dataset("neg", 2, np.array([0]), np.array([1]), np.array([-1.0]), True, "t"),
                   "neg", folder=tmp_path)
    row = run_one("neg", "scipy", "dijkstra", timeout_s=120, processed_dir=tmp_path)
    assert row["status"] == "error" and "nonnegative" in row["reason"]


def test_append_row_handles_new_columns(tmp_path):
    path = tmp_path / "r.csv"
    append_row({"a": 1}, path)
    append_row({"a": 2, "b": 3}, path)
    table = pd.read_csv(path)
    assert table["a"].tolist() == [1, 2]
    assert np.isnan(table["b"][0]) and table["b"][1] == 3  # old row gets an empty cell
