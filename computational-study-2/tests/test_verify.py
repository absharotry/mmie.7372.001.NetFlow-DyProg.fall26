"""Tests for the verifier: it must accept every correct best answer and reject each kind of broken one."""

import networkx as nx
import pytest
from conftest import MINI_HAND_FLOW, MINI_MAX_FLOW, arc_people

from maxflow.instance import DATASETS, DIRECTED, SCALE, SPARSE, TWO_WAY, read_instance
from maxflow.residual import arc_flows, build_residual, flow_value
from maxflow.verify import VerificationError, check_flow, check_residual

FLOOR_1 = frozenset({1, 2, 3, 4})


# --- answers that must be accepted -----------------------------------------------------------

def test_accepts_hand_flow(mini):
    cert = check_flow(mini, arc_people(mini, MINI_HAND_FLOW), MINI_MAX_FLOW * SCALE)
    assert cert.value == cert.cut_capacity == 9 * SCALE
    assert cert.cut_side == FLOOR_1  # the narrowest set of stairs: all four up stairs, 3 + 2 + 3 + 1


def test_accepts_a_different_best_answer(mini):
    """Same 9 people, plus one extra person looping 1 -> 2 -> 4 -> 3 -> 1 around floor 1.

    This also puts people both ways along corridor 3-4 (3 one way, 1 the other), which is allowed.
    """
    loop = dict(MINI_HAND_FLOW)
    loop[(1, 2)] += 1
    loop[(2, 4)] = 1
    loop[(4, 3)] = 1
    loop[(3, 1)] = 1
    cert = check_flow(mini, arc_people(mini, loop), 9 * SCALE)
    assert cert.cut_side == FLOOR_1


def test_accepts_zero_when_the_exit_cannot_be_reached(write_elist):
    """Like the sparse files: the start reaches only itself and a dead-end neighbour."""
    inst = read_instance(write_elist("4\n3\n1\n4\n1 2 5\n2 1 1\n3 4 5\n"))
    cert = check_flow(inst, [0, 0, 0], 0)
    assert cert.cut_side == {1, 2} and cert.cut_capacity == 0


def networkx_best(inst):
    """NetworkX's own best answer, as people per file arc. An independent reference only."""
    graph = nx.DiGraph()
    graph.add_nodes_from(range(1, inst.n + 1))
    graph.add_weighted_edges_from(inst.arcs, weight="capacity")
    value, flow = nx.maximum_flow(graph, inst.s, inst.t)
    return value, [flow[arc.tail][arc.head] for arc in inst.arcs]


CASES = [(name, DIRECTED) for name in DATASETS] + [(name, TWO_WAY) for name in SPARSE]


@pytest.mark.parametrize("name, reading", CASES)
def test_accepts_networkx_answer_on_every_data_case(data_dir, name, reading):
    """All 21 data cases. Then the same answer goes through the residual network and back out."""
    inst = read_instance(data_dir / f"{name}.txt", reading)
    value, flows = networkx_best(inst)
    cert = check_flow(inst, flows, value)
    assert inst.t not in cert.cut_side

    residual = build_residual(inst)
    res = residual.fresh()
    for e, x in zip(residual.arc_record, flows):
        res[e] -= x
        res[e ^ 1] += x
    check_residual(residual, res)
    assert flow_value(residual, res) == value
    assert check_flow(inst, arc_flows(residual, res), value).cut_side == cert.cut_side


# --- broken answers that must be rejected ------------------------------------------------------

def broken(mini, changes):
    """The hand-worked answer with some arcs changed: {(tail, head): unscaled people}."""
    return arc_people(mini, {**MINI_HAND_FLOW, **changes})


def test_rejects_too_many_on_a_passage(mini):
    with pytest.raises(VerificationError, match=r"passage limit: arc 17 \(1, 6\) carries 4 but holds 0 to 3"):
        check_flow(mini, broken(mini, {(1, 6): 4, (6, 8): 4}), 10 * SCALE)


def test_rejects_negative_people(mini):
    with pytest.raises(VerificationError, match=r"passage limit: arc 22 \(8, 4\) carries -1"):
        check_flow(mini, broken(mini, {(8, 4): -1}), 9 * SCALE)


def test_rejects_people_vanishing(mini):
    with pytest.raises(VerificationError, match="conservation: room 6 takes in 3 but sends out 2"):
        check_flow(mini, broken(mini, {(6, 8): 2}), 8 * SCALE)


def test_rejects_wrong_value(mini):
    with pytest.raises(VerificationError, match="value: net flow into exit 8 is 9, but the answer says 10"):
        check_flow(mini, arc_people(mini, MINI_HAND_FLOW), 10 * SCALE)


def test_rejects_valid_but_not_best(mini):
    """Leave out group 4 (1 person on 1 -> 3 -> 8): a valid flow of 8, but not the best."""
    with pytest.raises(VerificationError, match=r"not maximum: .* along 1 -> 3 -> 8, which has space for 1 more"):
        check_flow(mini, broken(mini, {(1, 3): 3, (3, 8): 0}), 8 * SCALE)


def test_rejects_wrong_length(mini):
    with pytest.raises(VerificationError, match="length: got 21 arc flows for 22 arcs"):
        check_flow(mini, arc_people(mini, MINI_HAND_FLOW)[:-1], 9 * SCALE)


def test_bookkeeping_rejects_one_sided_update(mini):
    """An algorithm that forgets the partner record loses people between the two sides."""
    residual = build_residual(mini)
    res = residual.fresh()
    res[0] -= 2 * SCALE  # 2 people 1 -> 2, but the way back 2 -> 1 was never credited
    with pytest.raises(VerificationError, match=r"bookkeeping: passage 1 <-> 2 has 18 space left in total, but started with 20"):
        check_residual(residual, res)


def test_bookkeeping_rejects_negative_space(mini):
    residual = build_residual(mini)
    res = residual.fresh()
    e = residual.arc_record[16]  # stair 1 -> 6, capacity 3
    res[e] -= 4 * SCALE
    res[e ^ 1] += 4 * SCALE
    with pytest.raises(VerificationError, match=r"bookkeeping: passage 1 -> 6 has negative space left"):
        check_residual(residual, res)


def test_bookkeeping_rejects_wrong_length(mini):
    with pytest.raises(VerificationError, match="length: got 27 residual values for 28 records"):
        check_residual(build_residual(mini), build_residual(mini).fresh()[:-1])
