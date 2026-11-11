# Plan of action: shortest augmenting path vs preflow-push

Status: **plan approved by the author, 2026-11-09. Phases 0 to 6 complete: both algorithms are
written, verified and timed; winners decided over 30 door orders; the report is next.** Each phase below starts only after approval of the one before it.

**Goal: study and compare (1) shortest augmenting path and (2) preflow-push on all of the datasets.**

Sources reviewed: the 14 data files, Lecture 3 (Sections 6 and 7), AMO Chapters 6, 7 and 18, the
Study 1 code, report and decision log, the project knowledge file, and the GitHub repo.

## 1. What the data actually allows

Every file was parsed and solved with NetworkX as a scoping check, using exact integer capacities.
All 14 files are well formed: the header matches the arc count, node ids are in range, and there are
no duplicate arcs, self-loops, or non-positive capacities.

**Only 6 of the 14 files carry any flow.**

| File | n | m | Density | m/n | Antiparallel pairs | Max flow | Min-cut arcs |
|---|---|---|---|---|---|---|---|
| elist96d | 96 | 528 | 0.0579 | 5.5 | 151 | 1.3784 | 16 |
| elist160d | 160 | 912 | 0.0358 | 5.7 | 261 | 211.8491 | 32 |
| elist200d | 200 | 1,340 | 0.0337 | 6.7 | 340 | 2.1353 | 25 |
| elist500d | 500 | 3,975 | 0.0159 | 8.0 | 880 | 702.1112 | 100 |
| elist640d | 640 | 12,608 | 0.0308 | 19.7 | 1,846 | 0.8817 | 512 |
| elist960d | 960 | 9,488 | 0.0103 | 9.9 | 2,018 | 335.1562 | 80 |

**The other 8 files have max flow 0**, because no directed path joins s to t (reach counts include
s and t themselves):

| File | n | m | Nodes s can reach | Nodes that can reach t | Max flow if read as undirected |
|---|---|---|---|---|---|
| elist96 | 96 | 187 | 4 | 1 | 4.6653 |
| elist160 | 160 | 285 | 5 | 1 | 970.3170 |
| elist200 | 200 | 483 | 4 | 2 | 5.0001 |
| elist500 | 500 | 1,040 | 7 | 1 | 3,013.5749 |
| elist640 | 640 | 3,037 | 11 | 3 | 0.5477 |
| elist960 | 960 | 2,061 | 8 | 1 | 61.3107 |
| elist1440 | 1,440 | 5,397 | 11 | 4 | 111.0133 |
| elist1440d | 1,440 | 5,397 | 11 | 4 | 111.0133 |

All seven sparse graphs are acyclic. Every successor of s is a dead end (out-degree 0), and every
predecessor of t has in-degree 0. The sparse arcs are all contained in the matching dense file, with
some capacities changed. `elist1440d` is a byte-for-byte copy of `elist1440`.

On a zero-flow file neither algorithm does meaningful work. SAP's first backward search never reaches
s, so it stops at once. Preflow-push floods the arcs out of s and sends that excess straight back.

### Decision (author, 2026-11-08): files are used exactly as given

Every file is read as directed, with its arcs, capacities, s and t unchanged. Nothing is reinterpreted,
repaired or replaced. `elist1440d` is analysed as supplied, and its identity with `elist1440` is
reported as a fact about the data. The data's source says these edge lists may be read as directed
or undirected (`Data/SOURCES.md`); the report will state that the main study reads them as directed.

### Decision (author, 2026-11-08): sparse-undirected supplement

In addition to the main study, the 7 sparse files are also solved with each arc read as an undirected
edge. These results are a separate, labelled supplement and are never pooled with the main results.
`elist1440d` is not repeated in the supplement because it is identical to `elist1440`. The dense files
are not read as undirected: they list both directions for some node pairs, often with different
capacities, so one capacity per pair would require a rule the data does not provide.

## 2. What the course defines

