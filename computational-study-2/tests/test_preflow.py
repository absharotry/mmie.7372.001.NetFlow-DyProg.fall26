"""Tests for preflow-push: hand trace, AMO's bad example for FIFO, NetworkX, and all six settings agreeing."""

from pathlib import Path

import pytest
from conftest import CASES, MINI_MAX_FLOW, RANDOM

from maxflow.instance import SCALE, read_instance
from maxflow.preflow import FIFO, HIGHEST, preflow_push
from maxflow.residual import arc_flows, build_residual, flow_value
from maxflow.sap import shortest_augmenting_path
from maxflow.structure import reference_max_flow
from maxflow.verify import check_flow, check_residual

DATA = Path(__file__).resolve().parent / "data"
SETTINGS = [(FIFO, False), (FIFO, True), (HIGHEST, False), (HIGHEST, True)]


def solve(inst, rule, heuristics, trace=None):
    """Run preflow-push from fresh residual values and verify the answer."""
    residual = build_residual(inst)
    res = residual.fresh()
    result = preflow_push(residual, res, rule=rule, heuristics=heuristics, trace=trace)
    check_residual(residual, res)
    check_flow(inst, arc_flows(residual, res), result.value)
    assert flow_value(residual, res) == result.value
    return result


def events(trace):
    """Trace events with people unscaled."""
    readable = []
    for event in trace:
        if event[0] in ("flood", "push"):
            kind, tail, head, people = event
            readable.append((kind, tail, head, people // SCALE))
        else:
            readable.append(event)
    return readable


def flood(j, people):
    return ("flood", 1, j, people)


def push(i, j, people):
    return ("push", i, j, people)


def relabel(room, old, new):
    return ("relabel", room, old, new)


# --- the mini building: the hand trace in docs/mini_building.md --------------------------------

MINI_FIFO_AS_TAUGHT = [
    flood(2, 10), flood(3, 10), flood(6, 3),  # 23 people leave the start; only 9 can get out
    push(2, 4, 10),
    push(3, 8, 1), relabel(3, 1, 3),
    push(6, 8, 3),
    push(4, 7, 3), relabel(4, 2, 4),
    relabel(3, 3, 5),
    push(7, 8, 3),
    push(4, 2, 7),
    push(3, 4, 9),
    push(2, 5, 2), relabel(2, 3, 5),
    relabel(4, 4, 6),
    push(5, 6, 2),
    relabel(2, 5, 7),
    push(4, 3, 9),
    push(6, 8, 2),  # the 9th person is out: the maximum preflow
    push(2, 4, 5),  # from here on, 14 people walk back to the start
    relabel(3, 5, 7),
    relabel(4, 6, 8),
    relabel(3, 7, 9),
    push(4, 2, 5),
    push(3, 1, 9),
    relabel(2, 7, 9),
    push(2, 1, 5),
]


def test_mini_fifo_as_taught(mini):
    trace = []
    result = solve(mini, FIFO, False, trace)
    assert events(trace) == MINI_FIFO_AS_TAUGHT
    assert result.value == MINI_MAX_FLOW * SCALE
    c = result.counts
    assert (c.saturating, c.nonsaturating, c.relabels, c.examinations) == (4, 11, 10, 22)
    assert (c.source_pushes, c.movements) == (3, 18)
    assert (c.walkback_pushes, c.walkback_relabels) == (3, 3)
    assert (c.pushes_after_max_preflow, c.relabels_after_max_preflow) == (4, 4)
    assert (c.gaps, c.global_relabels, c.label_raises) == (0, 0, 0)


def test_mini_fifo_gap(mini):
    """The 4th relabel (room 2, from 3 to 5) leaves label 3 empty: rooms 2, 3, 4 jump to n = 8."""
    trace = []
    result = solve(mini, FIFO, True, trace)
    assert events(trace)[:15] == MINI_FIFO_AS_TAUGHT[:15]  # the same run up to that relabel
    assert events(trace)[15] == ("gap", 3, (2, 3, 4))
    assert result.counts.gaps == 1 and result.counts.label_raises == 3
    assert result.value == MINI_MAX_FLOW * SCALE


# --- AMO Figure 7.15: the bad example for FIFO (pp. 233-234), with n = 10 ----------------------

@pytest.fixture
def amo_7_15():
    return read_instance(DATA / "amo_figure_7_15.txt")


def test_amo_figure_7_15_highest_label(amo_7_15):
    """'The highest-label preflow-push algorithm examines nodes 2, 3, ..., n - 1, in this order and
    pushes all the excess to the sink.'"""
    trace = []
    result = solve(amo_7_15, HIGHEST, False, trace)
    assert [e[1] for e in events(trace) if e[0] == "push"] == list(range(2, 10))
    c = result.counts
    assert (c.nonsaturating, c.saturating, c.relabels, c.examinations) == (8, 0, 0, 8)


def test_amo_figure_7_15_fifo(amo_7_15):
    """With the queue 9, 8, ..., 2, FIFO 'would perform n - 2 phases and use (n - 2) + (n - 3) + ... + 1'
    non-saturating pushes: 8 + 7 + ... + 1 = 36."""
    result = solve(amo_7_15, FIFO, False)
    c = result.counts
    assert (c.nonsaturating, c.saturating, c.relabels, c.examinations) == (36, 0, 0, 36)


# --- rules that hold on every network --------------------------------------------------------

@pytest.mark.parametrize("inst", RANDOM, ids=lambda inst: inst.name)
def test_random_network_matches_networkx(inst):
    expected = reference_max_flow(inst)
    n, m = inst.n, inst.m
    for rule, heuristics in SETTINGS:
        result = solve(inst, rule, heuristics)
        assert result.value == expected, (rule, heuristics)
        c = result.counts
        assert c.max_label < 2 * n  # AMO Lemma 7.12
        assert c.relabels <= 2 * n * n  # Lemma 7.13
        assert c.saturating <= n * m  # Lemma 7.14
        assert c.movements == c.source_pushes + c.saturating + c.nonsaturating
        assert c.walkback_pushes <= c.saturating + c.nonsaturating
        assert c.backward_checks + c.global_checks <= c.checks
        if not heuristics:
            assert (c.gaps, c.global_relabels, c.label_raises, c.global_checks) == (0, 0, 0, 0)


def test_unknown_rule_is_refused(mini):
    residual = build_residual(mini)
    with pytest.raises(ValueError, match="rule must be"):
        preflow_push(residual, residual.fresh(), rule="lifo")


def test_solver_never_uses_analysis_or_checking_code():
    """Decision DM7: the solver sees only the residual network, never floors or references."""
    source = (Path(__file__).resolve().parents[1] / "src" / "maxflow" / "preflow.py").read_text()
    imports = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
    assert not [line for line in imports if any(w in line for w in ("structure", "verify", "networkx"))]


# --- the real data: all six settings agree on all 21 cases ----------------------------------------

@pytest.mark.parametrize("name, reading", CASES)
def test_all_six_settings_agree(data_dir, name, reading):
    inst = read_instance(data_dir / f"{name}.txt", reading)
    expected = reference_max_flow(inst)
    values = {}
    for numb in (False, True):
        residual = build_residual(inst)
        res = residual.fresh()
        values[("sap", numb)] = shortest_augmenting_path(residual, res, numb=numb).value
        check_residual(residual, res)
        check_flow(inst, arc_flows(residual, res), values[("sap", numb)])
    for rule, heuristics in SETTINGS:
        result = solve(inst, rule, heuristics)
        assert result.counts.max_label < 2 * inst.n
        values[(rule, heuristics)] = result.value
    assert set(values.values()) == {expected}, values
