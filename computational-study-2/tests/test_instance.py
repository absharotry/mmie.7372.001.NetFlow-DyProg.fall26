"""Tests for the file reader: formats, audit rules, the two-way option, and all 14 real files."""

import hashlib
import re

import pytest

from maxflow.instance import (
    DATASETS,
    DIRECTED,
    SCALE,
    SPARSE,
    TWO_WAY,
    DataError,
    parse_capacity,
    read_instance,
    to_text,
)
from maxflow.structure import characteristics, reference_max_flow, shortest_route

# --- capacities -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("3.200100e+00", 32001),
        ("3.20010", 32001),
        ("8.86000E-02", 886),
        ("1500", 15_000_000),
        ("0.0002", 2),
        ("1.000000e-03", 10),
    ],
)
def test_capacity_formats_are_read_exactly(text, expected):
    assert parse_capacity(text) == expected


@pytest.mark.parametrize("text", ["0.00001", "0", "-1", "abc", "nan", "inf"])
def test_bad_capacities_are_rejected(text):
    with pytest.raises(DataError):
        parse_capacity(text)


def test_to_text_shows_file_units():
    assert to_text(13784) == "1.3784"
    assert to_text(15_000_000) == "1500"
    assert to_text(0) == "0"


# --- reading a whole file -------------------------------------------------------------------

def test_reads_crlf_mixed_formats_and_irregular_spacing(write_elist):
    text = "  4\r\n3\r\n1\r\n   4\r\n1  2   3.200100e+00 \r\n 2 3 8.86000E-02\r\n3   4 3.20010"
    inst = read_instance(write_elist(text))
    assert (inst.n, inst.m, inst.s, inst.t, inst.reading) == (4, 3, 1, 4, DIRECTED)
    assert [tuple(arc) for arc in inst.arcs] == [(1, 2, 32001), (2, 3, 886), (3, 4, 32001)]


@pytest.mark.parametrize(
    "text, rule",
    [
        ("4 1 1 4 1 2 1 3", "3 values"),
        ("4 3 1 4 1 2 1 2 3 1", "header says 3"),
        ("4 1 1 4 1 9 1", "outside"),
        ("4 1 1 4 2 2 1", "self-loop"),
        ("4 2 1 4 1 2 1 1 2 5", "listed twice"),
        ("4 1 1 4 1 2 0", "not positive"),
        ("4 1 1 1 1 2 1", "same room"),
        ("4 1 1 4 1 x 1", "not a whole number"),
        ("4 1", "header needs"),
    ],
)
def test_audit_rejects_broken_files(write_elist, text, rule):
    with pytest.raises(DataError, match=rule):
        read_instance(write_elist(text))


# --- the two-way reading --------------------------------------------------------------------

def test_two_way_doubles_each_passage_with_the_same_capacity(write_elist):
    inst = read_instance(write_elist("3 2 1 3 1 2 5 2 3 7"), reading=TWO_WAY)
    assert inst.reading == TWO_WAY
    assert [tuple(arc) for arc in inst.arcs] == [
        (1, 2, 5 * SCALE), (2, 1, 5 * SCALE), (2, 3, 7 * SCALE), (3, 2, 7 * SCALE)
    ]


def test_two_way_refuses_files_with_two_way_pairs(write_elist):
    with pytest.raises(DataError, match="DM3"):
        read_instance(write_elist("3 3 1 3 1 2 5 2 1 4 2 3 7"), reading=TWO_WAY)


def test_unknown_reading_is_rejected(write_elist):
    with pytest.raises(ValueError):
        read_instance(write_elist("3 1 1 3 1 2 5"), reading="sideways")


# --- the 14 real files (docs/data_modeling.md, Sections 3, 4 and 8) -------------------------

