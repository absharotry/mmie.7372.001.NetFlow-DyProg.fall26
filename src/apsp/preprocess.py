"""Preprocessing: turn a loaded Dataset (raw weights) into a distance graph, and save/load it.

Every transform here implements a decision recorded in docs/decisions.md.
"""

from dataclasses import replace
from pathlib import Path

import numpy as np

from apsp.loaders import (Dataset, compact_ids, load_slashdot, load_usairport,
                          load_wikiconflict)

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def drop_isolated(ds):
    """Decision D2b: keep only nodes that appear in at least one edge, renumbered 0..n'-1 in order
    of first appearance (apsp.loaders.compact_ids). Labels, if any, follow their nodes."""
    u, v, kept = compact_ids(ds.u, ds.v)
    labels = [ds.labels[i] for i in kept.tolist()] if ds.labels is not None else None
    return replace(ds, n=len(kept), u=u, v=v, labels=labels)


def undirected_hops(ds):
    """Decisions D2 + D3: every distinct undirected pair becomes ONE edge of length 1 (sign, size and
    repeat count are discarded), stored in BOTH directions so the algorithms can use it either way.

    Self-loops are dropped: a node's distance to itself is 0 anyway.
    """
    a, b = np.minimum(ds.u, ds.v), np.maximum(ds.u, ds.v)  # {u, v} and {v, u} become the same pair
    pairs = np.unique(np.column_stack([a, b])[a != b], axis=0)
    u = np.concatenate([pairs[:, 0], pairs[:, 1]])
    v = np.concatenate([pairs[:, 1], pairs[:, 0]])
    return replace(ds, u=u, v=v, w=np.ones(len(u)), directed=False,
                   weight_meaning="hops (1 per interacting pair; sign and size ignored)")


def inverse_weights(ds):
    """Decision D1: distance = 1 / weight, so strong (busy) edges become short.

    Requires every weight > 0. A zero weight would become an infinite distance, which is the same as
    no edge, so it should have been dropped before this point (the US airport source already
    removed 0-passenger routes).
    """
    if (ds.w <= 0).any():
        raise ValueError("inverse_weights needs strictly positive weights")
    return replace(ds, w=1.0 / ds.w, weight_meaning=f"1 / ({ds.weight_meaning})")


def friends_only_hops(ds):
    """Decision D4: keep only positive ("friend") edges, each of length 1, direction kept.

    Foe edges are removed entirely, so no negative weights (and no negative cycles) remain.
    """
    keep = ds.w > 0
    return replace(ds, u=ds.u[keep], v=ds.v[keep], w=np.ones(int(keep.sum())),
                   weight_meaning="hops along friend tags (foe tags removed)")


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


# slug -> (loader, preprocessing steps in order). Each step implements a logged decision.
PIPELINES = {
    "usairport": (load_usairport, [inverse_weights]),  # D1
    "wikiconflict": (load_wikiconflict, [drop_isolated, undirected_hops]),  # D2b, then D2 + D3
    "slashdot": (load_slashdot, [friends_only_hops, drop_isolated]),  # D4, then D4b
}


def build(slug):
    """Load the raw dataset and apply its preprocessing steps. Returns (raw, processed)."""
    loader, steps = PIPELINES[slug]
    raw = ds = loader()
    for step in steps:
        ds = step(ds)
    return raw, ds