| Item | Lecture 3 | AMO |
|---|---|---|
| SAP: exact labels, advance / retreat / relabel / augment, stop at d(s) >= n | Section 6 | Section 7.4, Figures 7.5 and 7.6 |
| `numb` array early termination | not covered | Section 7.4, pp. 219-220 |
| Generic preflow-push, O(n²m) | Section 7 | Section 7.6, Figures 7.11 and 7.12 |
| FIFO selection, O(n³) | not covered | Section 7.7 |
| Highest-label selection, O(n²√m) | not covered | Section 7.8 |
| Global relabeling and gap heuristics | not covered | Section 7.6, pp. 229-230 |
| Assumptions: directed, integer capacities, reverse arcs exist, no parallel arcs | Section 1 | Assumptions 6.1 to 6.5 |
| Representative operation counts | not covered | Section 18.2 |

The generic algorithm needs a rule for choosing the next active node, so a selection rule has to be
picked. FIFO is the simplest rule with a proven bound.

## 3. Proposed design

**Algorithms, all written from scratch in plain Python.**

| Label | Algorithm | Role |
|---|---|---|
| SAP | Figures 7.5 and 7.6 exactly | **headline, as taught** |
| PP-FIFO | Generic preflow-push with FIFO selection | **headline, as taught** |
| SAP+numb | SAP with `numb` termination | tuned comparison |
| PP-FIFO+h | PP-FIFO with gap and global relabeling | tuned comparison |
| PP-HL | Highest-label selection | secondary, baseline order only |
| PP-HL+h | Highest-label with gap and global relabeling | secondary, baseline order only |

Heuristics are switches, so each variant can be timed with and without them. AMO warns that
preflow-push depends on them in practice, so "preflow-push is slower" would not be a fair conclusion
from the plain versions alone.

**Shared code**, so that speed differences come from the algorithms: one reader, one residual-network
structure, and one verifier.

**Exact integer arithmetic instead of a tolerance.** Every capacity has at most 4 decimals, so
multiplying by 10⁴ gives exact integers (largest 1.5 × 10⁷). This satisfies Assumption 6.2 directly,
leaves the algorithms unchanged, and removes floating-point round-off. Flow values are divided by 10⁴
only for reporting.

**Residual network in AMO's form (Assumption 6.4).** Each node pair {i, j} gets one pair of residual
records, with r_ij = u_ij − x_ij + x_ji. Antiparallel arcs (present in every non-trivial file) start
with r_ij = u_ij and r_ji = u_ji. Arc flows are recovered as max(u_ij − r_ij, 0).

**Arcs entering s or leaving t stay in.** The dense files have 3 to 13 of each. They cannot change the
max flow, and the value is measured as net flow into t. AMO's remark that no arc leaves t in
preflow-push (p. 224) is a report note.

**Undirected supplement (AMO Section 2.4, p. 39).** A reader option replaces each edge {i, j} of
capacity u with arcs (i, j) and (j, i), both of capacity u. The solvers are unchanged. The verifier
checks the net flow, |x_ij − x_ji| ≤ u.

**Verification, required before any timing is trusted.** Every run, on every file, must pass:

1. Capacity bounds on every arc, and flow conservation at every node except s and t.
2. Min-cut certificate: the cut around the nodes reachable from s in the final residual network has
   capacity equal to the flow value.
3. All variants return the same integer value.
4. That value equals NetworkX's, on the 14 files and on random small graphs, including graphs with
   antiparallel arcs and an unreachable sink.
5. On the 6 dense files, that value equals the weakest gap's total forward capacity, a check that
   needs no solver at all.

**Measurements.**

- *Time:* `perf_counter` around the solve only, with garbage collection off. Each run takes
  milliseconds, so use one discarded warm-up and 31 timed repeats, rebuilt untimed each time, in
  shuffled order. Report median and interquartile range. (Study 1 used 5 repeats, but those runs were
  far longer.)
- *Operation counts,* which do not depend on the machine: arc inspections and relabels for all;
  augmentations, advances, retreats and total path length for SAP; saturating and non-saturating
  pushes, node examinations and global relabels for preflow-push; and the share of work done after
  the max preflow is reached (AMO p. 229).
- *Robustness:* results depend on arc order, so repeat with 30 seeded shuffles of the adjacency lists
  and compare the algorithms pairwise per instance. With only 6 non-trivial instances, this is how
  the study can tell a real difference from luck.

