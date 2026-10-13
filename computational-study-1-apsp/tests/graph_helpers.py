"""Helpers shared by the algorithm tests: random test graphs and the networkx reference answer."""

import math
import random

import networkx as nx
import numpy as np


def networkx_apsp(n, edges):
    """Reference all-pairs distances from networkx as an n x n array (inf = unreachable).

    MultiDiGraph keeps parallel edges; networkx then uses the smallest one. Bellman-Ford is used
    because, unlike Dijkstra, it is also correct when some weights are negative.
    """
    g = nx.MultiDiGraph()
    g.add_nodes_from(range(n))
    g.add_weighted_edges_from(edges)
    dist = np.full((n, n), math.inf)
    for src, lengths in nx.all_pairs_bellman_ford_path_length(g):
        for dst, d in lengths.items():
            dist[src, dst] = d
    return dist


def random_graph(seed):
    """Small random directed graph that deliberately includes the awkward cases:
    zero weights, self-loops, multi-edges, and (usually) unreachable pairs."""
    rng = random.Random(seed)
    n = rng.randint(1, 30)
    m = rng.randint(0, 3 * n)
    edges = [(rng.randrange(n), rng.randrange(n), rng.randint(0, 20)) for _ in range(m)]
    return n, edges


def random_dag_with_negative_weights(seed):
    """Random graph with some negative weights but NO cycles (every edge goes from a lower to a
    higher node number), so it cannot contain a negative cycle."""
    rng = random.Random(seed)
    n = rng.randint(2, 30)
    edges = []
    for _ in range(rng.randint(0, 3 * n)):
        u, v = sorted(rng.sample(range(n), 2))
        edges.append((u, v, rng.randint(-10, 20)))
    return n, edges