# file: n, m, two-way pairs, distinct pairs, out-arcs of s, in-arcs of t, capacity min, max, max flow
INVENTORY = {
    "elist96": (96, 187, 0, 187, 3, 0, "0.0004", "3.2001", "0"),
    "elist96d": (96, 528, 151, 377, 3, 3, "0.0004", "3.2001", "1.3784"),
    "elist160": (160, 285, 0, 285, 4, 0, "0.2624", "480", "0"),
    "elist160d": (160, 912, 261, 651, 4, 5, "0.0751", "480", "211.8491"),
    "elist200": (200, 483, 0, 483, 3, 1, "0.0017", "5.0001", "0"),
    "elist200d": (200, 1340, 340, 1000, 3, 3, "0.0002", "5.0001", "2.1353"),
    "elist500": (500, 1040, 0, 1040, 6, 0, "0.0206", "1500", "0"),
    "elist500d": (500, 3975, 880, 3095, 6, 5, "0.0026", "1500", "702.1112"),
    "elist640": (640, 3037, 0, 3037, 10, 2, "0.001", "1.2801", "0"),
    "elist640d": (640, 12608, 1846, 10762, 10, 7, "0.001", "1.2801", "0.8817"),
    "elist960": (960, 2061, 0, 2061, 7, 0, "0.001", "800", "0"),
    "elist960d": (960, 9488, 2018, 7470, 7, 7, "0.001", "800", "335.1562"),
    "elist1440": (1440, 5397, 0, 5397, 10, 3, "0.0002", "720", "0"),
    "elist1440d": (1440, 5397, 0, 5397, 10, 3, "0.0002", "720", "0"),
}

# sparse file: rooms the start reaches, rooms that reach the exit (directed reading)
SPARSE_REACH = {
    "elist96": (4, 1), "elist160": (5, 1), "elist200": (4, 2), "elist500": (7, 1),
    "elist640": (11, 3), "elist960": (8, 1), "elist1440": (11, 4),
}

# sparse file, two-way reading: arcs, max flow, shortest route
TWO_WAY_TABLE = {
    "elist96": (374, "4.6653", 6), "elist160": (570, "970.317", 10), "elist200": (966, "5.0001", 8),
    "elist500": (2080, "3013.5749", 20), "elist640": (6074, "0.5477", 9),
    "elist960": (4122, "61.3107", 59), "elist1440": (10794, "111.0133", 9),
}


def test_checksums_match_sources_md(data_dir):
    table = (data_dir / "SOURCES.md").read_text()
    recorded = dict(re.findall(r"\| (elist\w+)\.txt \| ([0-9a-f]{64}) \|", table))
    assert sorted(recorded) == sorted(DATASETS)
    for name in DATASETS:
        digest = hashlib.sha256((data_dir / f"{name}.txt").read_bytes()).hexdigest()
        assert digest == recorded[name], name


@pytest.mark.parametrize("name", DATASETS)
def test_inventory_matches_data_document(data_dir, name):
    inst = read_instance(data_dir / f"{name}.txt")
    c = characteristics(inst)
    n, m, pairs2, distinct, out_s, in_t, cmin, cmax, flow = INVENTORY[name]
    assert (inst.n, inst.m, inst.s, inst.t) == (n, m, 1, n)
    assert (c["two_way_pairs"], c["distinct_pairs"], c["out_arcs_s"], c["in_arcs_t"]) == (
        pairs2, distinct, out_s, in_t
    )
    assert (to_text(c["capacity_min"]), to_text(c["capacity_max"])) == (cmin, cmax)
    assert to_text(reference_max_flow(inst)) == flow


def test_1440_and_1440d_are_identical(data_dir):
    a = read_instance(data_dir / "elist1440.txt")
    b = read_instance(data_dir / "elist1440d.txt")
    assert a.arcs == b.arcs


@pytest.mark.parametrize("name", SPARSE)
def test_sparse_files_have_no_route_when_directed(data_dir, name):
    inst = read_instance(data_dir / f"{name}.txt")
    c = characteristics(inst)
    assert (c["rooms_reached_from_s"], c["rooms_reaching_t"]) == SPARSE_REACH[name]
    assert c["shortest_route"] is None


@pytest.mark.parametrize("name", SPARSE)
def test_two_way_supplement_matches_data_document(data_dir, name):
    inst = read_instance(data_dir / f"{name}.txt", reading=TWO_WAY)
    m, flow, route = TWO_WAY_TABLE[name]
    assert inst.m == m
    assert to_text(reference_max_flow(inst)) == flow
    assert shortest_route(inst) == route


@pytest.mark.parametrize("name", [n for n in DATASETS if n.endswith("d") and n != "elist1440d"])
def test_dense_files_refuse_the_two_way_reading(data_dir, name):
    with pytest.raises(DataError, match="DM3"):
        read_instance(data_dir / f"{name}.txt", reading=TWO_WAY)
