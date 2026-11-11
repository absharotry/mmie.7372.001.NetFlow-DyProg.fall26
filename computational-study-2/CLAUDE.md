# Computational Study 2: maximum flow, shortest augmenting path vs preflow-push

Course project (MMIE 7372, Network Flows). Compare the shortest augmenting path algorithm and the
preflow-push algorithm on all 14 `elist*.txt` datasets in `Data/`.

Full plan, evidence and open decisions: `docs/plan_of_action.md`. Data model, measure definitions,
decision rules and visualization plan: `docs/data_modeling.md` (read before writing any code; data
visualization is central to this study). Assignment: `docs/assignment.md` (currently the author's
description; the instructor's text is still to be added).

## Working agreement (read this first)

This is a learning project. Work in small steps.
- Do one phase at a time, and do not start the next without approval. Do not scaffold future phases.
- Share the plan before execution. Before non-trivial code, explain the approach and wait for an OK.
- After writing code, explain what it does and why. Point out anything a grader or exam could probe.
- Explain from the basics, in plain terms first, with small worked examples. Use the floors-and-people
  analogy (vocabulary in `docs/plan_of_action.md`, Section 5), not other analogies.
- Prefer clear code over clever code. Comments connect code to theory and cite AMO sections.
- Never silently change a modeling decision (arc direction, dropped arcs, capacity handling). Ask.

## Phases

- [x] 0. Environment: install, freeze `requirements-lock.txt`
- [x] 1. Survey the buildings: reader, floors, data cards, figures, written predictions
- [x] 2. Mini building: residual network, verifier, 8-room test worked by hand
- [x] 3. Shortest augmenting path, `numb`, counters
- [x] 4. Preflow-push: FIFO, highest-label, heuristics, counters
- [x] 5. Benchmark harness, runs on all 14 files, then the sparse-undirected supplement
- [x] 6. Arc-order robustness runs, compare with predictions
- [x] 7. Analysis and report: `computational_study_2.ipynb` (Colab notebook = report + code)

## Status (2026-11-10)

Plan and design choices approved by the author. Phases 0 to 7 complete; the report is the Colab
notebook `computational_study_2.ipynb` (author's decision, 2026-11-10: notebook is the report and
the source; only Section 6, the 30-order M2 results, reads from this GitHub repo). Due 2026-11-10. Phase 1: reader, audit,
floor finder, data cards, seven figures, and predictions (`docs/predictions.md`, frozen once Phase 3
starts). Phase 2: residual network (`residual.py`), verifier (`verify.py`), and the 8-room mini
building worked by hand (`docs/mini_building.md`, figure 8). Phase 3: shortest augmenting path
(`sap.py`), as taught and with `numb`, checked against hand traces, AMO Figure 7.4, 300 random
networks and NetworkX, and all 21 data cases. Predictions are frozen. Phase 4: preflow-push
(`preflow.py`), FIFO and highest-label, each as taught and with gap and global relabeling, checked
against the hand trace, AMO Figure 7.15 and 300 random networks; all six settings agree on all 21
data cases. Phase 5: benchmark harness (`bench.py`, `scripts/run_benchmark.py`); all six settings
checked and timed (31 repeats, one shuffled schedule) on all 21 cases at file order, results in
`results/runs_baseline.csv` and `results/times_baseline.csv`. No winners decided yet (Phase 6).
The author chose to keep the code structure as is (no merged entry point) on 2026-11-10. Phase 6:
30 shuffled door orders for SAP, SAP+numb, PP-FIFO and PP-FIFO+h on the 13 cases that carry flow
(`scripts/run_shuffles.py`), winner rule and prediction outcomes (`scripts/compare_orders.py`,
`winners.py`), figure R6. Phase 7 (the report) needs its plan shared and approved before writing.
Decided by the author: every data file is
used exactly as given (directed, nothing reinterpreted or replaced) for the main study. The 7 sparse
files are also solved as undirected, as a separate labelled supplement. Dense files stay directed.
The headline comparison is the conventional algorithms as taught; speed-ups are kept as a separate
tuned comparison and are never mixed into the headline. Highest-label (PP-HL, PP-HL+h) runs only at
the baseline file order in Phase 5, as a secondary check and to test P6; the Phase 6 shuffles cover
only SAP, SAP+numb, PP-FIFO and PP-FIFO+h.

## Final report

Simple explanations, straight to the point. Goal: study and compare (1) shortest augmenting path and
(2) preflow-push on all of the datasets. Order: quick overview of the data; initial findings;
assumptions; running the algorithms; comparison of all datasets and results. `docs/data_modeling.md`
is backing detail, not the report text. Full outline and report rules: `docs/plan_of_action.md`,
Section 5 ("Final report"). Build around one master results table covering every dataset, and keep
the main story to shortest augmenting path against FIFO preflow-push.

## Report notes: algorithm variants (MUST appear in the final write-up)

Whenever an implementation is not the textbook algorithm, the report must say what differs and how it
affects correctness or complexity. Add to this list as soon as a new case is found.

- Lecture 3 covers only generic preflow-push. FIFO and highest-label (AMO 7.7, 7.8) are node-selection
  rules added to it.
- `numb` early termination (AMO 7.4), gap and global relabeling (AMO 7.6) are not in Lecture 3 and are
  separate switches. "As taught" results have them off.
- Capacities are scaled by 10⁴ to exact integers to meet Assumption 6.2. No tolerance is used.
- Files contain arcs into s and out of t, which AMO's preflow-push discussion excludes (p. 224). They
  are kept; flow value is net flow into t.
- The supplement reads sparse files as undirected using AMO Section 2.4 (each edge becomes two arcs of
  the same capacity). It is a different reading of the data, not a different algorithm.
- SAP relabel when a room has no passage with space left: AMO's min{d(j) + 1} is over an empty set
  and undefined. `sap.py` gives n ("cannot reach the exit"), which keeps the labels valid; at the
  start it ends the run. Each room's passages are tried in file order (AMO p. 216 allows any fixed
  order; its Figure 7.4 example uses smallest j, which our test file lists in that order).
