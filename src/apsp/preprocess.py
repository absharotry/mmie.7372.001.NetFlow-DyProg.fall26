"""Preprocessing: turn a loaded Dataset (raw weights) into a distance graph, and save/load it.

Every transform here implements a decision recorded in docs/decisions.md.
"""

from dataclasses import replace
from pathlib import Path

import numpy as np

from apsp.loaders import Dataset

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def inverse_weights(ds):
    """Decision D1: distance = 1 / weight, so strong (busy) edges become short.

    Requires every weight > 0. A zero weight would become an infinite distance, which is the same as
    no edge, so it should have been dropped before this point (the US airport source already
    removed 0-passenger routes).
    """
    if (ds.w <= 0).any():
        raise ValueError("inverse_weights needs strictly positive weights")
    return replace(ds, w=1.0 / ds.w, weight_meaning=f"1 / ({ds.weight_meaning})")


def save_processed(ds, slug, folder=PROCESSED_DIR):
    """Save a processed Dataset as a compressed .npz (exact float64 values, fast to reload)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{slug}.npz"
    np.savez_compressed(
        path, n=ds.n, u=ds.u, v=ds.v, w=ds.w, directed=ds.directed,
        name=ds.name, weight_meaning=ds.weight_meaning, source=ds.source,
        labels=np.array(ds.labels if ds.labels is not None else [], dtype=str),
    )
    return path


def load_processed(slug, folder=PROCESSED_DIR):
    with np.load(Path(folder) / f"{slug}.npz") as f:
        labels = f["labels"].tolist() or None
        return Dataset(
            name=str(f["name"]), n=int(f["n"]), u=f["u"], v=f["v"], w=f["w"],
            directed=bool(f["directed"]), weight_meaning=str(f["weight_meaning"]),
            labels=labels, source=str(f["source"]),
        )
