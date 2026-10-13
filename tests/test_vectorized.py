"""Correctness tests for the numpy Floyd-Warshall (tier 2). The pure tier and networkx are oracles."""

import numpy as np
import pytest
from graph_helpers import networkx_apsp, random_dag_with_negative_weights, random_graph

from apsp.pure import apsp_floyd_warshall
from apsp.vectorized import apsp_floyd_warshall_numpy, edges_to_dense


def test_hand_checked_toy_graph(toy_graph):
    n, edges, expected = toy_graph
    assert np.allclose(apsp_floyd_warshall_numpy(n, edges), expected)


def test_path_needing_two_stops_numbered_backwards():
    dist = apsp_floyd_warshall_numpy(4, [(0, 3, 1), (3, 2, 1), (2, 1, 1)])
    assert dist[0, 1] == 3


def test_multi_edge_keeps_minimum_regardless_of_order():
    # Fancy assignment would keep the LAST duplicate; we must keep the SMALLEST.
    assert edges_to_dense(2, [(0, 1, 4), (0, 1, 10)])[0, 1] == 4
    assert edges_to_dense(2, [(0, 1, 10), (0, 1, 4)])[0, 1] == 4


@pytest.mark.parametrize("seed", range(50))
def test_matches_pure_floyd_warshall(seed):
    # Same algorithm, two implementations: results must be identical.
    n, edges = random_graph(seed)
    assert np.allclose(apsp_floyd_warshall_numpy(n, edges), apsp_floyd_warshall(n, edges))


@pytest.mark.parametrize("seed", range(30))
def test_negative_weights_without_negative_cycle(seed):
    n, edges = random_dag_with_negative_weights(seed)
    assert np.allclose(apsp_floyd_warshall_numpy(n, edges), networkx_apsp(n, edges))


def test_negative_cycle_is_detected():
    with pytest.raises(ValueError, match="negative cycle"):
        apsp_floyd_warshall_numpy(2, [(0, 1, 1), (1, 0, -2)])


def test_single_node_no_edges():
    assert apsp_floyd_warshall_numpy(1, []).tolist() == [[0.0]]
