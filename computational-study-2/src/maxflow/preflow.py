"""Preflow-push algorithm: FIFO and highest-label (AMO Sections 7.6-7.8; Lecture 3, Section 7).

Building language: shortest augmenting path sends one complete group at a time. Preflow-push lets
crowds build up inside rooms first, then clears them.

1. Flood (AMO Figure 7.11a): fill every passage out of the start to capacity, and raise the start's
   label to n.
2. A room holding extra people (positive excess) is crowded, which AMO calls active. The start and
   the exit never count.
3. Visit a crowded room (a node examination, AMO Section 7.7): push people through admissible
   passages, one step closer to the exit, until the room is empty or nothing admissible is left. If
   people remain, relabel the room and put it back in line.
4. Stop when no room is crowded. Anyone who could not reach the exit has walked back to the start.

A push is saturating if it fills the passage (delta = r_ij), and non-saturating otherwise.

Which crowded room goes next is the only difference between the variants:
- rule="fifo": a queue, the room crowded longest first (AMO Section 7.7, O(n^3)).
- rule="highest": the crowded room with the highest label first (AMO Section 7.8, O(n^2 m^0.5)).
Lecture 3 teaches only the generic version; both rules are added to it (CLAUDE.md, "Report notes").

heuristics=True switches on the speed-ups of AMO pp. 229-230, which are not in Lecture 3:
- gap: when a relabel leaves label k < n with no rooms, every room with k < d < n is cut off from the
  exit, so its label jumps to n.
- global relabeling: every n relabels, rerun the backward search. Rooms that can reach the exit get
  their exact distance; rooms that cannot are raised to at least n.
Both only ever raise labels and keep them valid, so AMO's correctness and complexity arguments still
hold. This is a one-phase method: rooms at n or above keep pushing their people back to the start,
rather than being set aside for a separate return step as in AMO's two-phase description.

Passages into the start and out of the exit are kept (CLAUDE.md, "Report notes"). The exit is never
crowded, so it never pushes, and the answer is the excess at the exit: net flow into it.

This module uses only the residual network. It never imports maxflow.structure (decision DM7).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .residual import Residual, distance_labels

FIFO = "fifo"
HIGHEST = "highest"


@dataclass
class PpCounts:
    """Operation counts (docs/data_modeling.md, Section 10.2). They do not depend on the machine."""

    checks: int  # passages checked: every test of one residual record, in any part of the run
    backward_checks: int  # of which in the starting backward search
    global_checks: int  # of which in the backward searches of global relabeling
    examinations: int  # room visits (node examinations, AMO Section 7.7)
    relabels: int  # ordinary relabels
    saturating: int  # pushes that fill their passage
    nonsaturating: int  # pushes that do not (each one empties its room)
    source_pushes: int  # passages filled by the opening flood (not counted as pushes)
    movements: int  # residual pairs updated, including the flood
    walkback_pushes: int  # pushes from rooms with label >= n, which can no longer reach the exit
    walkback_relabels: int  # relabels that take a room to a label >= n
    gaps: int  # gap events
    global_relabels: int  # global relabeling events
    label_raises: int  # rooms whose label a gap or global relabel raised
    max_label: int  # highest label any room reached; always < 2n (AMO Lemma 7.12)
    checks_after_max_preflow: int  # after the last push into the exit (all of them if none)
    relabels_after_max_preflow: int
    pushes_after_max_preflow: int


@dataclass
class PpResult:
    value: int  # people per minute that reach the exit (scaled integer)
    counts: PpCounts


def preflow_push(residual: Residual, res: list[int], rule: str = FIFO, heuristics: bool = False,
                 trace: list | None = None) -> PpResult:
    """Send the most people from start to exit. Changes `res` in place.

    `res` should come from `residual.fresh()`. If `trace` is a list, the run appends events to it
    for the step-by-step walkthroughs: ("flood", s, room, people), ("push", from, to, people),
    ("relabel", room, old, new), ("gap", k, rooms raised to n) and ("global", ((room, old, new), ...)).
    Timed runs leave it as None.
    """
    if rule not in (FIFO, HIGHEST):
        raise ValueError(f"rule must be {FIFO!r} or {HIGHEST!r}, not {rule!r}")
    n, s, t = residual.n, residual.s, residual.t
    head, out = residual.head, residual.out

    d, backward_checks = distance_labels(residual, res)
    checks = backward_checks
    excess = [0] * (n + 1)
    current = [0] * (n + 1)  # current-arc pointer: a position in out[i] (AMO p. 216)
    examinations = relabels = saturating = nonsaturating = 0
    walkback_pushes = walkback_relabels = 0
    gaps = global_relabels = label_raises = global_checks = 0
    since_global = 0
    max_label = n
    at_max_preflow = (0, 0, 0)  # (checks, relabels, pushes) at the last push into the exit

    # Flood (AMO Figure 7.11a): fill every passage out of the start, then d(s) = n.
    crowded: list[int] = []  # rooms in the order they became crowded
    source_pushes = 0
    checks += len(out[s])
    for e in out[s]:
        delta = res[e]
        if delta > 0:
            j = head[e]
            res[e] = 0
            res[e ^ 1] += delta
            if excess[j] == 0 and j != t:
                crowded.append(j)
            excess[j] += delta
            excess[s] -= delta
            source_pushes += 1
            if j == t:
                at_max_preflow = (checks, 0, 0)
            if trace is not None:
                trace.append(("flood", s, j, delta))
    movements = source_pushes
    d[s] = n

    # numb for the gap heuristic: rooms_at[k] = number of rooms with label k, for k = 0..n-1.
    rooms_at = [0] * n
    if heuristics:
        for room in range(1, n + 1):
            if d[room] < n:
                rooms_at[d[room]] += 1

    # The line of crowded rooms.
    queue: deque[int] = deque()
    buckets: list[list[int]] = []
    level = 0
    if rule == FIFO:
        queue.extend(crowded)
    else:
        # One stack per label 0..2n-1 (AMO p. 233); labels stay below 2n (Lemma 7.12).
        buckets = [[] for _ in range(2 * n)]
        for room in crowded:
            buckets[d[room]].append(room)
            level = max(level, d[room])

    while True:
        # Select a crowded room.
        if rule == FIFO:
            if not queue:
                break
            i = queue.popleft()
        else:
            while level >= 0 and not buckets[level]:
                level -= 1
            if level < 0:
                break
            i = buckets[level].pop()
        examinations += 1

        # Examine it: push until it is empty or has no admissible passage left.
        records = out[i]
        size = len(records)
        di = d[i]
        target = di - 1  # an admissible passage leads to a room with this label
        ex = excess[i]
        k = current[i]
        while ex > 0:
            start = k
            while k < size:
                e = records[k]
                if res[e] > 0 and d[head[e]] == target:
                    break
                k += 1
            if k == size:
                checks += size - start
                break
            checks += k - start + 1
            j = head[e]
            r = res[e]
            delta = ex if ex < r else r
            res[e] = r - delta
            res[e ^ 1] += delta
            ex -= delta
            movements += 1
            if delta == r:
                saturating += 1
            else:
                nonsaturating += 1
            if di >= n:
                walkback_pushes += 1
            if excess[j] == 0 and j != s and j != t:
                if rule == FIFO:
                    queue.append(j)
                else:
                    buckets[d[j]].append(j)
            excess[j] += delta
            if j == t:
                at_max_preflow = (checks, relabels, saturating + nonsaturating)
            if trace is not None:
                trace.append(("push", i, j, delta))
        excess[i] = ex
        current[i] = k
        if ex == 0:
            continue

        # Relabel (Figure 7.11b). A crowded room always has a passage with space back toward the
        # start (AMO Lemma 7.11), so this minimum is never over an empty set.
        checks += size
        new = min(d[head[e]] + 1 for e in records if res[e] > 0)
        d[i] = new
        current[i] = 0
        relabels += 1
        if new >= n:
            walkback_relabels += 1
        if new > max_label:
            max_label = new
        if trace is not None:
            trace.append(("relabel", i, di, new))
        if rule == FIFO:
            queue.append(i)
        else:
            buckets[new].append(i)
            level = new

        if not heuristics:
            continue
        raised = False
        if di < n:
            rooms_at[di] -= 1
            if new < n:
                rooms_at[new] += 1
            if rooms_at[di] == 0:
                # Gap: rooms above label di cannot reach the exit (AMO p. 230), so raise them to n.
                lifted = []
                for room in range(1, n + 1):
                    if di < d[room] < n:
                        rooms_at[d[room]] -= 1
                        d[room] = n
                        current[room] = 0
                        lifted.append(room)
                gaps += 1
                label_raises += len(lifted)
                raised = raised or bool(lifted)
                if trace is not None:
                    trace.append(("gap", di, tuple(lifted)))
        since_global += 1
        if since_global == n:
            # Global relabeling (AMO p. 230): exact labels from a fresh backward search.
            since_global = 0
            exact, found = distance_labels(residual, res)
            global_checks += found
            checks += found
            global_relabels += 1
            changes = []
            for room in range(1, n + 1):
                if room == s:
                    continue
                label = exact[room] if exact[room] < n else max(d[room], n)
                if label != d[room]:
                    assert label > d[room], "valid labels are lower bounds, so they can only rise"
                    changes.append((room, d[room], label))
                    d[room] = label
                    current[room] = 0
            label_raises += len(changes)
            raised = raised or bool(changes)
            rooms_at = [0] * n
            for room in range(1, n + 1):
                if d[room] < n:
                    rooms_at[d[room]] += 1
            if trace is not None:
                trace.append(("global", tuple(changes)))
        if raised and rule == HIGHEST:
            # Labels of waiting rooms changed, so rebuild the stacks.
            buckets = [[] for _ in range(2 * n)]
            level = 0
            for room in range(1, n + 1):
                if excess[room] > 0 and room != s and room != t:
                    buckets[d[room]].append(room)
                    level = max(level, d[room])

    pushes = saturating + nonsaturating
    counts = PpCounts(
        checks=checks, backward_checks=backward_checks, global_checks=global_checks,
        examinations=examinations, relabels=relabels, saturating=saturating,
        nonsaturating=nonsaturating, source_pushes=source_pushes, movements=movements,
        walkback_pushes=walkback_pushes, walkback_relabels=walkback_relabels, gaps=gaps,
        global_relabels=global_relabels, label_raises=label_raises, max_label=max_label,
        checks_after_max_preflow=checks - at_max_preflow[0],
        relabels_after_max_preflow=relabels - at_max_preflow[1],
        pushes_after_max_preflow=pushes - at_max_preflow[2],
    )
    return PpResult(excess[t], counts)