- SAP stores the route as the residual record used to enter each room rather than the previous room.
  With one record pair per room pair (Assumption 6.4) the two are equivalent.
- Preflow-push heuristics are one-phase: gap and global relabeling only raise labels (gap: rooms
  above an empty label k < n go to n; global relabeling: exact distance, or at least n for rooms that
  cannot reach the exit), and rooms at n or above keep pushing their people back to the start. AMO
  (pp. 229-230) describes them inside a two-phase method that sets such rooms aside and returns their
  excess in a separate step (Exercise 7.11). Labels stay valid, so AMO's lemmas still hold.
- Global relabeling runs every n relabels (AMO's "after alpha n relabels", alpha = 1).
- Ties: FIFO starts in the order of the start's passages; highest-label keeps one last-in, first-out
  stack per label (AMO p. 233 allows stacks or queues).
- Push counts follow AMO p. 225: saturating means delta = r_ij, even if the room is also emptied. The
  opening flood (AMO Figure 7.11a) is counted separately, not as pushes.

## Known pitfalls

- Exactly 6 of the 14 files carry flow when read as directed. Never fold the 8 zero-flow files into
  speed or growth results, and never pool supplement results with the main results.
- Unreachable nodes need d = n after the backward search. A relabel with no residual arcs needs a
  defined result: SAP uses n; preflow-push never meets the case (AMO Lemma 7.11), and its `min()`
  has no default so that a bug would fail loudly.
- Preflow-push labels can reach 2n − 1, while SAP's `numb` covers 0..n − 1. Size arrays accordingly.
- Antiparallel arcs share one residual pair (Assumption 6.4). Recover arc flow as max(u_ij − r_ij, 0).
- Rebuild the residual state before every timed repeat (`Residual.fresh()`). Algorithms mutate it.
- A run counts only if `verify.check_flow` and `verify.check_residual` pass. Keep `check_flow`
  independent: it must never use `residual.py` or solver code.
- Timed runs last milliseconds: keep garbage collection off and shuffle the run order.
- This repo is public. Never commit the textbook, slides, datasets or personal notes.

## Layout

```
Data/                  the 14 datasets (gitignored) and SOURCES.md (checksums)
course_files_export/   textbook and slides (gitignored)
docs/                  assignment, plan of action, data model, figures, later report
src/maxflow/           package code
tests/                 pytest correctness tests; tests/data/ holds the mini building, AMO Figs 7.4, 7.15
scripts/               runnable entry points
results/               CSV outputs, figures
```

## Commands

- Shared venv at the repo root: `source ../.venv/bin/activate`
- Install (from this folder): `pip install -r requirements.txt && pip install -e .`
- Tests (from this folder): `pytest -q`
- Data cards (from this folder): `python scripts/survey_data.py` writes `results/data_cards.csv`
- Data figures (from this folder): `python scripts/make_data_figures.py` writes the 8 figures in
  `docs/figures/`
- Benchmark (from this folder, machine idle, about 8 minutes): `python scripts/run_benchmark.py`
  writes `results/runs_baseline.csv` and `results/times_baseline.csv`
- Shuffled orders (machine idle, about 28 minutes): `python scripts/run_shuffles.py`, then
  `python scripts/compare_orders.py` writes `results/winners.csv`, `results/prediction_evidence.csv`
  and `docs/figures/r6_shuffle_ratios.png`
- Solvers must never import `maxflow.structure` (decision DM7); it is for analysis only.
