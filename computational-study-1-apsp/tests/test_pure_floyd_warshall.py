"""Correctness tests for the pure-Python Floyd-Warshall (tier 1), with networkx as the oracle."""

import math

import numpy as np
import pytest
from graph_helpers import networkx_apsp, random_dag_with_negative_weights, random_graph

from apsp.pure import apsp_dijkstra, apsp_floyd_warshall


def test_hand_checked_toy_graph(toy_graph):
    n, edges, expected = toy_graph
    assert np.allclose(apsp_floyd_warshall(n, edges), expected)


def test_path_needing_two_stops_numbered_backwards():
    # Chain 0 -> 3 -> 2 -> 1, each edge cost 1, so 0 -> 1 = 3 using stops 3 and 2.
    # Guards against the classic bug of putting the k loop innermost (i, j, k order): that version
    # fills in dist[0][1] before dist[0][2] and dist[3][1] are known and gets inf. The toy graph
    # does NOT catch that bug, because its nodes happen to be numbered in path order.
    dist = apsp_floyd_warshall(4, [(0, 3, 1), (3, 2, 1), (2, 1, 1)])
    assert dist[0][1] == 3


@pytest.mark.parametrize("seed", range(50))
def test_matches_networkx_on_random_graphs(seed):
    n, edges = random_graph(seed)
    assert np.allclose(apsp_floyd_warshall(n, edges), networkx_apsp(n, edges))


@pytest.mark.parametrize("seed", range(50))
def test_agrees_with_our_dijkstra(seed):
    # Two completely different algorithms must produce the same table.
    n, edges = random_graph(seed)
    assert np.allclose(apsp_floyd_warshall(n, edges), apsp_dijkstra(n, edges))


@pytest.mark.parametrize("seed", range(30))
def test_negative_weights_without_negative_cycle(seed):
    # FW handles negative edges (Dijkstra can't), as long as no cycle has a negative total.
    n, edges = random_dag_with_negative_weights(seed)
    assert np.allclose(apsp_floyd_warshall(n, edges), networkx_apsp(n, edges))


def test_negative_edge_hand_example():
    # 0 -> 1 costs 5, but 0 -> 2 -> 1 costs 2 + (-4) = -2.
    dist = apsp_floyd_warshall(3, [(0, 1, 5), (0, 2, 2), (2, 1, -4)])
    assert dist[0][1] == -2


def test_negative_cycle_is_detected():
    # 0 -> 1 -> 0 costs 1 + (-2) = -1: every lap makes the path shorter.
    with pytest.raises(ValueError, match="negative cycle"):
        apsp_floyd_warshall(2, [(0, 1, 1), (1, 0, -2)])


def test_one_negative_undirected_edge_is_a_negative_cycle():
    # The CLAUDE.md pitfall: an undirected edge {0, 1} with weight -1 means 0 -> 1 AND 1 -> 0,
    # so 0 -> 1 -> 0 already costs -2. This is why the signed datasets need a decision.
    with pytest.raises(ValueError, match="negative cycle"):
        apsp_floyd_warshall(2, [(0, 1, -1), (1, 0, -1)])


def test_zero_weight_edge_is_a_real_edge():
    assert apsp_floyd_warshall(2, [(0, 1, 0)]) == [[0, 0], [math.inf, 0]]


def test_single_node_no_edges():
    assert apsp_floyd_warshall(1, []) == [[0]]
