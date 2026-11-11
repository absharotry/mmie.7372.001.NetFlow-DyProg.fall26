"""Check a finished answer: is it a valid flow, and is it provably the best possible?

Building language: given how many people per minute use each passage, and the claimed number
reaching the exit, check that
  1. passage limits: every passage carries between 0 and its capacity,
  2. conservation: every room except the start and the exit sends out exactly what comes in,
  3. value: the net number arriving at the exit equals the claimed answer,
  4. min-cut certificate: the rooms the start can still reach (set S) do not include the exit, and the
     passages leaving S add up to the claimed answer. A flow and a cut of the same size prove that
     both are optimal (AMO Property 6.1, Section 6.3; Theorems 6.3 and 6.4, Section 6.5).

`check_flow` works only from the original file arcs and the people on each one. It shares no logic
with the residual network or the solvers, so a bug there cannot hide itself here.

`check_residual` is a separate bookkeeping check on an algorithm's final residual values:
  5. for every passage, the space left in both directions adds up to its starting total, and no
     space is negative, so nobody went missing between the two sides.

Not checked here, because they compare several runs or references: all settings agree, the value
matches NetworkX, and on the dense files it matches the stair sum. The benchmark harness (Phase 5)
does those, using the reference values in results/data_cards.csv.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, NamedTuple, Sequence

from .instance import Instance, to_text

if TYPE_CHECKING:  # used for type hints only: no residual-network logic is shared
    from .residual import Residual


class VerificationError(ValueError):
    """An answer fails a check. The message names the check that failed."""


class Certificate(NamedTuple):
    value: int  # people per minute reaching the exit (scaled integer)
    cut_side: frozenset[int]  # S: rooms the start can still reach once the answer is in place
    cut_capacity: int  # total capacity of the passages leaving S, equal to value


def check_flow(instance: Instance, flows: Sequence[int], value: int) -> Certificate:
    """Run checks 1 to 4 on `flows` (people on each file arc, in file order, scaled integers).

    Returns the min-cut certificate if every check passes; raises VerificationError otherwise.
    """
    name, n, s, t, arcs = instance.name, instance.n, instance.s, instance.t, instance.arcs
    if len(flows) != len(arcs):
        raise VerificationError(f"{name}: length: got {len(flows)} arc flows for {len(arcs)} arcs")

    # 1. Passage limits: 0 <= x_ij <= u_ij on every arc (AMO 6.1c).
    for number, (arc, x) in enumerate(zip(arcs, flows), start=1):
        if not 0 <= x <= arc.capacity:
            raise VerificationError(
                f"{name}: passage limit: arc {number} ({arc.tail}, {arc.head}) carries {to_text(x)} "
                f"but holds 0 to {to_text(arc.capacity)}"
            )

    # 2. Conservation: in = out at every room except the start and the exit (AMO 6.1b).
    inflow = [0] * (n + 1)
    outflow = [0] * (n + 1)
    for arc, x in zip(arcs, flows):
        outflow[arc.tail] += x
        inflow[arc.head] += x
    for room in range(1, n + 1):
        if room not in (s, t) and inflow[room] != outflow[room]:
            raise VerificationError(
                f"{name}: conservation: room {room} takes in {to_text(inflow[room])} "
                f"but sends out {to_text(outflow[room])}"
            )

    # 3. Value: net people into the exit. Conservation everywhere else forces the start's net
    # outflow to be the same number, because the room balances add up to zero.
    arrived = inflow[t] - outflow[t]
    if arrived != value:
        raise VerificationError(
            f"{name}: value: net flow into exit {t} is {to_text(arrived)}, "
            f"but the answer says {to_text(value)}"
        )

    # 4. Min-cut certificate. Space left from i to j counts both ways a passage can take people:
    # unused capacity on arc (i, j), plus people on arc (j, i) who could be sent back.
    space: dict[int, dict[int, int]] = {room: {} for room in range(1, n + 1)}
    for arc, x in zip(arcs, flows):
        forward = space[arc.tail]
        forward[arc.head] = forward.get(arc.head, 0) + arc.capacity - x
        backward = space[arc.head]
        backward[arc.tail] = backward.get(arc.tail, 0) + x

    came_from = {s: s}  # rooms the start can reach through passages with space left
    queue = deque([s])
    while queue:
        room = queue.popleft()
        for nxt, left in space[room].items():
            if left > 0 and nxt not in came_from:
                came_from[nxt] = room
                queue.append(nxt)

    if t in came_from:  # an augmenting path exists, so the flow is not maximum (AMO Theorem 6.4)
        route = [t]
        while route[-1] != s:
            route.append(came_from[route[-1]])
        route.reverse()
        extra = min(space[i][j] for i, j in zip(route, route[1:]))
        raise VerificationError(
            f"{name}: not maximum: the exit can still be reached along "
            f"{' -> '.join(map(str, route))}, which has space for {to_text(extra)} more"
        )

    cut_side = frozenset(came_from)
    cut_capacity = sum(arc.capacity for arc in arcs if arc.tail in cut_side and arc.head not in cut_side)
    # With checks 1 to 3 passed and the exit unreachable, every passage leaving S is full and every
    # passage entering S is empty, so AMO equation (6.3) gives cut capacity = value. Checking it
    # anyway guards this module's own arithmetic.
    if cut_capacity != value:
        raise VerificationError(
            f"{name}: certificate: passages leaving the start's side hold {to_text(cut_capacity)}, "
            f"not {to_text(value)}"
        )
    return Certificate(value, cut_side, cut_capacity)


def check_residual(residual: Residual, res: Sequence[int]) -> None:
    """Check 5, bookkeeping: both records of every pair add up to their starting total, none negative.

    Every move of k people takes k from one record and gives k to its partner, so the pair's total
    r_ij + r_ji = u_ij + u_ji never changes (AMO Section 2.4).
    """
    capacity, head = residual.capacity, residual.head
    if len(res) != len(capacity):
        raise VerificationError(f"length: got {len(res)} residual values for {len(capacity)} records")
    for e in range(0, len(capacity), 2):
        i, j = head[e + 1], head[e]
        if res[e] < 0 or res[e + 1] < 0:
            raise VerificationError(
                f"bookkeeping: passage {i} -> {j} has negative space left "
                f"({to_text(res[e])} forward, {to_text(res[e + 1])} back)"
            )
        if res[e] + res[e + 1] != capacity[e] + capacity[e + 1]:
            raise VerificationError(
                f"bookkeeping: passage {i} <-> {j} has {to_text(res[e] + res[e + 1])} space left in "
                f"total, but started with {to_text(capacity[e] + capacity[e + 1])}"
            )
