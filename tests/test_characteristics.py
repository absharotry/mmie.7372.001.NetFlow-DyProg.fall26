"""Tests for id compaction and dataset characteristics, on the hand-checkable toy graph."""

import numpy as np
import pytest

from apsp.characteristics import describe
from apsp.loaders import RAW_DIR, Dataset, compact_ids, load_usairport


def test_compact_ids_uses_first_appearance_order():
    # Edges 10->47, 10->832, 2->679  =>  10:0, 47:1, 832:2, 2:3, 679:4
    u, v, original = compact_ids(np.array([10, 10, 2]), np.array([47, 832, 679]))
    assert u.tolist() == [0, 0, 3]
    assert v.tolist() == [1, 2, 4]
    assert original.tolist() == [10, 47, 832, 2, 679]


def test_describe_toy_graph(toy_graph):
    n, edges, _ = toy_graph
    u, v, w = (np.array(col) for col in zip(*edges))
    info = describe(Dataset("toy", n, u, v, w.astype(float), True, "test"))
    assert info["m (edge rows)"] == 7
    assert info["m (distinct pairs)"] == 6  # A->B counted once
    assert info["duplicate rows"] == 1
    assert info["density m/(n(n-1))"] == pytest.approx(6 / 20)
    assert info["reciprocity"] == 0  # no edge has a reverse partner
    assert info["weak components"] == 1
    assert info["strong components"] == 5  # no cycles: every node is its own SCC
    assert info["reachable pair fraction"] == pytest.approx(10 / 20)  # same 10 as the hand table
    assert info["out-degree max"] == 2
    assert info["nodes with out-degree 0"] == 1  # E


@pytest.mark.skipif(not (RAW_DIR / "opsahl-usairport" / "USairport_2010.txt").exists(),
                    reason="raw US airport data not downloaded")
def test_usairport_matches_konect_header():
    ds = load_usairport()
    assert (ds.n, len(ds.u)) == (1574, 28236)  # KONECT header: % 28236 1574 1574
    assert ds.labels[ds.u[0]] == "06A"  # first edge in the original file starts at id 1 = "06A"
