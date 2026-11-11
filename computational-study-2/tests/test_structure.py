"""Tests for the structure module: reachability, the floor finder, and the stair-sum Proposition."""

import pytest
from conftest import toy_building_text

from maxflow.instance import DENSE, SCALE, SPARSE, read_instance, to_text
from maxflow.structure import (
    can_reach,
    find_floors,
    reachable_from,
    reference_max_flow,
    shortest_route,
    source_flood,
)

# --- a made-up building with a known answer ------------------------------------------------

@pytest.fixture
def toy(write_elist):
    return read_instance(write_elist(toy_building_text()))


def test_toy_reachability_and_route(toy):
    assert reachable_from(toy, 1) == set(range(1, 13))
    assert can_reach(toy, 12) == set(range(1, 13))
    assert shortest_route(toy) == 4  # 1 -> 5 -> 6 -> 10 -> 12: one corridor on floor 2, one on floor 3
    assert source_flood(toy) == (10 + 10 + 3) * SCALE


def test_toy_floors_are_found(toy):
    floors = find_floors(toy)
    assert floors is not None
    assert (floors.count, floors.side, floors.corridor_capacity) == (3, 2, 10 * SCALE)
    assert floors.up_totals == (7 * SCALE, 4 * SCALE)
    assert (floors.up_stairs, floors.down_stairs) == (4, 1)
    assert floors.narrowest_gap == 1
    assert {floors.floor_of[r] for r in (1, 2, 3, 4)} == {0}
    assert {floors.floor_of[r] for r in (9, 10, 11, 12)} == {2}


def test_toy_stair_sum_equals_reference_max_flow(toy):
    floors = find_floors(toy)
    assert floors.proposition_holds
    assert floors.stair_sum_max_flow == reference_max_flow(toy) == 4 * SCALE


def test_a_stair_skipping_a_floor_means_no_floor_structure(write_elist):
    text = toy_building_text().replace("7 2 1", "2 11 1")  # floor 1 straight to floor 3
    assert find_floors(read_instance(write_elist(text))) is None


def test_a_one_way_corridor_means_no_floor_structure(write_elist):
    text = toy_building_text().replace("2\r\n1 2 10\r\n2 1 10", "2\r\n1 2 10\r\n2 1 9", 1)
    assert find_floors(read_instance(write_elist(text))) is None


# --- the 6 dense files (docs/data_modeling.md, Section 7) -----------------------------------

# file: floors, side, up per room, down per room, U, narrowest F, widest F, narrowest gap
# (1 = floors 1->2), shortest directed route, source flood
DENSE_TABLE = {
    "elist96d": (6, 4, 1, 2, "3.2001", "1.3784", "1.871", 5, 5, "6.4888"),
    "elist160d": (10, 4, 2, 1, "480", "211.8491", "285.8806", 2, 9, "978.1452"),
    "elist200d": (8, 5, 1, 3, "5.0001", "2.1353", "2.5266", 3, 9, "10.1297"),
    "elist500d": (20, 5, 4, 1, "1500", "702.1112", "814.9268", 1, 19, "3029.637"),
    "elist640d": (10, 8, 8, 10, "1.2801", "0.8817", "0.9081", 4, 9, "2.5717"),
    "elist960d": (60, 4, 5, 2, "800", "335.1562", "461.0198", 52, 59, "1623.2095"),
}


@pytest.mark.parametrize("name", DENSE)
def test_dense_floors_match_data_document(data_dir, name):
    inst = read_instance(data_dir / f"{name}.txt")
    floors = find_floors(inst)
    assert floors is not None
    L, side, up, down, U, narrow, wide, gap, route, flood = DENSE_TABLE[name]
    assert (floors.count, floors.side, floors.up_per_room, floors.down_per_room) == (L, side, up, down)
    assert to_text(floors.corridor_capacity) == U
    assert to_text(min(floors.up_totals)) == narrow
    assert to_text(max(floors.up_totals)) == wide
    assert floors.narrowest_gap + 1 == gap
    assert shortest_route(inst) == route
    assert to_text(source_flood(inst)) == flood
    assert floors.floor_of[inst.s] == 0 and floors.floor_of[inst.t] == L - 1


@pytest.mark.parametrize("name", DENSE)
def test_stair_sum_proposition_holds_on_dense_files(data_dir, name):
    inst = read_instance(data_dir / f"{name}.txt")
    floors = find_floors(inst)
    assert floors.proposition_holds
    assert floors.stair_sum_max_flow == reference_max_flow(inst)


@pytest.mark.parametrize("name", DENSE)
def test_start_and_exit_are_corner_rooms(data_dir, name):
    inst = read_instance(data_dir / f"{name}.txt")
    floors = find_floors(inst)
    corners = {(0, 0), (0, floors.side - 1), (floors.side - 1, 0), (floors.side - 1, floors.side - 1)}
    assert floors.position[inst.s] in corners and floors.position[inst.t] in corners


@pytest.mark.parametrize("name", SPARSE)
def test_sparse_files_have_no_floor_structure(data_dir, name):
    assert find_floors(read_instance(data_dir / f"{name}.txt")) is None
