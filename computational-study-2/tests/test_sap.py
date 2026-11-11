"""Tests for the shortest augmenting path algorithm: hand traces, AMO's example, NetworkX, real data."""

from pathlib import Path

import pytest
from conftest import CASES, MINI_MAX_FLOW, RANDOM

from maxflow.instance import SCALE, read_instance
from maxflow.residual import arc_flows, build_residual, flow_value
from maxflow.sap import STOP_LABEL, shortest_augmenting_path
from maxflow.structure import reference_max_flow
from maxflow.verify import check_flow, check_residual

DATA = Path(__file__).resolve().parent / "data"


def solve(inst, numb, trace=None):
    """Run SAP from fresh residual values and verify the answer. Returns (result, residual values)."""
    residual = build_residual(inst)
    res = residual.fresh()
    result = shortest_augmenting_path(residual, res, numb=numb, trace=trace)
    check_residual(residual, res)
    check_flow(inst, arc_flows(residual, res), result.value)
    assert flow_value(residual, res) == result.value
    return result, res


def events(trace):
    """Trace events with people unscaled: ("augment", route, people) or ("relabel", room, old, new)."""
    readable = []
    for event in trace:
        if event[0] == "augment":
            kind, route, people = event
            readable.append((kind, route, people // SCALE))
        else:
            readable.append(event)
    return readable


def augment(*route_and_people):
    *route, people = route_and_people
    return ("augment", tuple(route), people)


def relabel(room, old, new):
    return ("relabel", room, old, new)


# --- the mini building: the hand trace in docs/mini_building.md --------------------------------

MINI_UNTIL_GAP = [
    augment(1, 3, 8, 1), relabel(3, 1, 3),
    augment(1, 6, 8, 3), relabel(1, 2, 4),
    augment(1, 2, 4, 7, 8, 3), relabel(4, 2, 4),
    augment(1, 2, 5, 6, 8, 2),  # all four up stairs are full: 9 out
    relabel(2, 3, 5), relabel(3, 3, 5),  # no room is left at distance 3
]
MINI_AS_TAUGHT = MINI_UNTIL_GAP + [
    relabel(1, 4, 6), relabel(4, 4, 6), relabel(2, 5, 7), relabel(3, 5, 7), relabel(1, 6, 8),  # d(1) = n
]


def test_mini_with_numb(mini):
    trace = []
    result, _ = solve(mini, numb=True, trace=trace)
    assert events(trace) == MINI_UNTIL_GAP
    assert result.value == MINI_MAX_FLOW * SCALE
    assert result.stop == "gap at label 3"
    c = result.counts
    assert (c.augmentations, c.relabels, c.advances, c.retreats, c.movements) == (4, 5, 16, 3, 12)
    assert c.relabels_after_last == 2
    assert c.backward_checks == 28  # every record once: each room's list is scanned once
    assert (c.checks, c.checks_after_last) == (81, 13)


def test_mini_as_taught(mini):
    trace = []
    result, _ = solve(mini, numb=False, trace=trace)
    assert events(trace) == MINI_AS_TAUGHT
    assert result.stop == STOP_LABEL
    c = result.counts
    assert (c.augmentations, c.relabels, c.advances, c.retreats, c.movements) == (4, 10, 19, 7, 12)
    assert c.relabels_after_last == 7  # 7 of the 10 relabels come after everyone is already out
    assert (c.checks, c.backward_checks, c.checks_after_last) == (119, 28, 51)


# --- AMO Figure 7.4: what the book says happens (pp. 213-214 and 219-220) -------------------

AMO_GROUPS = [augment(1, j, j + 5, 12, 1) for j in (2, 3, 4, 5, 6)]


@pytest.fixture
def amo():
    return read_instance(DATA / "amo_figure_7_4.txt")


def test_amo_figure_7_4_with_numb(amo):
    """'... it constructs the partial admissible path 1-6. Next it relabels node 6 and its distance
    label increases from 2 to 4. The algorithm finds that numb(2) = 0 and it terminates.'"""
    trace = []
    result, _ = solve(amo, numb=True, trace=trace)
    assert [e for e in events(trace) if e[0] == "augment"] == AMO_GROUPS
    assert events(trace)[:2] == [AMO_GROUPS[0], relabel(2, 2, 4)]  # d(2) rises to 4 after the first group
    assert events(trace)[-1] == relabel(6, 2, 4)
    assert result.stop == "gap at label 2"
    assert result.counts.relabels_after_last == 1


def test_amo_figure_7_4_as_taught(amo):
    """'... the algorithm would increase the distance labels of nodes 6, 1, 2, 3, 4, 5, in the given
    order, each time by 2 units. Eventually, d(1) >= 12 and the algorithm terminates.'"""
    trace = []
    result, _ = solve(amo, numb=False, trace=trace)
    after = events(trace)[events(trace).index(AMO_GROUPS[-1]) + 1:]
    assert after[:6] == [relabel(6, 2, 4), relabel(1, 3, 5), relabel(2, 4, 6),
                         relabel(3, 4, 6), relabel(4, 4, 6), relabel(5, 4, 6)]
    assert [room for _, room, *_ in after] == [6, 1, 2, 3, 4, 5] * 4 + [6, 1]
    assert after[-1] == relabel(1, 11, 13)
    assert result.stop == STOP_LABEL
    assert result.counts.relabels_after_last == 26


# --- rules that hold on every network --------------------------------------------------------

def test_random_networks_cover_the_awkward_cases():
    def two_way(inst):
        pairs = {(a.tail, a.head) for a in inst.arcs}
        return any((j, i) in pairs for i, j in pairs)

    assert sum(reference_max_flow(inst) == 0 for inst in RANDOM) >= 20  # exit cannot be reached
    assert sum(two_way(inst) for inst in RANDOM) >= 200  # passages listed both ways
    assert sum(any(a.head == inst.s for a in inst.arcs) for inst in RANDOM) >= 200  # into the start
    assert sum(any(a.tail == inst.t for a in inst.arcs) for inst in RANDOM) >= 200  # out of the exit


@pytest.mark.parametrize("inst", RANDOM, ids=lambda inst: inst.name)
def test_random_network_matches_networkx(inst):
    taught_trace, numb_trace = [], []
    taught, _ = solve(inst, numb=False, trace=taught_trace)
    with_numb, _ = solve(inst, numb=True, trace=numb_trace)
    assert taught.value == with_numb.value == reference_max_flow(inst)

    # numb only adds a stopping test, so its run is the first part of the as-taught run.
    assert taught_trace[:len(numb_trace)] == numb_trace
    for field in ("checks", "relabels", "advances", "retreats"):
        assert getattr(with_numb.counts, field) <= getattr(taught.counts, field)
    assert with_numb.counts.augmentations == taught.counts.augmentations

    # Counter bookkeeping.
    c = taught.counts
    routes = [e[1] for e in taught_trace if e[0] == "augment"]
    assert c.movements == sum(len(route) - 1 for route in routes)
    assert c.advances == c.movements + c.retreats  # the run ends at the start, so every step was undone or used
    assert c.relabels == sum(e[0] == "relabel" for e in taught_trace)
    assert c.backward_checks <= c.checks and c.relabels_after_last <= c.relabels
    # Routes never get shorter (a consequence of AMO Lemma 7.5).
    assert all(len(a) <= len(b) for a, b in zip(routes, routes[1:]))


def test_rerun_from_fresh_gives_the_same_run(mini):
    first, res1 = solve(mini, numb=False)
    second, res2 = solve(mini, numb=False)
    assert first == second and res1 == res2


def test_solver_never_uses_analysis_or_checking_code():
    """Decision DM7: the solver sees only the residual network, never floors or references."""
    source = (Path(__file__).resolve().parents[1] / "src" / "maxflow" / "sap.py").read_text()
    imports = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
    assert not [line for line in imports if any(w in line for w in ("structure", "verify", "networkx"))]


# --- the real data: all 21 cases ---------------------------------------------------------------

@pytest.mark.parametrize("name, reading", CASES)
def test_real_data(data_dir, name, reading):
    inst = read_instance(data_dir / f"{name}.txt", reading)
    expected = reference_max_flow(inst)
    for numb in (False, True):
        result, _ = solve(inst, numb=numb)
        assert result.value == expected
        if expected == 0:
            # The backward search never reaches the start, so d(s) = n and nothing else happens.
            c = result.counts
            assert result.stop == STOP_LABEL
            assert (c.augmentations, c.relabels, c.advances) == (0, 0, 0)
            assert c.checks == c.backward_checks
