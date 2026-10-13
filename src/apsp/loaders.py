"""Dataset loaders. Each returns a Dataset with 0-based node ids and RAW weights (no transform).

Turning raw weights into distances is a modeling decision (see CLAUDE.md, open decisions) and
happens later, in preprocessing, never inside a loader.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@dataclass
class Dataset:
    name: str
    n: int
    u: np.ndarray  # edge sources, 0-based ints
    v: np.ndarray  # edge targets, 0-based ints
    w: np.ndarray  # raw edge weights, float
    directed: bool
    weight_meaning: str
    labels: list | None = None  # labels[i] = human-readable name of node i, if known
    source: str = ""


def compact_ids(u, v):
    """Renumber node ids to 0..n-1 in order of FIRST APPEARANCE in the edge list (reading each
    edge as source, then target). This is the same numbering KONECT uses, so our node i is
    KONECT node i + 1. Returns (u, v, original_ids) with original_ids[i] = old id of node i."""
    flat = np.column_stack([u, v]).ravel()  # u0, v0, u1, v1, ... in file order
    original_ids, first_pos = np.unique(flat, return_index=True)
    original_ids = original_ids[np.argsort(first_pos)]  # sort by where each id first appears
    new_id = {old: new for new, old in enumerate(original_ids.tolist())}
    to_new = np.vectorize(new_id.__getitem__, otypes=[np.int64])
    return to_new(u), to_new(v), original_ids


def load_usairport(raw_dir=RAW_DIR):
    """US airport network 2010 (Opsahl), from the original tnet file plus the airport-code file.

    Equivalent to KONECT opsahl-usairport (verified: identical edge list after compact_ids), but
    the original files let us label nodes with airport codes.
    Weight = number of PASSENGERS on the route in 2010 (BTS T-100). KONECT's README says
    "number of flights", which is wrong according to the original source.
    """
    folder = Path(raw_dir) / "opsahl-usairport"
    data = np.loadtxt(folder / "USairport_2010.txt")
    u, v, original_ids = compact_ids(data[:, 0].astype(np.int64), data[:, 1].astype(np.int64))

    codes = {}
    for line in (folder / "USairport_2010_codes.txt").read_text().splitlines():
        if line.strip():
            old_id, code = line.split(maxsplit=1)
            codes[int(old_id)] = code.strip('"')

    return Dataset(
        name="US Airports",
        n=len(original_ids),
        u=u,
        v=v,
        w=data[:, 2].astype(float),
        directed=True,
        weight_meaning="passengers on the route in 2010 (strength, not distance)",
        labels=[codes[i] for i in original_ids.tolist()],
        source="http://opsahl.co.uk/tnet/datasets/USairport_2010.txt (+ _codes.txt)",
    )
