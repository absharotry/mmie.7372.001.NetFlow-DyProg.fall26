"""Correctness tests for the pure-Python Dijkstra (tier 1), with networkx as the oracle."""

import math

import numpy as np
import pytest
from graph_helpers import networkx_apsp, random_graph

from apsp.pure import adjacency_list, apsp_dijkstra, dijkstra


def test_hand_checked_toy_graph(toy_graph):
    n, edges, expected = toy_graph
    assert np.allclose(apsp_dijkstra(n, edges), expected)


def test_single_source_from_A(toy_graph):
    # The walkthrough done by hand: from A, distances to (A, B, C, D, E) = (0, 3, 1, 4, 7).
    n, edges, _ = toy_graph
    assert dijkstra(adjacency_list(n, edges), 0) == [0, 3, 1, 4, 7]


@pytest.mark.parametrize("seed", range(50))
def test_matches_networkx_on_random_graphs(seed):
    n, edges = random_graph(seed)
    assert np.allclose(apsp_dijkstra(n, edges), networkx_apsp(n, edges))


def test_zero_weight_edge_is_a_real_edge():
    # 0 -> 1 costs nothing; it must not be treated as "no edge".
    assert apsp_dijkstra(2, [(0, 1, 0)]) == [[0, 0], [math.inf, 0]]


def test_single_node_no_edges():
    assert apsp_dijkstra(1, []) == [[0]]


def test_negative_weight_is_rejected():
    with pytest.raises(ValueError, match="nonnegative"):
        apsp_dijkstra(2, [(0, 1, -1)])