## 4. Analysis the report will contain

1. Characteristics of all 14 instances, with the zero-flow group labelled and reported separately.
2. Head-to-head time and operation counts on the 6 non-trivial instances, as taught and tuned.
3. Where each algorithm spends its effort, tied to AMO's bottleneck operations: path traversal for
   SAP and non-saturating pushes for preflow-push.
4. Behaviour against size, density and shape, using n, m, m/n, and frames × grid size (long networks
   such as `elist960d` against wide ones such as `elist640d`).
5. Actual operation counts against the worst-case bounds.
6. Effect of the heuristics.
7. Limits of the evidence, stated plainly.
8. Supplement: the same time and operation-count comparison on the 7 sparse files read as undirected,
   in its own section, noting that the bottleneck is the few edges at the sink in `elist160`,
   `elist200` and `elist500`.

**Hypotheses to test, not results.** Since m > n on all six instances, the worst-case bounds favour
FIFO over SAP by a factor of m/n, from 5.5 to 19.7, so `elist640d` is where preflow-push should gain
most if the bounds predict practice. AMO reports highest-label as the best in practice (p. 233).

**Limits to state in the report.**

- A sparse-vs-dense comparison at the same n is not possible in the main study, because every sparse
  file is zero-flow. The supplement does not repair this: its capacities and direction differ from
  the dense files (`elist160` read as undirected carries 970, `elist160d` only 212).
- Growth fits rest on 6 points where n and m rise together, so slopes are descriptive only.
- Python interpreter overhead can hide operation-count differences, so every speed claim needs both
  timings and counts.

## 5. Phases

Same working agreement as Study 1: one phase at a time, explain before non-trivial code, then walk
through what was built.

| Phase | Name | Work | Done when |
|---|---|---|---|
| 0 | Set up | Install the package, freeze `requirements-lock.txt` | `pytest` runs |
| 1 | Survey the buildings | Reader (with undirected option); find floors; one-line card per file; add up the stairs; regenerate the seven figures in `data_modeling.md` from project code; write predictions in `docs/predictions.md` | all 14 files load; cards match Section 1; narrowest stairs equal the known max flow on the 6 dense files; acceptance checks in `data_modeling.md` Section 13 pass |
| 2 | Build a mini building | Residual network and verifier; 8-room test building (2 floors of 2×2) worked by hand | verifier accepts correct flows and rejects deliberately broken ones |
| 3 | One group at a time | SAP and `numb`, with counters; walk through the mini building and AMO Figure 7.4 | matches oracle on random graphs |
| 4 | Everyone in at once | Preflow-push: FIFO, highest-label, heuristics, counters; walk through the mini building | all variants agree and pass verification |
| 5 | Time the runs | Benchmark harness, runs on all 14 files, then the sparse-undirected supplement | results CSV with machine and library versions; a column marks the reading |
| 6 | Stress-test the results | Arc-order robustness runs for the four headline and tuned settings; compare with the predictions | per-instance paired comparison |
| 7 | Write it up | Analysis, shape map, report (Markdown and Word), AI-use section as in Study 1 | checked against `assignment.md` |

Total computing time should be minutes, since the largest non-trivial instance has 12,608 arcs.

The data model, measure definitions, decision rules and visualization plan are specified in
`data_modeling.md`. Its Section 13 lists the acceptance checks for Phase 1.

### Final report (author's requirement, 2026-11-09)

The report uses simple explanations and gets straight to the point. Its goal is to study and compare
(1) shortest augmenting path and (2) preflow-push on all of the datasets. Its order is: quick overview
of the data; initial findings; assumptions; running the algorithms; comparison of all datasets and
results. `data_modeling.md` is backing detail and is not the report text.

| Section | Content | Visuals |
|---|---|---|
| Summary | Which algorithm did better, by how much, and where, in one short paragraph | None |
| 1. Quick overview of the data | What the 14 files are, in a few sentences | One small table, Figure 1 |
| 2. Initial findings | 6 files carry flow, 8 have zero flow, flow is limited by the narrowest stairs | Figures 2 and 6 |
| 3. Assumptions | A short bullet list | None |
| 4. Running the algorithms | How each works in 2 or 3 sentences, what was measured, how answers were checked | The 8-room mini building, both algorithms side by side |
| 5. Comparison of all datasets | The master results table and what it shows | 2 or 3 charts |
| 6. Conclusion | Which algorithm to use, and when | None |
| Appendix | Algorithm variants, full tables, how to reproduce, AI use as in Study 1 | Remaining figures |

