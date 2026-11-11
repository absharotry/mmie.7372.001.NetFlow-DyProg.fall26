"""Tests for the residual network: shape, starting values, moving people, and the read-outs."""

import pytest
from conftest import MINI_GROUPS, MINI_HAND_FLOW, MINI_MAX_FLOW, arc_people

from maxflow.instance import DATASETS, SCALE, SPARSE, TWO_WAY, Arc, read_instance
from maxflow.residual import arc_flows, build_residual, flow_value
from maxflow.verify import check_residual


def record(residual, tail, head):
    """The record for 'space left going tail -> head'."""
    (e,) = [e for e in residual.out[tail] if residual.head[e] == head]
    return e


def send_route(residual, res, route, people):
    """Move `people` (scaled) along a route of rooms: two updates per passage."""
    for tail, head in zip(route, route[1:]):
        e = record(residual, tail, head)
        res[e] -= people
        res[e ^ 1] += people


def load_flows(residual, flows):
    """Residual values after putting `flows` (people per file arc) on the passages."""
    res = residual.fresh()
    for e, x in zip(residual.arc_record, flows):
        res[e] -= x
        res[e ^ 1] += x
    return res


def distinct_pairs(instance):
    return len({frozenset((arc.tail, arc.head)) for arc in instance.arcs})


# --- the mini building ----------------------------------------------------------------------

def test_mini_shape(mini):
    r = build_residual(mini)
    assert (r.n, r.s, r.t) == (8, 1, 8)
    assert r.records == 28  # 22 arcs: 8 corridor pairs + 4 up stairs + 2 down stairs = 14 pairs
    assert len(r.arc_record) == 22
    assert r.out[0] == ()
    # Every record sits in exactly one room's list, and that room is its tail.
    listed = sorted(e for room in range(1, 9) for e in r.out[room])
    assert listed == list(range(28))
    for room in range(1, 9):
        for e in r.out[room]:
            assert r.tail(e) == room
            assert r.head[e ^ 1] == room and r.tail(e ^ 1) == r.head[e]


def test_mini_room_lists_follow_file_order(mini):
    r = build_residual(mini)
    # Room 1: corridors to 2 and 3, its up stair to 6, then the way back up the down stair 5 -> 1.
    assert [r.head[e] for e in r.out[1]] == [2, 3, 6, 5]
    assert [r.head[e] for e in r.out[8]] == [6, 7, 3, 4]


def test_mini_starting_values(mini):
    r = build_residual(mini)
    res = r.fresh()
    assert res == list(r.capacity)
    # A corridor is one pair with 10 each way.
    assert res[record(r, 1, 2)] == res[record(r, 2, 1)] == 10 * SCALE
    # An up stair: 3 going up, nothing coming down.
    assert res[record(r, 1, 6)] == 3 * SCALE and res[record(r, 6, 1)] == 0
    # The down stair into the start: 1 going down, nothing going up.
    assert res[record(r, 5, 1)] == 1 * SCALE and res[record(r, 1, 5)] == 0


def test_fresh_gives_independent_copies(mini):
    r = build_residual(mini)
    first = r.fresh()
    first[0] -= 5
    assert r.fresh()[0] == r.capacity[0] == first[0] + 5


def test_mini_hand_flow(mini):
    """Send the four hand-worked groups and read the answer back out."""
    r = build_residual(mini)
    res = r.fresh()
    for route, people in MINI_GROUPS:
        send_route(r, res, route, people * SCALE)
    assert flow_value(r, res) == MINI_MAX_FLOW * SCALE
    assert arc_flows(r, res) == arc_people(mini, MINI_HAND_FLOW)
    check_residual(r, res)
    # The residual table in docs/mini_building.md.
    assert (res[record(r, 1, 2)], res[record(r, 2, 1)]) == (8 * SCALE, 12 * SCALE)
    assert (res[record(r, 1, 6)], res[record(r, 6, 1)]) == (0, 3 * SCALE)
    assert (res[record(r, 5, 1)], res[record(r, 1, 5)]) == (1 * SCALE, 0)


def test_people_both_ways_cancel(mini):
    """3 people 3 -> 4 and 1 person 4 -> 3 read back as a net 2 going 3 -> 4."""
    r = build_residual(mini)
    res = load_flows(r, arc_people(mini, {(3, 4): 3, (4, 3): 1}))
    assert (res[record(r, 3, 4)], res[record(r, 4, 3)]) == (8 * SCALE, 12 * SCALE)
    flows = dict(zip([(a.tail, a.head) for a in mini.arcs], arc_flows(r, res)))
    assert (flows[(3, 4)], flows[(4, 3)]) == (2 * SCALE, 0)


def test_flow_value_counts_arcs_out_of_the_exit(mini):
    """People who go 8 -> 4 down the stair count against the answer: it is net flow into t."""
    r = build_residual(mini)
    res = r.fresh()
    send_route(r, res, (1, 3, 8), 1 * SCALE)
    send_route(r, res, (8, 4), 1 * SCALE)
    assert flow_value(r, res) == 0


def test_repeated_arc_is_refused(mini):
    doubled = mini._replace(arcs=mini.arcs + (Arc(1, 2, 5),))
    with pytest.raises(ValueError, match="listed twice"):
        build_residual(doubled)


# --- the real files ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", DATASETS)
def test_real_files_directed(data_dir, name):
    inst = read_instance(data_dir / f"{name}.txt")
    r = build_residual(inst)
    assert r.records == 2 * distinct_pairs(inst)
    assert r.fresh() == list(r.capacity)
    assert sum(r.capacity) == sum(arc.capacity for arc in inst.arcs)
    assert flow_value(r, r.fresh()) == 0
    assert arc_flows(r, r.fresh()) == [0] * inst.m


def test_record_counts_match_data_model(data_dir):
    """docs/data_modeling.md, Section 6: 754 records for elist96d and 21,524 for elist640d."""
    assert build_residual(read_instance(data_dir / "elist96d.txt")).records == 754
    assert build_residual(read_instance(data_dir / "elist640d.txt")).records == 21_524


@pytest.mark.parametrize("name", SPARSE)
def test_real_files_two_way(data_dir, name):
    """Two-way reading: every pair starts with the edge's capacity in both directions."""
    inst = read_instance(data_dir / f"{name}.txt", TWO_WAY)
    r = build_residual(inst)
    assert r.records == inst.m  # each edge became 2 arcs, and they share one pair
    for e in range(0, r.records, 2):
        assert r.capacity[e] == r.capacity[e + 1] > 0


# --- shuffled door orders (Phase 6) ------------------------------------------------------------

def test_shuffle_rooms_changes_only_the_order(mini):
    from maxflow.residual import shuffle_rooms

    base = build_residual(mini)
    one, again, other = shuffle_rooms(base, 1), shuffle_rooms(base, 1), shuffle_rooms(base, 2)
    assert one.out == again.out  # the same seed gives the same order
    assert one.out != base.out and one.out != other.out  # different seeds give different orders
    for room in range(9):
        assert sorted(one.out[room]) == sorted(base.out[room])  # the same doors in every room
    assert (one.head, one.capacity, one.arc_record) == (base.head, base.capacity, base.arc_record)
    assert one.fresh() == base.fresh()
