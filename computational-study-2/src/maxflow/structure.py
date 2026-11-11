"""Describe a network's structure: counts, reachability and floors. Analysis only.

The solvers never import this module (decision DM7). They see only the list of arcs, so anything
found here, such as the floors, is knowledge we use to explain results, never a shortcut for them.

NetworkX appears here only as an independent reference (max flow, grid matching). It is never one of
the algorithms being compared.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import networkx as nx

from .instance import Instance


# ---------------------------------------------------------------------------------------------
# Reachability: which rooms can the start reach, and which rooms can reach the exit?
# ---------------------------------------------------------------------------------------------

def _neighbours(instance: Instance, backward: bool = False) -> dict[int, list[int]]:
    nbrs: dict[int, list[int]] = {room: [] for room in range(1, instance.n + 1)}
    for arc in instance.arcs:
        if backward:
            nbrs[arc.head].append(arc.tail)
        else:
            nbrs[arc.tail].append(arc.head)
    return nbrs


def _breadth_first(nbrs: dict[int, list[int]], start: int) -> dict[int, int]:
    """Number of passages from start to every room it can reach (breadth-first search)."""
    dist = {start: 0}
    queue = deque([start])
    while queue:
        room = queue.popleft()
        for nxt in nbrs[room]:
            if nxt not in dist:
                dist[nxt] = dist[room] + 1
                queue.append(nxt)
    return dist


def reachable_from(instance: Instance, room: int) -> set[int]:
    """Rooms that can be reached from `room` (including itself)."""
    return set(_breadth_first(_neighbours(instance), room))


def can_reach(instance: Instance, room: int) -> set[int]:
    """Rooms from which `room` can be reached (including itself)."""
    return set(_breadth_first(_neighbours(instance, backward=True), room))


def shortest_route(instance: Instance) -> int | None:
    """Fewest passages on any route from start to exit, or None if there is no route.

    Every augmenting path the shortest augmenting path algorithm finds is at least this long,
    because distance labels never decrease (AMO Lemma 7.5).
    """
    return _breadth_first(_neighbours(instance), instance.s).get(instance.t)


def source_flood(instance: Instance) -> int:
    """Total capacity out of the start: what preflow-push sends out first (AMO Figure 7.11)."""
    return sum(arc.capacity for arc in instance.arcs if arc.tail == instance.s)


def reference_max_flow(instance: Instance) -> int:
    """Max flow from NetworkX on the exact integer capacities. An independent reference only."""
    graph = nx.DiGraph()
    graph.add_nodes_from(range(1, instance.n + 1))
    graph.add_weighted_edges_from(instance.arcs, weight="capacity")
    return nx.maximum_flow_value(graph, instance.s, instance.t)


def characteristics(instance: Instance) -> dict:
    """The counts on each dataset card (docs/data_modeling.md, Section 4)."""
    pairs = {(arc.tail, arc.head) for arc in instance.arcs}
    capacities = [arc.capacity for arc in instance.arcs]
    n, m = instance.n, instance.m
    return {
        "n": n,
        "m": m,
        "density": m / (n * (n - 1)),
        "m_per_n": m / n,
        "two_way_pairs": sum(1 for (u, v) in pairs if u < v and (v, u) in pairs),
        "distinct_pairs": len({frozenset(pair) for pair in pairs}),
        "out_arcs_s": sum(1 for arc in instance.arcs if arc.tail == instance.s),
        "in_arcs_t": sum(1 for arc in instance.arcs if arc.head == instance.t),
        "capacity_min": min(capacities),
        "capacity_max": max(capacities),
        "rooms_reached_from_s": len(reachable_from(instance, instance.s)),
        "rooms_reaching_t": len(can_reach(instance, instance.t)),
        "shortest_route": shortest_route(instance),
        "source_flood": source_flood(instance),
    }


# ---------------------------------------------------------------------------------------------
# Floors: the structure of the dense files (docs/data_modeling.md, Section 7)
# ---------------------------------------------------------------------------------------------

@dataclass(frozen=True, eq=False)
class Floors:
    count: int  # number of floors L
    side: int  # each floor is a side x side grid of rooms
    corridor_capacity: int  # U, the one capacity shared by every corridor
    floor_of: dict[int, int]  # room -> floor number, 0 = the start's floor
    position: dict[int, tuple[int, int]]  # room -> (row, column) inside its floor's grid
    up_totals: tuple[int, ...]  # F_k: total up-stair capacity from floor k to floor k + 1
    up_stairs: int  # number of stairs going one floor up
    down_stairs: int  # number of stairs going one floor down

    @property
    def rooms_per_floor(self) -> int:
        return self.side * self.side

    @property
    def up_per_room(self) -> float:
        return self.up_stairs / (self.rooms_per_floor * (self.count - 1))

    @property
    def down_per_room(self) -> float:
        return self.down_stairs / (self.rooms_per_floor * (self.count - 1))

    @property
    def narrowest_gap(self) -> int:
        """Index k of the narrowest gap: k = 0 means the stairs from floor 1 to floor 2."""
        return min(range(len(self.up_totals)), key=self.up_totals.__getitem__)

    @property
    def stair_sum_max_flow(self) -> int:
        """Max flow by adding up stairs: min over k of F_k (the Proposition, data_modeling.md 7)."""
        return min(self.up_totals)

    @property
    def proposition_holds(self) -> bool:
        """The Proposition needs min F_k <= U, so that no corridor can be the limit."""
        return self.stair_sum_max_flow <= self.corridor_capacity


def find_floors(instance: Instance) -> Floors | None:
    """Find the chain of grid floors, or return None if the network is not built that way.

    Steps:
    1. Corridors are the arcs with the largest capacity U, and each must run both ways.
    2. Rooms joined by corridors form the floors; every floor must be an exact grid of one size.
    3. All other arcs are stairs. They must link the floors into a single chain that starts at the
       start's floor, and every stair must join neighbouring floors.
    Sparse files fail step 2, because some stairs were widened to U and floors merge together.
    """
    corridor_capacity = max(arc.capacity for arc in instance.arcs)
    corridors = {(arc.tail, arc.head) for arc in instance.arcs if arc.capacity == corridor_capacity}
    if any((v, u) not in corridors for (u, v) in corridors):
        return None

    corridor_graph = nx.Graph()
    corridor_graph.add_nodes_from(range(1, instance.n + 1))
    corridor_graph.add_edges_from(corridors)
    groups = [set(group) for group in nx.connected_components(corridor_graph)]
    size = len(groups[0])
    side = math.isqrt(size)
    if side < 2 or side * side != size or any(len(group) != size for group in groups):
        return None

    grid = nx.grid_2d_graph(side, side)
    position: dict[int, tuple[int, int]] = {}
    for group in groups:
        matcher = nx.isomorphism.GraphMatcher(corridor_graph.subgraph(group), grid)
        if not matcher.is_isomorphic():
            return None
        position.update(matcher.mapping)

    group_of = {room: g for g, group in enumerate(groups) for room in group}
    stairs = [arc for arc in instance.arcs if arc.capacity != corridor_capacity]
    chain = nx.Graph()
    chain.add_nodes_from(range(len(groups)))
    chain.add_edges_from((group_of[a.tail], group_of[a.head]) for a in stairs)
    start_group = group_of[instance.s]
    if not nx.is_isomorphic(chain, nx.path_graph(len(groups))):
        return None
    if len(groups) > 1 and chain.degree(start_group) != 1:
        return None
    order = nx.single_source_shortest_path_length(chain, start_group)
    floor_of = {room: order[group_of[room]] for room in group_of}

    count = len(groups)
    up_totals = [0] * (count - 1)
    up = down = 0
    for arc in stairs:
        step = floor_of[arc.head] - floor_of[arc.tail]
        if step == 1:
            up_totals[floor_of[arc.tail]] += arc.capacity
            up += 1
        elif step == -1:
            down += 1
        else:
            return None
    return Floors(count, side, corridor_capacity, floor_of, position, tuple(up_totals), up, down)
