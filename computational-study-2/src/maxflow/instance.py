"""Read one elist data file into a checked list of arcs.

Building language (docs/plan_of_action.md, Section 5): rooms are nodes, passages are arcs, the start
room is the source s and the exit room is the sink t. Capacity ("people per minute") has no units.

Decisions applied here (docs/data_modeling.md, Section 9):
- DM1: every file is used exactly as given and read as directed.
- DM2, DM3: the two-way reading is a separate option, allowed only for files with no two-way pairs.
- DM4: capacities become exact integers by multiplying by 10**4, which meets AMO Assumption 6.2.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NamedTuple

# Every capacity in the data has at most 4 decimal places, so this makes all of them whole numbers.
SCALE = 10_000

DIRECTED = "directed"
TWO_WAY = "two-way"

SIZES = (96, 160, 200, 500, 640, 960, 1440)
SPARSE = tuple(f"elist{size}" for size in SIZES)
DENSE = tuple(f"elist{size}d" for size in SIZES if size != 1440)  # the 6 files that carry flow
DATASETS = tuple(name for size in SIZES for name in (f"elist{size}", f"elist{size}d"))


class DataError(ValueError):
    """A data file breaks a rule the study relies on. The message names the rule."""


class Arc(NamedTuple):
    tail: int  # room the passage leaves
    head: int  # room the passage enters
    capacity: int  # exact integer: the file's capacity times SCALE


class Instance(NamedTuple):
    name: str
    n: int  # number of rooms
    s: int  # start room (source)
    t: int  # exit room (sink)
    arcs: tuple[Arc, ...]  # in file order, which is the baseline arc order (DM8)
    reading: str  # DIRECTED or TWO_WAY

    @property
    def m(self) -> int:
        """Number of arcs the algorithms will see."""
        return len(self.arcs)


def parse_capacity(text: str) -> int:
    """Turn capacity text into an exact integer (times SCALE), without any floating-point step.

    The files mix formats such as '3.200100e+00', '3.20010' and '8.86000E-02'. Decimal reads all of
    them exactly, so 3.2001 becomes exactly 32001. Rounding is never used: a value that is not a
    whole number after scaling is an error.
    """
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise DataError(f"capacity {text!r} is not a number") from None
    if not value.is_finite():
        raise DataError(f"capacity {text!r} is not a finite number")
    scaled = value * SCALE
    if scaled != scaled.to_integral_value():
        raise DataError(f"capacity {text!r} has more than 4 decimal places")
    if scaled <= 0:
        raise DataError(f"capacity {text!r} is not positive")
    return int(scaled)


def to_text(scaled: int) -> str:
    """Show a scaled integer in the file's own units, for example 13784 -> '1.3784', 0 -> '0'."""
    return format((Decimal(scaled) / SCALE).normalize(), "f")


def _parse_int(text: str, what: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise DataError(f"{what} {text!r} is not a whole number") from None


def parse_elist(text: str, name: str) -> Instance:
    """Read the text of one file and audit it (docs/data_modeling.md, Section 3).

    Format: n, m, s, t, then one 'tail head capacity' triple per arc. Values are split on any
    whitespace, so irregular spacing and CRLF line endings do not matter.
    """
    tokens = text.split()
    if len(tokens) < 4:
        raise DataError(f"{name}: the header needs four numbers: n, m, s and t")
    n = _parse_int(tokens[0], "room count n")
    m = _parse_int(tokens[1], "arc count m")
    s = _parse_int(tokens[2], "start room s")
    t = _parse_int(tokens[3], "exit room t")
    if n < 2:
        raise DataError(f"{name}: needs at least 2 rooms, header says {n}")
    if not (1 <= s <= n and 1 <= t <= n):
        raise DataError(f"{name}: start {s} or exit {t} is outside rooms 1..{n}")
    if s == t:
        raise DataError(f"{name}: start and exit are the same room {s}")

    body = tokens[4:]
    if len(body) % 3:
        raise DataError(f"{name}: every arc needs 3 values (tail head capacity); {len(body) % 3} left over")
    if len(body) // 3 != m:
        raise DataError(f"{name}: header says {m} arcs but the file lists {len(body) // 3}")

    arcs: list[Arc] = []
    seen: set[tuple[int, int]] = set()
    for i in range(0, len(body), 3):
        number = i // 3 + 1
        u = _parse_int(body[i], f"arc {number} tail")
        v = _parse_int(body[i + 1], f"arc {number} head")
        if not (1 <= u <= n and 1 <= v <= n):
            raise DataError(f"{name}: arc {number} ({u}, {v}) uses a room outside 1..{n}")
        if u == v:
            raise DataError(f"{name}: arc {number} is a self-loop at room {u}")
        if (u, v) in seen:
            raise DataError(f"{name}: arc {number} ({u}, {v}) is listed twice (AMO Assumption 6.5)")
        seen.add((u, v))
        try:
            capacity = parse_capacity(body[i + 2])
        except DataError as err:
            raise DataError(f"{name}: arc {number} ({u}, {v}): {err}") from None
        arcs.append(Arc(u, v, capacity))
    return Instance(name, n, s, t, tuple(arcs), DIRECTED)


def to_two_way(instance: Instance) -> Instance:
    """Read every passage as usable in both directions (AMO Section 2.4, p. 39).

    Each edge {i, j} of capacity u becomes arcs (i, j) and (j, i), both of capacity u. Flows in
    opposite directions cancel, so at most u people per minute cross in net. The new arcs follow
    file order, each forward arc followed by its reverse.

    Allowed only when no node pair is already listed in both directions (DM3): such a pair would
    need a rule for combining two capacities, and the data does not give one.
    """
    if instance.reading != DIRECTED:
        raise ValueError(f"{instance.name} is already read as {instance.reading}")
    pairs = {(arc.tail, arc.head) for arc in instance.arcs}
    doubled = sum(1 for (u, v) in pairs if u < v and (v, u) in pairs)
    if doubled:
        raise DataError(
            f"{instance.name} already lists {doubled} node pairs in both directions; reading it as "
            "two-way would need a rule for combining their capacities (DM3)"
        )
    arcs: list[Arc] = []
    for arc in instance.arcs:
        arcs.append(arc)
        arcs.append(Arc(arc.head, arc.tail, arc.capacity))
    return instance._replace(arcs=tuple(arcs), reading=TWO_WAY)


def read_instance(path: str | Path, reading: str = DIRECTED) -> Instance:
    """Read and audit one data file, in the directed reading (default) or the two-way reading."""
    path = Path(path)
    instance = parse_elist(path.read_text(encoding="ascii"), path.stem)
    if reading == DIRECTED:
        return instance
    if reading == TWO_WAY:
        return to_two_way(instance)
    raise ValueError(f"unknown reading {reading!r}; use {DIRECTED!r} or {TWO_WAY!r}")
