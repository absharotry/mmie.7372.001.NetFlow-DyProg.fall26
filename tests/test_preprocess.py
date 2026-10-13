"""Tests for preprocessing transforms and the processed-file round trip."""

import numpy as np
import pytest

from apsp.loaders import Dataset
from apsp.preprocess import (drop_isolated, drop_self_loops, friends_only_hops, inverse_weights,
                            load_processed, save_processed, undirected_hops)
from apsp.scipy_tier import apsp_dijkstra_scipy, edges_to_csr


def small_dataset(w):
    return Dataset("t", 3, np.array([0, 1, 0]), np.array([1, 2, 2]), np.array(w, dtype=float),
                   True, "passengers", labels=["X", "Y", "Z"], source="test")


def test_inverse_weights_values():
    out = inverse_weights(small_dataset([1, 4, 1_000_000]))
    assert np.allclose(out.w, [1, 0.25, 1e-6])
    assert out.weight_meaning == "1 / (passengers)"


def test_busy_two_leg_path_beats_quiet_direct_route():
    # The decision-log example in miniature: X->Z direct carried 1 passenger (cost 1), while
    # X->Y and Y->Z carried 1,000 each (cost 0.001 + 0.001). The 2-leg path wins.
    ds = inverse_weights(small_dataset([1000, 1000, 1]))
    dist = apsp_dijkstra_scipy(edges_to_csr(ds.n, list(zip(ds.u, ds.v, ds.w))))
    assert dist[0, 2] == pytest.approx(0.002)


def test_inverse_weights_rejects_zero():
    with pytest.raises(ValueError, match="strictly positive"):
        inverse_weights(small_dataset([1, 0, 2]))


def test_save_load_round_trip(tmp_path):
    ds = inverse_weights(small_dataset([1, 2, 3]))
    save_processed(ds, "t", folder=tmp_path)
    back = load_processed("t", folder=tmp_path)
    assert back.n == ds.n and back.directed and back.labels == ["X", "Y", "Z"]
    assert np.array_equal(back.u, ds.u) and np.array_equal(back.v, ds.v)
    assert np.array_equal(back.w, ds.w)  # exact: .npz stores float64 bits, no rounding


# --- Wiki Conflict decisions (D2, D2b, D3) on a tiny hand-made signed, undirected dataset ---------

def tiny_signed_undirected():
    # Ids 0..5; id 3 and id 5 never appear (isolated). Pair {0,1} interacts 3 times with mixed signs,
    # once stored as (1, 0). Pair {2,4} has a zero weight (ln 1 = 0).
    return Dataset("wiki-mini", 6,
                   u=np.array([0, 0, 1, 1, 2]), v=np.array([1, 1, 0, 2, 4]),
                   w=np.array([-0.69, 1.1, -2.0, -0.69, 0.0]), directed=False, weight_meaning="signed")


def test_drop_isolated_renumbers_by_first_appearance():
    out = drop_isolated(tiny_signed_undirected())
    assert out.n == 4  # ids 3 and 5 are gone
    # first appearance: 0 -> 0, 1 -> 1, 2 -> 2, 4 -> 3
    assert out.u.tolist() == [0, 0, 1, 1, 2] and out.v.tolist() == [1, 1, 0, 2, 3]


def test_undirected_hops_one_edge_per_pair_both_directions():
    out = undirected_hops(drop_isolated(tiny_signed_undirected()))
    arcs = sorted(zip(out.u.tolist(), out.v.tolist()))
    # pairs {0,1}, {1,2}, {2,3}: each once per direction, whatever the sign or repeat count
    assert arcs == [(0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2)]
    assert (out.w == 1).all() and not out.directed


def test_hops_graph_runs_through_dijkstra_without_negative_weights():
    # The raw graph would be rejected (negative weights). After D2 it is a plain unit-weight graph.
    out = undirected_hops(drop_isolated(tiny_signed_undirected()))
    dist = apsp_dijkstra_scipy(edges_to_csr(out.n, list(zip(out.u, out.v, out.w))))
    assert dist[0].tolist() == [0, 1, 2, 3]  # 0 -1- 1 -1- 2 -1- 3


# --- Slashdot decisions (D4, D4b) ------------------------------------------------------------------

def test_friends_only_removes_foes_and_mutual_foe_cycle():
    # 0 <-> 1 mutual foes (a negative 2-cycle), 1 -> 2 friend, 2 -> 3 friend, 3 -> 4 foe.
    ds = Dataset("sd-mini", 5, u=np.array([0, 1, 1, 2, 3]), v=np.array([1, 0, 2, 3, 4]),
                 w=np.array([-1.0, -1.0, 1.0, 1.0, -1.0]), directed=True, weight_meaning="+-1")
    out = drop_isolated(friends_only_hops(ds))
    # Only 1 -> 2 -> 3 survives; nodes 0 and 4 had only foe tags and are dropped (D4b).
    assert out.n == 3 and out.directed and (out.w == 1).all()
    dist = apsp_dijkstra_scipy(edges_to_csr(out.n, list(zip(out.u, out.v, out.w))))
    assert dist[0].tolist() == [0, 1, 2]  # direction kept: forward chain reachable...
    assert dist[2, 0] == np.inf  # ...but not backwards


# --- Advogato decisions (D6, D6b, D6c) --------------------------------------------------------------

def test_self_loops_removed_then_self_only_node_is_isolated():
    # Node 2 only certified itself; node 0 certified itself and node 1.
    ds = Dataset("adv-mini", 3, u=np.array([0, 0, 2]), v=np.array([0, 1, 2]),
                 w=np.array([0.8, 1.0, 0.6]), directed=True, weight_meaning="trust",
                 labels=["ann", "bob", "cy"])
    out = inverse_weights(drop_isolated(drop_self_loops(ds)))
    assert out.n == 2 and out.labels == ["ann", "bob"]  # "cy" had only a self-loop: dropped
    assert out.u.tolist() == [0] and out.v.tolist() == [1] and out.w.tolist() == [1.0]


def test_advogato_levels_never_detour():
    # Under 1/w the cheapest step is 1.0 (master) and the dearest 1/0.6 = 1.67 (apprentice), so any
    # two-step chain (>= 2.0) loses to a direct certification, even the weakest one.
    ds = inverse_weights(Dataset("adv", 3, u=np.array([0, 0, 1]), v=np.array([2, 1, 2]),
                                 w=np.array([0.6, 1.0, 1.0]), directed=True, weight_meaning="trust"))
    dist = apsp_dijkstra_scipy(edges_to_csr(ds.n, list(zip(ds.u, ds.v, ds.w))))
    assert dist[0, 2] == pytest.approx(1 / 0.6)  # direct apprentice link beats master -> master
