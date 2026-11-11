"""Shortest augmenting path algorithm (AMO Section 7.4, Figures 7.5 and 7.6; Lecture 3, Section 6).

Building language: every room carries a distance label d(i), an estimate of how many passages it
takes to reach the exit. A passage i -> j is admissible (usable now) if it has space left and
d(i) = d(j) + 1, so it leads one step closer. Starting from the start room, the algorithm grows a
route one passage at a time:

- advance: the current room has an admissible passage, so step through it. On reaching the exit,
  send as many people as the tightest passage allows (augment) and start again from the start.
- retreat: the current room has none, so its estimate was too low. Relabel it to
  1 + the smallest label among rooms it still has space to reach, then step back one room.

It stops when d(start) >= n (as taught), because then no route from start to exit has space
(AMO Property 7.2). With `numb=True` it also stops as soon as some distance k < n has no rooms left:
the rooms above the gap form a minimum cut (AMO pp. 219-220). This is a speed-up that is not in
Lecture 3, so the "as taught" results have it off.

Implementation notes (also in CLAUDE.md, "Report notes"):
- Current-arc pointers (AMO p. 216): each room remembers where it stopped scanning its list and goes
  back to the top only after a relabel. This gives the O(n^2 m) bound (AMO Theorem 7.10).
- A relabel over an empty set (no passage out with space left) gives n, meaning "cannot reach the
  exit". AMO's formula leaves this case undefined; n keeps the labels valid.
- pred[j] stores the record used to enter room j, not just the previous room. With one pair of
  records per pair of rooms (Assumption 6.4) both carry the same information.

This module uses only the residual network. It never imports maxflow.structure (decision DM7).
"""

from __future__ import annotations

from dataclasses import dataclass

from .residual import Residual, distance_labels

STOP_LABEL = "d(s) >= n"  # the as-taught stopping rule (AMO Figure 7.5)


@dataclass
class SapCounts:
    """Operation counts (docs/data_modeling.md, Section 10.2). They do not depend on the machine."""

    checks: int  # passages checked: every test of one residual record, in any part of the run
    backward_checks: int  # of which in the initial backward search from the exit
    relabels: int  # room re-estimates
    advances: int  # steps forward
    retreats: int  # steps back (a relabel at the start room is not a retreat)
    augmentations: int  # groups sent
    movements: int  # residual pairs updated: the total length of all routes used
    checks_after_last: int  # passages checked after the last group was sent (all of them if none)
    relabels_after_last: int  # relabels after the last group was sent


@dataclass
class SapResult:
    value: int  # people per minute that reach the exit (scaled integer)
    stop: str  # STOP_LABEL, or "gap at label k" when numb found an empty distance k
    counts: SapCounts


def shortest_augmenting_path(residual: Residual, res: list[int], numb: bool = False,
                             trace: list | None = None) -> SapResult:
    """Send the most people from start to exit. Changes `res` in place.

    `res` should come from `residual.fresh()`. If `trace` is a list, the run appends
    ("augment", route, people) and ("relabel", room, old label, new label) events to it, for the
    step-by-step walkthroughs. Timed runs leave it as None.
    """
    n, s, t = residual.n, residual.s, residual.t
    head, out = residual.head, residual.out

    # Exact distance labels from a backward search from the exit (AMO Figure 7.5, line 3). Rooms that
    # cannot reach the exit get n.
    d, backward_checks = distance_labels(residual, res)

    # numb: rooms_at[k] is AMO's numb(k), the number of rooms with label k, for k = 0..n-1 (p. 220).
    rooms_at = [0] * n
    if numb:
        for room in range(1, n + 1):
            if d[room] < n:
                rooms_at[d[room]] += 1

    current = [0] * (n + 1)  # current-arc pointer: a position in out[i]
    pred = [0] * (n + 1)  # pred[j]: the record used to enter room j on the route being built
    value = 0
    checks = backward_checks
    relabels = advances = retreats = augmentations = movements = 0
    checks_at_last = relabels_at_last = 0
    stop = STOP_LABEL

    i = s
    while d[s] < n:
        records = out[i]
        size = len(records)
        start = current[i]
        k = start
        target = d[i] - 1  # an admissible passage leads to a room with this label
        while k < size:
            e = records[k]
            if res[e] > 0 and d[head[e]] == target:
                break
            k += 1

        if k < size:
            # Advance (AMO Figure 7.6a).
            checks += k - start + 1
            current[i] = k
            i = head[e]
            pred[i] = e
            advances += 1
            if i == t:
                # Augment (Figure 7.6c): the route is found by walking back along pred.
                delta = res[pred[t]]
                j = t
                while j != s:
                    e = pred[j]
                    if res[e] < delta:
                        delta = res[e]
                    j = head[e ^ 1]
                j = t
                while j != s:
                    e = pred[j]
                    res[e] -= delta
                    res[e ^ 1] += delta
                    movements += 1
                    j = head[e ^ 1]
                value += delta
                augmentations += 1
                checks_at_last, relabels_at_last = checks, relabels
                if trace is not None:
                    route = [t]
                    while route[-1] != s:
                        route.append(head[pred[route[-1]] ^ 1])
                    trace.append(("augment", tuple(reversed(route)), delta))
                i = s
        else:
            # Retreat (Figure 7.6b): relabel, then step back one room unless at the start.
            checks += size - start + size  # the rest of the scan, then the relabel looks at every passage
            new = min((d[head[e]] + 1 for e in records if res[e] > 0), default=n)
            old = d[i]
            d[i] = new
            current[i] = 0
            relabels += 1
            if trace is not None:
                trace.append(("relabel", i, old, new))
            if numb:
                # old < n here: rooms on the route have labels at most d(s) < n (AMO Lemma 7.9 proof).
                rooms_at[old] -= 1
                if new < n:
                    rooms_at[new] += 1
                if rooms_at[old] == 0:
                    stop = f"gap at label {old}"
                    break
            if i != s:
                i = head[pred[i] ^ 1]
                retreats += 1

    counts = SapCounts(
        checks=checks, backward_checks=backward_checks, relabels=relabels, advances=advances,
        retreats=retreats, augmentations=augmentations, movements=movements,
        checks_after_last=checks - checks_at_last, relabels_after_last=relabels - relabels_at_last,
    )
    return SapResult(value, stop, counts)
