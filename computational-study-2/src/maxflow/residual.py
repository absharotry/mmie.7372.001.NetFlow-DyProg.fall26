"""The residual network that both algorithms share: how much room is left on each passage, each way.

Building language: for every pair of rooms joined by a passage in either direction, we keep two
numbers, "space left going i -> j" and "space left going j -> i". This is AMO's residual network with
one pair of records per node pair (AMO Assumption 6.4, Section 2.4):

    r_ij = u_ij - x_ij + x_ji

Records are numbered in pairs: 0 and 1, 2 and 3, and so on. Record e and record e ^ 1 (flip the last
bit) are the two directions of one passage. Sending k people along record e is two updates:

    res[e] -= k          # less space left going forward
    res[e ^ 1] += k      # those k people could be sent back

The structure (which rooms, which passages, the starting capacities) never changes after it is built,
so it is stored in tuples. The residual values change while an algorithm runs, so they live in a
separate plain list that `fresh()` hands out. Build once per data case (untimed); call `fresh()`
before every timed run, because the algorithms change the values (CLAUDE.md, "Known pitfalls").

Both readings use this code unchanged. In the two-way reading the reader has already turned every
edge into two arcs (i, j) and (j, i) of capacity u, and they land in one pair with r = u each way.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, replace

from .instance import Instance


@dataclass(frozen=True, eq=False)
class Residual:
    """The fixed shape of the residual network. Room numbers are those in the file (1..n)."""

    n: int
    s: int
    t: int
    head: tuple[int, ...]  # head[e]: the room record e leads to
    capacity: tuple[int, ...]  # capacity[e]: the file's capacity that way, 0 if the file has no such arc
    out: tuple[tuple[int, ...], ...]  # out[i]: records leaving room i, in file order; out[0] is unused
    arc_record: tuple[int, ...]  # arc_record[k]: the record of the file's k-th arc (0-based)

    @property
    def records(self) -> int:
        """Number of residual records: 2 x (node pairs joined by at least one arc)."""
        return len(self.head)

    def tail(self, e: int) -> int:
        """The room record e leaves. Its partner e ^ 1 leads back there."""
        return self.head[e ^ 1]

    def fresh(self) -> list[int]:
        """Starting residual values: nobody has moved yet, so space left equals capacity."""
        return list(self.capacity)


def build_residual(instance: Instance) -> Residual:
    """Turn the file's arcs into residual records, in file order (the baseline arc order, DM8).

    The first arc between two rooms creates the pair: record e for its own direction (added to the
    tail room's list) and record e + 1 for the way back (added to the head room's list). If the file
    later lists the opposite arc, it fills in the capacity of the existing way-back record, so
    antiparallel arcs share one pair (Assumption 6.4) and start with r_ij = u_ij and r_ji = u_ji.
    """
    head: list[int] = []
    capacity: list[int] = []
    out: list[list[int]] = [[] for _ in range(instance.n + 1)]
    record_of: dict[tuple[int, int], int] = {}  # (from room, to room) -> record
    arc_record: list[int] = []

    for arc in instance.arcs:
        e = record_of.get((arc.tail, arc.head))
        if e is None:
            e = len(head)
            head += [arc.head, arc.tail]
            capacity += [0, 0]
            out[arc.tail].append(e)
            out[arc.head].append(e + 1)
            record_of[(arc.tail, arc.head)] = e
            record_of[(arc.head, arc.tail)] = e + 1
        elif capacity[e]:
            # The reader rejects repeated arcs; this guards instances built some other way.
            raise ValueError(f"arc ({arc.tail}, {arc.head}) is listed twice (AMO Assumption 6.5)")
        capacity[e] = arc.capacity
        arc_record.append(e)

    return Residual(
        n=instance.n,
        s=instance.s,
        t=instance.t,
        head=tuple(head),
        capacity=tuple(capacity),
        out=tuple(tuple(records) for records in out),
        arc_record=tuple(arc_record),
    )


def arc_flows(residual: Residual, res: list[int]) -> list[int]:
    """People on each file arc, in file order: x_ij = max(u_ij - r_ij, 0).

    u_ij - r_ij equals x_ij - x_ji, the net number sent from i to j. When it is positive it all goes on
    arc (i, j); when it is negative the arc carries nobody and its partner carries the rest. So at most
    one direction of a pair comes out positive, which is a valid way to describe the same movement.
    """
    capacity = residual.capacity
    return [max(capacity[e] - res[e], 0) for e in residual.arc_record]


def flow_value(residual: Residual, res: list[int]) -> int:
    """Net people per minute into the exit: the sum over records leaving t of (r - u).

    For a record t -> j, r_tj - u_tj = x_jt - x_tj, the net number that came into t from j. Arcs out of
    the exit are kept (the dense files have some), so this is net flow, as the report notes say.
    """
    capacity = residual.capacity
    return sum(res[e] - capacity[e] for e in residual.out[residual.t])


def distance_labels(residual: Residual, res: list[int]) -> tuple[list[int], int]:
    """Exact distance labels: the fewest passages with space left from each room to the exit.

    Backward breadth-first search from the exit (AMO Figure 7.5, line 3; Figure 7.11a). Room i is one
    step further than room j if passage i -> j has space. Room j's list holds the record j -> i, and
    its partner e ^ 1 is the record i -> j. Rooms that cannot reach the exit get n (CLAUDE.md, "Known
    pitfalls"). Both algorithms call this, so their starting labels come from identical code.

    Returns the labels (index 0 unused) and the number of records checked.
    """
    n, t, head, out = residual.n, residual.t, residual.head, residual.out
    d = [n] * (n + 1)
    d[t] = 0
    queue = deque([t])
    checks = 0
    while queue:
        j = queue.popleft()
        records = out[j]
        checks += len(records)
        for e in records:
            i = head[e]
            if d[i] == n and res[e ^ 1] > 0:
                d[i] = d[j] + 1
                queue.append(i)
    return d, checks


def shuffle_rooms(residual: Residual, seed: int) -> Residual:
    """The same network with each room's door list in a random order fixed by `seed` (Phase 6).

    Both algorithms try a room's passages in list order, so the order can make either one luckier on
    the same building. Only the order changes: the rooms, passages, capacities and record numbers stay
    the same, so every answer and every check is unaffected.
    """
    rng = random.Random(seed)
    rooms = []
    for records in residual.out:
        records = list(records)
        rng.shuffle(records)
        rooms.append(tuple(records))
    return replace(residual, out=tuple(rooms))
