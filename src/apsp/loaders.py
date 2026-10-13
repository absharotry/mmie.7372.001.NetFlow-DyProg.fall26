"""Dataset loaders. Each returns a Dataset with 0-based node ids and RAW weights (no transform).

Turning raw weights into distances is a modeling decision (see CLAUDE.md, open decisions) and
happens later, in preprocessing, never inside a loader.
"""

import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@dataclass
class Dataset:
    name: str
    n: int
    u: np.ndarray  # edge sources, 0-based ints
    v: np.ndarray  # edge targets, 0-based ints
    w: np.ndarray  # raw edge weights, float
    # directed=False means every edge works both ways. The edge list may store each pair once
    # (raw files) or in both directions (processed files); see apsp.preprocess.
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
        weight_meaning="passengers on the route in 2010",  # a strength, not a distance
        labels=[codes[i] for i in original_ids.tolist()],
        source="http://opsahl.co.uk/tnet/datasets/USairport_2010.txt (+ _codes.txt)",
    )


def load_wikiconflict(raw_dir=RAW_DIR):
    """Wikipedia conflict network (KONECT wikiconflict), RAW: every interaction row, signed weights.

    Undirected; each pair is stored once with u < v. Ids are shifted to 0-based but NOT compacted, so
    n = 118,100 including 1,264 ids with no edges (dropping them is decision D2b, in preprocessing).
    Weight = sign * ln(k): + agreement, - disagreement/revert; what k counts is undocumented.
    The timestamp column is not loaded (no decision uses it).
    The file's "%" header claims 2,985,759 edges; the file and KONECT's website have 2,917,785.
    """
    path = Path(raw_dir) / "wikiconflict" / "out.wikiconflict"
    # pandas' C parser reads the 120 MB file in about a second (np.loadtxt is far slower).
    df = pd.read_csv(path, sep=r"\s+", comment="%", header=None, usecols=[0, 1, 2],
                     names=["u", "v", "w"], dtype={"u": np.int64, "v": np.int64, "w": float})
    return Dataset(
        name="Wiki Conflict",
        n=118_100,  # from the header line "% 2985759 118100 118100"
        u=df["u"].to_numpy() - 1,
        v=df["v"].to_numpy() - 1,
        w=df["w"].to_numpy(),
        directed=False,
        weight_meaning="sign * ln(k): + agreement, - disagreement (k undocumented)",
        source="http://konect.cc/networks/wikiconflict",
    )


def load_slashdot(raw_dir=RAW_DIR):
    """Slashdot Zoo friend/foe network (Netzschleuder slashdot_zoo = KONECT slashdot-zoo), RAW.

    Directed: u -> v means "u tagged v". Weight +1 = friend, -1 = foe. Ids are already 0-based.
    Read straight from the downloaded zip (its SHA-256 is in data/SOURCES.md), so the loader does
    not depend on an unzipped copy.
    """
    path = Path(raw_dir) / "slashdot_zoo" / "slashdot_zoo.csv.zip"
    with zipfile.ZipFile(path) as zf, zf.open("edges.csv") as f:
        df = pd.read_csv(f, comment="#", header=None, names=["u", "v", "w"],
                         dtype={"u": np.int64, "v": np.int64, "w": float})
    return Dataset(
        name="Slashdot Zoo",
        n=79_120,  # Netzschleuder num_vertices; 4 ids have no edges
        u=df["u"].to_numpy(),
        v=df["v"].to_numpy(),
        w=df["w"].to_numpy(),
        directed=True,
        weight_meaning="+1 friend, -1 foe",
        source="https://networks.skewed.de/net/slashdot_zoo/files/slashdot_zoo.csv.zip",
    )
