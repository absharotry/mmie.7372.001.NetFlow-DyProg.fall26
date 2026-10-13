"""Tests for preprocessing transforms and the processed-file round trip."""

import numpy as np
import pytest

from apsp.loaders import Dataset
from apsp.preprocess import inverse_weights, load_processed, save_processed
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
