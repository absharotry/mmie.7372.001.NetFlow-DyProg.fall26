"""Shared test graphs."""

import math

import pytest

INF = math.inf

# The hand-checkable toy graph from scripts/demo_toolchain.py, with A..E renamed to 0..4.
# Edge A->B appears twice (weights 4 and 10) to exercise multi-edge handling.
TOY_N = 5
TOY_EDGES = [
    (0, 1, 4),  # A->B
    (0, 2, 1),  # A->C
    (2, 1, 2),  # C->B
    (1, 3, 1),  # B->D
    (2, 3, 5),  # C->D
    (3, 4, 3),  # D->E
    (0, 1, 10),  # A->B duplicate, worse weight
]
# Worked out by hand (row = source, column = target).
TOY_EXPECTED = [
    [0, 3, 1, 4, 7],
    [INF, 0, INF, 1, 4],
    [INF, 2, 0, 3, 6],
    [INF, INF, INF, 0, 3],
    [INF, INF, INF, INF, 0],
]


@pytest.fixture
def toy_graph():
    return TOY_N, TOY_EDGES, TOY_EXPECTED
