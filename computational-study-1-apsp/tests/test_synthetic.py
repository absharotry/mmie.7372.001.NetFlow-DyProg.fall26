"""Tests for the random networks used in the density experiment."""

import numpy as np
import pytest

from apsp.synthetic import random_digraph


def test_density_close_to_p_and_no_self_loops():
    ds = random_digraph(300, 0.1, seed=1)
    assert ds.n == 300 and (ds.u != ds.v).all()
    assert len(ds.u) / (300 * 299) == pytest.approx(0.1, rel=0.05)
    assert ((ds.w >= 1) & (ds.w < 10)).all()


def test_same_seed_same_graph():
    a, b = random_digraph(100, 0.2, seed=7), random_digraph(100, 0.2, seed=7)
    assert np.array_equal(a.u, b.u) and np.array_equal(a.v, b.v) and np.array_equal(a.w, b.w)


def test_p_one_is_complete():
    ds = random_digraph(20, 1.0, seed=0)
    assert len(ds.u) == 20 * 19
