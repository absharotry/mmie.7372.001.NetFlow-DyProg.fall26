"""Draw the data figures: the seven of docs/data_modeling.md (Phase 1) and the mini building (Phase 2).

Run from the project folder:

    python scripts/make_data_figures.py

Colours: one blue for the main series, orange for the one thing to notice (the narrowest gap, or the
people who walk back), aqua for the start and what it can reach, grey for structure. Every coloured
series also has a label or marker shape, so colour is never the only cue.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from maxflow.instance import DENSE, SCALE, SPARSE, read_instance, to_text  # noqa: E402
from maxflow.structure import find_floors, reachable_from, source_flood  # noqa: E402
from maxflow.verify import check_flow  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
MINI_BUILDING = PROJECT / "tests" / "data" / "mini_building.txt"
# The hand-worked best answer (docs/mini_building.md), also in tests/conftest.py. fig8 checks it.
MINI_GROUPS = (((1, 6, 8), 3), ((1, 2, 5, 7, 8), 2), ((1, 3, 4, 7, 8), 3), ((1, 3, 8), 1))

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, BASE, ROOM = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#b4b2a9"
FLOOR_STEP = 5.2  # horizontal distance between floors in the building drawings

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
    "axes.titlesize": 11, "axes.titlecolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 170,
    "savefig.bbox": "tight", "savefig.facecolor": "white", "legend.frameon": False,
})


def units(scaled: int) -> float:
    return scaled / SCALE


def building_xy(floors, room):
    """Where to draw a room: its grid position, shifted right by its floor."""
    row, col = floors.position[room]
    return row + floors.floor_of[room] * FLOOR_STEP, col


def label_floors(ax, floors):
    for f in range(floors.count):
        ax.text((floors.side - 1) / 2 + f * FLOOR_STEP, -0.95, f"Floor {f + 1}", ha="center", color=INK2)


def fig1_floors_and_stairs(dense, out):
    inst, floors = dense["elist96d"]
    pos = {room: building_xy(floors, room) for room in floors.floor_of}
    gap = floors.narrowest_gap
    fig, ax = plt.subplots(figsize=(10.5, 3.3))
    for arc in inst.arcs:
        a, b = floors.floor_of[arc.tail], floors.floor_of[arc.head]
        if a == b:
            ax.plot(*zip(pos[arc.tail], pos[arc.head]), color=ROOM, lw=2.2, zorder=1, solid_capstyle="round")
        elif b > a:  # up stairs, thickness proportional to capacity; down stairs are not drawn
            ax.plot(*zip(pos[arc.tail], pos[arc.head]), color=ORANGE if a == gap else BLUE,
                    lw=0.4 + units(arc.capacity) * 11, alpha=0.8, zorder=2)
    ax.scatter(*zip(*pos.values()), s=20, color=INK2, zorder=3)
    ax.scatter(*pos[inst.s], s=120, color=AQUA, edgecolor="white", lw=2, zorder=4)
    ax.scatter(*pos[inst.t], s=120, color=AQUA, marker="s", edgecolor="white", lw=2, zorder=4)
    label_floors(ax, floors)
    for k, total in enumerate(floors.up_totals):
        ax.text(1.5 + k * FLOOR_STEP + FLOOR_STEP / 2, 3.65, f"{units(total):.2f}", ha="center",
                fontsize=11, color=INK, fontweight="bold" if k == gap else "normal")
    for room, word in ((inst.s, "start"), (inst.t, "exit")):
        x, y = pos[room]
        ax.text(x, y + (0.42 if y < 3 else -0.62), word, ha="center", color=INK2, fontsize=9)
    ax.set_xlim(-0.7, 3 + (floors.count - 1) * FLOOR_STEP + 0.7)
    ax.set_ylim(-1.4, 4.2)
    ax.axis("off")
    fig.savefig(out / "fig1_floors_and_stairs_elist96d.png")
    plt.close(fig)


def fig2_bottleneck_profile(dense, out):
    fig, axes = plt.subplots(2, 3, figsize=(10.5, 5.2))
    for ax, name in zip(axes.flat, DENSE):
        _, floors = dense[name]
        values = [units(v) for v in floors.up_totals]
        gap = floors.narrowest_gap
        gaps = range(1, len(values) + 1)
        ax.bar(gaps, values, width=0.72, zorder=2,
               color=[ORANGE if k == gap else BLUE for k in range(len(values))])
        ax.set_title(f"{name}, {floors.count} floors", loc="left")
        ax.yaxis.grid(True, color=GRID, zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        ax.set_ylim(0, max(values) * 1.27)
        ax.annotate(f"Max flow {to_text(floors.stair_sum_max_flow)}\nfloors {gap + 1}→{gap + 2}",
                    xy=(gap + 1, max(values) * 1.03), ha="left" if gap < len(values) * 0.55 else "right",
                    va="bottom", fontsize=9, color=INK)
        if len(values) > 40:
            ax.set_xticks([1, 20, 40, len(values)])
        elif len(values) > 12:
            ax.set_xticks([1, 5, 10, 15, len(values)])
        else:
            ax.set_xticks(list(gaps))
    for ax in axes[1]:
        ax.set_xlabel("Gap between floors (1 = floors 1→2)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Total up-stair capacity")
    fig.tight_layout(h_pad=2)
    fig.savefig(out / "fig2_bottleneck_profile.png")
    plt.close(fig)


def fig3_capacity_groups(dense, out):
    fig, axes = plt.subplots(2, 3, figsize=(10.5, 5.2))
    for ax, name in zip(axes.flat, DENSE):
        inst, floors = dense[name]
        stairs = [units(a.capacity) for a in inst.arcs if floors.floor_of[a.tail] != floors.floor_of[a.head]]
        corridors = sum(1 for a in inst.arcs if floors.floor_of[a.tail] == floors.floor_of[a.head])
        lo, hi, bins = min(stairs), max(stairs), 22
        ax.hist(stairs, bins=[lo * (hi / lo) ** (i / bins) for i in range(bins + 1)], color=BLUE, rwidth=0.85, zorder=2)
        U, widen = units(floors.corridor_capacity), 1.16
        ax.bar(U / widen ** 0.5, corridors, width=U * (widen - 1) / widen ** 0.5, align="edge", color=ORANGE, zorder=2)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(0.8, max(corridors, 100) * 3)
        ax.set_title(name, loc="left")
        ax.tick_params(length=0, which="both")
        ax.yaxis.grid(True, color=GRID, zorder=0)
        ax.set_axisbelow(True)
    for ax in axes[1]:
        ax.set_xlabel("Capacity (log scale)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Passages (log scale)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (BLUE, ORANGE)]
    fig.legend(handles, ["Stairs (small, varied)", "Corridors (one large value)"], loc="upper left",
               ncol=2, bbox_to_anchor=(0.06, 1.05))
    fig.tight_layout(h_pad=2)
    fig.savefig(out / "fig3_capacity_groups.png")
    plt.close(fig)


def fig4_shape_map(dense, out):
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    for name in DENSE:
        inst, floors = dense[name]
        ax.scatter(floors.count, floors.side, s=95, color=BLUE, edgecolor="white", lw=2, zorder=3)
        ax.annotate(f"{name}\n{inst.m / inst.n:.1f} per room", (floors.count, floors.side), xytext=(0, 11),
                    textcoords="offset points", ha="center", fontsize=9, color=INK2)
    ax.set_xscale("log")
    ax.set_xticks([6, 10, 20, 60])
    ax.set_xticklabels(["6", "10", "20", "60"])
    ax.minorticks_off()
    ax.set_yticks([4, 5, 8])
    ax.set_yticklabels(["4×4", "5×5", "8×8"])
    ax.set_ylim(3.4, 9.6)
    ax.set_xlim(4.6, 95)
    ax.grid(True, color=GRID, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.set_xlabel("Number of floors (long and thin to the right)")
    ax.set_ylabel("Rooms per floor (wider going up)")
    ax.set_title("Each point is one dense building, labelled with its passages per room", loc="left")
    fig.savefig(out / "fig4_shape_map.png")
    plt.close(fig)


def fig5_grid_of_dots(dense, sparse, out):
    styles = [("Corridor", ROOM, "s"), ("Up stairs", BLUE, "^"), ("Down stairs", ORANGE, "v")]
    fig, axes = plt.subplots(2, 2, figsize=(8.6, 8.6))
    for row, size in enumerate((96, 640)):
        dense_inst, floors = dense[f"elist{size}d"]
        order = sorted(floors.floor_of, key=lambda room: (floors.floor_of[room], room))
        index = {room: i for i, room in enumerate(order)}
        for col, inst in enumerate((dense_inst, sparse[f"elist{size}"])):
            ax = axes[row, col]
            groups = {0: [], 1: [], 2: []}
            for arc in inst.arcs:
                step = floors.floor_of[arc.head] - floors.floor_of[arc.tail]
                groups[0 if step == 0 else 1 if step > 0 else 2].append((index[arc.head], index[arc.tail]))
            for g, (label, colour, marker) in enumerate(styles):
                if groups[g]:
                    ax.scatter(*zip(*groups[g]), s=7 if size == 96 else 0.9, color=colour, marker=marker,
                               linewidths=0, label=label)
            for f in range(1, floors.count):
                edge = f * floors.rooms_per_floor - 0.5
                ax.axhline(edge, color=GRID, lw=0.7, zorder=0)
                ax.axvline(edge, color=GRID, lw=0.7, zorder=0)
            ax.set_xlim(-1, inst.n)
            ax.set_ylim(inst.n, -1)
            ax.set_aspect("equal")
            ax.set_title(f"{inst.name}, {inst.m:,} passages", loc="left")
            ax.tick_params(length=0)
            ax.set_xlabel("To room (ordered by floor)")
            ax.set_ylabel("From room (ordered by floor)")
    handles = [plt.Line2D([], [], ls="", marker=m, color=c, ms=8, label=lab) for lab, c, m in styles]
    fig.legend(handles=handles, loc="upper left", ncol=3, bbox_to_anchor=(0.07, 1.02), handletextpad=0.2,
               columnspacing=1.5)
    fig.tight_layout()
    fig.savefig(out / "fig5_grid_of_dots.png")
    plt.close(fig)


def fig6_reachability(dense, sparse, out):
    fig = plt.figure(figsize=(10.5, 5.6))
    grid = fig.add_gridspec(2, 1, height_ratios=[1, 1.15], hspace=0.28)
    ax = fig.add_subplot(grid[0])
    _, floors = dense["elist96d"]
    inst = sparse["elist96"]
    reach = reachable_from(inst, inst.s)
    pos = {room: building_xy(floors, room) for room in floors.floor_of}
    for arc in inst.arcs:
        hot = arc.tail == inst.s
        ax.annotate("", xy=pos[arc.head], xytext=pos[arc.tail], zorder=4 if hot else 1,
                    arrowprops=dict(arrowstyle="-|>", color=AQUA if hot else ROOM, lw=2 if hot else 0.5,
                                    alpha=1 if hot else 0.75, shrinkA=2, shrinkB=2,
                                    mutation_scale=9 if hot else 5))
    ax.scatter(*zip(*[pos[r] for r in pos if r not in reach]), s=15, color=ROOM, zorder=3)
    ax.scatter(*zip(*[pos[r] for r in reach]), s=56, color=AQUA, edgecolor="white", lw=1.5, zorder=5)
    ax.scatter(*pos[inst.t], s=95, color=ORANGE, marker="s", edgecolor="white", lw=1.5, zorder=5)
    label_floors(ax, floors)
    ax.set_title(f"elist96: the start reaches {len(reach)} of {inst.n} rooms and the exit has no way in",
                 loc="left", pad=26)
    key = [plt.Line2D([], [], ls="", marker="o", color=AQUA, ms=8, label="Start and rooms it can reach"),
           plt.Line2D([], [], ls="", marker="o", color=ROOM, ms=6, label="Other rooms"),
           plt.Line2D([], [], ls="", marker="s", color=ORANGE, ms=8, label="Exit")]
    ax.legend(handles=key, loc="lower left", ncol=3, bbox_to_anchor=(0, 0.98), borderaxespad=0,
              handletextpad=0.2, columnspacing=1.5, fontsize=9)
    ax.set_xlim(-0.7, 3 + (floors.count - 1) * FLOOR_STEP + 0.7)
    ax.set_ylim(-1.4, 3.4)
    ax.axis("off")

    ax = fig.add_subplot(grid[1])
    rows = [(name, sparse[name].n, len(reachable_from(sparse[name], sparse[name].s))) for name in SPARSE]
    ys = list(range(len(rows)))[::-1]
    ax.barh(ys, [100 * r / n for _, n, r in rows], height=0.56, color=AQUA, zorder=2)
    for y, (_, n, r) in zip(ys, rows):
        ax.text(100 * r / n + 0.12, y, f"{r} of {n:,} rooms", va="center", fontsize=9, color=INK2)
    ax.set_yticks(ys)
    ax.set_yticklabels([name for name, _, _ in rows])
    ax.tick_params(length=0)
    ax.set_xlim(0, 6.5)
    ax.xaxis.grid(True, color=GRID, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel("Rooms the start can reach, one-way reading (%)")
    fig.savefig(out / "fig6_reachability_sparse.png")
    plt.close(fig)


def fig7_walk_back(dense, out):
    fig, ax = plt.subplots(figsize=(9.2, 3.5))
    ys = list(range(len(DENSE)))[::-1]
    for y, name in zip(ys, DENSE):
        inst, floors = dense[name]
        flood, flow = source_flood(inst), floors.stair_sum_max_flow
        out_share = 100 * flow / flood
        ax.barh(y, out_share, height=0.56, color=BLUE, edgecolor="white", lw=2, zorder=2)
        ax.barh(y, 100 - out_share, left=out_share, height=0.56, color=ORANGE, edgecolor="white", lw=2, zorder=2)
        ax.text(out_share / 2, y, f"{out_share:.0f}%", ha="center", va="center", color="white", fontsize=9.5)
        ax.text(out_share + (100 - out_share) / 2, y, f"{100 - out_share:.0f}%", ha="center", va="center",
                color="white", fontsize=9.5)
        ax.text(101.5, y, f"{units(flood):,.2f} sent, {units(flow):,.2f} get out", va="center", fontsize=9, color=INK2)
    ax.set_yticks(ys)
    ax.set_yticklabels(DENSE)
    ax.tick_params(length=0)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Share of the people preflow-push sends from the start (%)")
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (BLUE, ORANGE)]
    ax.legend(handles, ["Reach the exit", "Must walk back to the start"], loc="lower left", ncol=2,
              bbox_to_anchor=(-0.01, 1.0), borderaxespad=0)
    fig.savefig(out / "fig7_walk_back_prediction.png")
    plt.close(fig)


# Mini building drawing: floor 1 on the left, floor 2 on the right, rooms as in docs/mini_building.md.
MINI_XY = {1: (0, 1), 2: (1, 1), 3: (0, 0), 4: (1, 0), 5: (2.6, 1), 6: (3.6, 1), 7: (2.6, 0), 8: (3.6, 0)}
MINI_BEND = {(1, 6): -0.3, (3, 8): 0.3, (5, 1): 0.2, (8, 4): -0.2}  # stairs that curve around rooms
MINI_CUT_X = 1.8


def mini_passage(ax, tail, head, colour, lw, dashed=False, arrow=True):
    ax.annotate("", xy=MINI_XY[head], xytext=MINI_XY[tail], zorder=2,
                arrowprops=dict(arrowstyle="-|>" if arrow else "-", color=colour, lw=lw, shrinkA=11, shrinkB=11,
                                linestyle=(0, (4, 3)) if dashed else "-", mutation_scale=11,
                                connectionstyle=f"arc3,rad={MINI_BEND.get((tail, head), 0)}"))


def mini_rooms(ax, inst):
    for room, (x, y) in MINI_XY.items():
        special = room in (inst.s, inst.t)
        ax.scatter(x, y, s=330, marker="s" if room == inst.t else "o", color=AQUA if special else "white",
                   edgecolor=AQUA if special else INK2, lw=1, zorder=3)
        ax.text(x, y, str(room), ha="center", va="center", fontsize=9.5, zorder=4,
                color="white" if special else INK, fontweight="bold" if special else "normal")
    ax.text(-0.2, 1, "start", ha="right", va="center", fontsize=9, color=INK2)
    ax.text(3.8, 0, "exit", ha="left", va="center", fontsize=9, color=INK2)
    ax.set_xlim(-0.75, 4.25)
    ax.set_ylim(-0.95, 1.85)
    ax.set_aspect("equal")
    ax.axis("off")


def fig8_mini_building(out):
    inst = read_instance(MINI_BUILDING)
    corridor = max(arc.capacity for arc in inst.arcs)
    people: dict[tuple[int, int], int] = {}
    for route, size in MINI_GROUPS:
        for step in zip(route, route[1:]):
            people[step] = people.get(step, 0) + size
    flows = [people.get((arc.tail, arc.head), 0) * SCALE for arc in inst.arcs]
    cert = check_flow(inst, flows, 9 * SCALE)  # the drawn answer must pass the verifier
    stair_labels = {(1, 6): (1.2, 1.53, "bottom"), (2, 5): (1.4, 1.04, "bottom"),
                    (4, 7): (1.4, 0.04, "bottom"), (3, 8): (1.2, -0.52, "top")}
    corridor_labels = {(1, 2): (0.5, 0.93, "center", "top"), (1, 3): (0.07, 0.5, "left", "center"),
                       (3, 4): (0.5, 0.07, "center", "bottom"), (5, 7): (2.67, 0.5, "left", "center"),
                       (6, 8): (3.53, 0.5, "right", "center"), (7, 8): (3.1, 0.07, "center", "bottom")}

    fig, (left, right) = plt.subplots(1, 2, figsize=(10.5, 3.5))
    for arc in inst.arcs:  # left: the building and its capacities
        if arc.capacity == corridor:
            if arc.tail < arc.head:
                mini_passage(left, arc.tail, arc.head, ROOM, 2.2, arrow=False)
        elif (arc.tail, arc.head) in stair_labels:
            mini_passage(left, arc.tail, arc.head, BLUE, 1.6)
            x, y, va = stair_labels[(arc.tail, arc.head)]
            left.text(x, y, to_text(arc.capacity), ha="center", va=va, fontsize=10, color=BLUE)
        else:
            mini_passage(left, arc.tail, arc.head, MUTED, 1, dashed=True)
    for x, floor in ((0.5, 1), (3.1, 2)):
        left.text(x, -0.85, f"Floor {floor}, corridors {to_text(corridor)}", ha="center", fontsize=9, color=INK2)
    mini_rooms(left, inst)
    left.set_title("The building: up stairs hold 3 + 2 + 3 + 1", loc="left")

    for arc, x in zip(inst.arcs, flows):  # right: the best answer and the narrowest set of stairs
        step = (arc.tail, arc.head)
        if x:
            mini_passage(right, *step, BLUE, 0.6 + 0.45 * x / SCALE)
            if step in stair_labels:
                lx, ly, va = stair_labels[step]
                right.text(lx, ly, f"{to_text(x)} of {to_text(arc.capacity)}", ha="center", va=va, fontsize=9.5)
            else:
                lx, ly, ha, va = corridor_labels[step]
                right.text(lx, ly, to_text(x), ha=ha, va=va, fontsize=9.5)
        elif arc.capacity != corridor or arc.tail < arc.head:
            mini_passage(right, *step, GRID, 1, dashed=arc.capacity != corridor, arrow=False)
    right.plot([MINI_CUT_X, MINI_CUT_X], [-0.8, 1.75], color=ORANGE, lw=1.6, ls=(0, (5, 3)), zorder=1)
    right.text(MINI_CUT_X + 0.08, -0.8, f"cut = {to_text(cert.cut_capacity)}", color=ORANGE, fontsize=9.5,
               va="bottom")
    mini_rooms(right, inst)
    right.set_title(f"Best answer: {to_text(cert.value)} people per minute, every up stair full", loc="left")

    key = [plt.Line2D([], [], color=ROOM, lw=2.2, label="Corridor (two-way)"),
           plt.Line2D([], [], color=BLUE, lw=1.6, label="Up stair, or people moving"),
           plt.Line2D([], [], color=MUTED, lw=1, ls=(0, (4, 3)), label="Down stair (1 each)"),
           plt.Line2D([], [], color=ORANGE, lw=1.6, ls=(0, (5, 3)), label="Narrowest set of stairs")]
    fig.legend(handles=key, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.04), fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "fig8_mini_building.png")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=PROJECT / "Data")
    parser.add_argument("--out", type=Path, default=PROJECT / "docs" / "figures")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    dense = {}
    for name in DENSE:
        inst = read_instance(args.data / f"{name}.txt")
        dense[name] = (inst, find_floors(inst))
    sparse = {name: read_instance(args.data / f"{name}.txt") for name in SPARSE}

    fig1_floors_and_stairs(dense, args.out)
    fig2_bottleneck_profile(dense, args.out)
    fig3_capacity_groups(dense, args.out)
    fig4_shape_map(dense, args.out)
    fig5_grid_of_dots(dense, sparse, args.out)
    fig6_reachability(dense, sparse, args.out)
    fig7_walk_back(dense, args.out)
    fig8_mini_building(args.out)
    print(f"Wrote 8 figures to {args.out}")
    assert math.isclose(units(dense["elist96d"][1].stair_sum_max_flow), 1.3784)


if __name__ == "__main__":
    main()
