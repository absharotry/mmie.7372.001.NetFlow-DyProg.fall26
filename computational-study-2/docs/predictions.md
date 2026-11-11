# Predictions, recorded before any solver exists

Recorded 2026-11-09, at the end of Phase 1. No solver code had been written at that point. The
predictions below are not edited after Phase 3 starts. Phase 6 fills in the outcome column, and the
report shows 3 or 4 of them against what happened.

Frozen 2026-11-10, when Phase 3 (the first solver) started. Outcomes filled in 2026-11-10 from
Phase 6 (`results/winners.csv`, `results/prediction_evidence.csv`); the predictions are unchanged.

Every number comes from the data files (`results/data_cards.csv`), not from any solver.

| # | Prediction | Basis | Outcome |
|---|---|---|---|
| P1 | If worst-case bounds predicted practice, FIFO preflow-push would beat shortest augmenting path by a factor that rises with passages per room, most on `elist640d` | Bounds n²m against n³ differ by m/n (table below) | **Not supported.** Over 30 door orders FIFO was clearly faster on 2 of 6 dense files (`elist160d` 1.11×, `elist500d` 1.72×), SAP on 3 (`elist96d`, `elist200d`, `elist960d`), and `elist640d`, the highest m/n, had no clear winner (ratio 1.00). No rising trend with m/n (Spearman 0.37, 6 files) |
| P2 | Every group shortest augmenting path sends walks at least the shortest route (table below) | Distance labels never decrease (AMO Lemma 7.5) | **Held.** On all 6 dense files and all 31 orders, the first group took exactly the shortest route and none took a shorter one; mean routes were 13.9 to 71.1 passages |
| P3 | Most of the people preflow-push sends from the start must walk back: 66% to 79% on the dense files (table below), so walk-back work will be a large share of its effort | The start's passages total far more than the max flow | **Partly.** The share walking back is fixed by the data (66% to 79%), and most of FIFO's effort comes after the maximum preflow (37% to 99% of passages checked). But little of it happens at rooms already labelled n or more: 0.3% to 2.4% of pushes as taught, 0.7% to 22% with speed-ups. Most late work is relabelling rooms up towards n |
| P4 | On the 8 zero-flow files, shortest augmenting path makes no augmentations and stops after its first backward search | The search from the exit never reaches the start | **Held** on all 8 zero-flow files, as taught and with `numb` |
| P5 | On the 8 zero-flow files, preflow-push works only at the start and its immediate neighbours, which are dead ends | The start reaches only itself and its neighbours | **Held.** All four preflow-push settings worked only on the start and its neighbours (4 to 11 rooms) on all 8 zero-flow files |
| P6 | Highest-label makes fewer non-saturating pushes than FIFO | AMO p. 233 | **Partly** (file order only). As taught, highest-label made fewer non-saturating pushes on 6 of 13 cases (from 28% fewer to 18% more); with speed-ups on 10 of 13 (from 66% fewer to 77% more) |
| P7 | Speed-ups help preflow-push more than shortest augmenting path | AMO pp. 229–230 | **Held** on 12 of 13 cases by time, 11 of 13 by work. On the dense files the speed-ups cut preflow-push's time 2.8 to 57 times and SAP's 1.2 to 11 times. Exception: `elist200` two-way (SAP 27×, preflow-push 19×) |

## Numbers behind P1 to P3

Directed reading, the 6 files that carry flow:

| File | m/n (P1) | Shortest route, passages (P2) | Sent from start | Max flow | Must walk back (P3) |
|---|---|---|---|---|---|
| elist96d | 5.50 | 5 | 6.4888 | 1.3784 | 78.8% |
| elist160d | 5.70 | 9 | 978.1452 | 211.8491 | 78.3% |
| elist200d | 6.70 | 9 | 10.1297 | 2.1353 | 78.9% |
| elist500d | 7.95 | 19 | 3,029.637 | 702.1112 | 76.8% |
| elist640d | 19.70 | 9 | 2.5717 | 0.8817 | 65.7% |
| elist960d | 9.88 | 59 | 1,623.2095 | 335.1562 | 79.4% |

Two-way supplement, shortest route for P2: `elist96` 6, `elist160` 10, `elist200` 8, `elist500` 20,
`elist640` 9, `elist960` 59, `elist1440` 9.
