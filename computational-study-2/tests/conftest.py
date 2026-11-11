"""Shared test pieces."""

import random
from pathlib import Path

import pytest

from maxflow.instance import DATASETS, DIRECTED, SCALE, SPARSE, TWO_WAY, Arc, Instance, read_instance

PROJECT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT / "Data"

# The 8-room mini building (docs/mini_building.md): two floors of 2 x 2 rooms, start 1, exit 8.
MINI_BUILDING = Path(__file__).resolve().parent / "data" / "mini_building.txt"

# The hand-worked best answer for the mini building, in people per minute (unscaled): four groups,
# each a route and its size, and the people they put on each arc. Together they get 9 out.
MINI_GROUPS = (((1, 6, 8), 3), ((1, 2, 5, 7, 8), 2), ((1, 3, 4, 7, 8), 3), ((1, 3, 8), 1))
MINI_HAND_FLOW = {
    (1, 6): 3, (6, 8): 3, (1, 2): 2, (2, 5): 2, (5, 7): 2,
    (7, 8): 5, (1, 3): 4, (3, 4): 3, (4, 7): 3, (3, 8): 1,
}
MINI_MAX_FLOW = 9


def arc_people(instance, people: dict[tuple[int, int], int]) -> list[int]:
    """People on each arc, in file order and scaled, from {(tail, head): unscaled people}."""
    unknown = set(people) - {(arc.tail, arc.head) for arc in instance.arcs}
    assert not unknown, f"no such arcs: {unknown}"
    return [people.get((arc.tail, arc.head), 0) * SCALE for arc in instance.arcs]


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """The real data files. They are not committed (see Data/SOURCES.md), so tests skip without them."""
    if not (DATA_DIR / "elist96.txt").exists():
        pytest.skip("data files are not present; see Data/SOURCES.md")
    return DATA_DIR


@pytest.fixture
def write_elist(tmp_path):
    """Write a small made-up data file and return its path."""

    def _write(text: str, name: str = "toy") -> Path:
        path = tmp_path / f"{name}.txt"
        path.write_bytes(text.encode("ascii"))
        return path

    return _write


@pytest.fixture
def mini():
    return read_instance(MINI_BUILDING)


def toy_building_text() -> str:
    """Three floors of 2 x 2 rooms, start room 1 on floor 1, exit room 12 on floor 3.

    Each floor's rooms (a, b, c, d) sit in a square: a-b, a-c, b-d, c-d. Corridors carry 10 both
    ways. Up stairs: floor 1 -> 2 totals 3 + 4 = 7, floor 2 -> 3 totals 2 + 2 = 4, so the narrowest
    gap is floors 2 -> 3 and the max flow is 4 (all values scaled by 10**4 when read).
    One down stair, 7 -> 2, carries 1.
    """
    lines = []
    for floor in range(3):
        a, b, c, d = (4 * floor + k for k in (1, 2, 3, 4))
        for u, v in ((a, b), (a, c), (b, d), (c, d)):
            lines += [f"{u} {v} 10", f"{v} {u} 10"]
    lines += ["1 5 3", "4 8 4", "6 10 2", "7 11 2", "7 2 1"]
    return "\r\n".join(["12", str(len(lines)), "1", "12", *lines])


# --- shared by the solver tests -------------------------------------------------------------------

# All 21 data cases: the 14 files read as directed, then the 7 sparse files read as two-way.
CASES = [(name, DIRECTED) for name in DATASETS] + [(name, TWO_WAY) for name in SPARSE]


def random_instance(rng, number):
    """A small random network: any pair of rooms may get a passage either or both ways."""
    n = rng.randint(2, 12)
    s, t = rng.sample(range(1, n + 1), 2)
    density = rng.uniform(0.1, 0.6)
    arcs = [Arc(i, j, rng.randint(1, 9)) for i in range(1, n + 1) for j in range(1, n + 1)
            if i != j and rng.random() < density]
    rng.shuffle(arcs)
    return Instance(f"random{number}", n, s, t, tuple(arcs), DIRECTED)


RANDOM = [random_instance(random.Random(seed), seed) for seed in range(300)]