Report rules (author approved, 2026-11-09):

1. One master table has a row for every dataset: max flow, time and work for each algorithm, and the
   winner. All 14 files appear, with the 7 two-way cases as a labelled block below.
2. The summary states the answer first, so a reader gets the result from it and the master table.
3. The main story is shortest augmenting path against FIFO preflow-push. One short paragraph says
   whether speed-ups or highest-label change the winner, with the numbers in the appendix. All six
   settings run at the baseline order; the 30 shuffles cover the four headline and tuned settings.
4. Each result is explained in one sentence tied to the work the algorithms did.
5. Each chart title states its finding, written only from actual results.
6. A small table shows 3 or 4 predictions against what happened.
7. Writing: define each term once, use short sentences, round numbers in the text with exact values
   in tables, and keep correctness to a line and limits to a few bullets.

### Explaining the data: floors and people (author's decision, 2026-11-08)

Explanations use this analogy. The report introduces it once, states that the networks are synthetic
and that capacities have no units, and otherwise uses AMO's terms.

| Building | AMO term |
|---|---|
| Floor | Frame |
| Room | Node |
| Corridor | Arc inside a frame |
| Up stairs, down stairs | Forward and backward arcs between frames |
| People per minute | Capacity (unitless; illustrative only) |
| Start room, exit room | s, t |
| Narrowest set of up stairs | Minimum cut |
| Room's estimate of steps to the exit | Distance label |
| People waiting in a room | Excess |

## 6. Decisions

The author approved every item below on 2026-11-09, except the two marked as still to provide.

| # | Decision | Outcome |
|---|---|---|
| 1 | Primary preflow-push rule | FIFO; highest-label secondary, run at the baseline order only and left out of the shuffles (**decided** 2026-11-10) |
| 2 | Include the heuristic variants | **decided:** keep them as a separate tuned comparison; the headline stays the conventional algorithms as taught, and the two are never mixed |
| 3 | Sparse files and 1440d | **decided:** run all exactly as given and directed; zero-flow group reported separately and left out of speed and growth analysis; sparse files also solved as undirected in a separate supplement |
| 4 | Capacities | exact integers, scaled by 10⁴ |
| 5 | Optional synthetic instances to strengthen growth analysis (like Study 1's density sweep) | not included unless wanted |
| 6 | Instructor's assignment text | author to paste into `assignment.md` |
| 7 | Explanatory analogy | **decided:** floors and people |
| 8 | Report structure and rules | **decided:** see "Final report" in Section 5 |
| 9 | Timing method, winner rule, results file layout (`data_modeling.md` 10.3, 10.4, 10.7) | as written there |
| 10 | DM4 to DM8 in `data_modeling.md` Section 9 | as written there |
| 11 | Mini building and written predictions | included |
| 12 | Study due date | author to provide |

## 7. Changes from the project knowledge file

| Earlier note | Now | Why |
|---|---|---|
| 4 sparse instances have zero flow | 7 sparse plus 1440d (8 in total) | it checked only for arcs into t; 200, 640 and 1440 have them, but t is still unreachable |
| Analysis of sparse vs dense at the same n | dropped | no sparse file has flow |
| Tolerance ε = 1e-9 | exact integers | all capacities have at most 4 decimals |
| Antiparallel arcs must stay separate; merging is a bug | merged per Assumption 6.4 | merging is AMO's own form; the real risk is losing track of a reverse arc, which the verifier catches |
| Median of 5 runs | warm-up plus 31 | runs last only milliseconds |
| Build in the cloud, re-run locally | build and run locally | the work now happens on the author's machine |
| Arcs look like a grid-like backbone | confirmed and made exact: chains of grid frames from RMFGEN | measured in all 6 dense files; see `Data/SOURCES.md` |
