"""Correctness tests for the scipy wrappers (tier 3), plus checks that pin down scipy's behavior on
the pitfalls listed in CLAUDE.md. If a future scipy version changes that behavior, these fail."""

import math

import numpy as np
import pytest
from graph_helpers import networkx_apsp, random_dag_with_negative_weights, random_graph
from scipy.sparse.csgraph import dijkstra

from apsp.pure import apsp_dijkstra
from apsp.scipy_tier import apsp_dijkstra_scipy, apsp_floyd_warshall_scipy, edges_to_csr
from apsp.vectorized import apsp_floyd_warshall_numpy

# --- Building the sparse matrix -----------------------------------------------------------------


def test_multi_edges_keep_minimum_not_sum():
    g = edges_to_csr(2, [(0, 1, 4), (0, 1, 10)])
    assert g[0, 1] == 4  # a plain COO -> CSR build would give 14


def test_explicit_zero_weight_is_kept_as_an_edge():
    g = edges_to_csr(2, [(0, 1, 0)])
    assert g.nnz == 1
    assert apsp_dijkstra_scipy(g)[0, 1] == 0
    assert apsp_floyd_warshall_scipy(g)[0, 1] == 0


def test_scipy_drops_stored_zeros_on_eliminate_zeros():
    # Documents the trap: any step that calls eliminate_zeros() turns a 0-cost edge into NO edge.
    g = edges_to_csr(2, [(0, 1, 0)])
    g.eliminate_zeros()
    assert apsp_dijkstra_scipy(g)[0, 1] == math.inf


def test_empty_graph():
    assert np.allclose(apsp_dijkstra_scipy(edges_to_csr(3, [])), np.where(np.eye(3), 0, np.inf))


# --- Correctness against our own implementations and networkx -----------------------------------


def test_hand_checked_toy_graph(toy_graph):
    n, edges, expected = toy_graph
    g = edges_to_csr(n, edges)
    assert np.allclose(apsp_dijkstra_scipy(g), expected)
    assert np.allclose(apsp_floyd_warshall_scipy(g), expected)


def test_path_needing_two_stops_numbered_backwards():
    g = edges_to_csr(4, [(0, 3, 1), (3, 2, 1), (2, 1, 1)])
    assert apsp_floyd_warshall_scipy(g)[0, 1] == 3


@pytest.mark.parametrize("seed", range(50))
def test_all_tiers_agree_on_random_graphs(seed):
    n, edges = random_graph(seed)
    g = edges_to_csr(n, edges)
    reference = networkx_apsp(n, edges)
    assert np.allclose(apsp_dijkstra_scipy(g), reference)
    assert np.allclose(apsp_floyd_warshall_scipy(g), reference)
    assert np.allclose(apsp_dijkstra(n, edges), reference)
    assert np.allclose(apsp_floyd_warshall_numpy(n, edges), reference)


@pytest.mark.parametrize("seed", range(30))
def test_floyd_warshall_negative_weights_without_negative_cycle(seed):
    n, edges = random_dag_with_negative_weights(seed)
    assert np.allclose(apsp_floyd_warshall_scipy(edges_to_csr(n, edges)), networkx_apsp(n, edges))


# --- Negative weights ----------------------------------------------------------------------------


def test_dijkstra_wrapper_rejects_negative_weights():
    with pytest.raises(ValueError, match="nonnegative"):
        apsp_dijkstra_scipy(edges_to_csr(2, [(0, 1, -1)]))


def test_raw_scipy_dijkstra_only_warns_on_negative_weights():
    # Documents WHY our wrapper has its own check: scipy itself does not stop.
    with pytest.warns(UserWarning, match="negative weights"):
        dijkstra(edges_to_csr(2, [(0, 1, -1)]), directed=True)


def test_floyd_warshall_negative_cycle_is_detected():
    with pytest.raises(ValueError, match="negative cycle"):
        apsp_floyd_warshall_scipy(edges_to_csr(2, [(0, 1, 1), (1, 0, -2)]))
