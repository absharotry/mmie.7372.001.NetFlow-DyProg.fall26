# APSP Benchmark: n× Dijkstra vs Floyd-Warshall

Course project (MMIE 7372, Network Flows). We compare all-pairs shortest paths computed by
(a) running Dijkstra once from every node and (b) Floyd-Warshall, on five real networks:
US Airports, Adolescent Health, Advogato, Slashdot Zoo, Wiki Conflict.

## Assignment requirements (full text: docs/assignment.md)

The report must cover, and be checked against:
1. Both approaches implemented (n x Dijkstra, Floyd-Warshall) and compared on all five datasets.
2. Network characteristics per dataset, including number of nodes and edges.
3. Discussion: (a) performance of each algorithm across the five datasets; (b) how performance
   changes with network size AND density; (c) which network structures favor which algorithm.
4. Any run that cannot complete (time or memory): report it and explain via complexity.
5. Deliverables: the discussion and the scripts.

## Working agreement (read this first)

This is a learning project. Work in small steps.
- Do one phase (or one sub-step) at a time. Don't scaffold future phases ahead of time.
- Before writing non-trivial code, explain the approach briefly and wait for my OK.
- After writing code, explain what it does and why. Point out anything a grader or exam could probe.
- Prefer clear code over clever code. Add comments that connect code to the theory
  (e.g. "this is the relaxation step", "this is the k-th intermediate-vertex sweep").
- Never silently change a modeling decision (weights, directedness, multi-edge handling).
  Raise it as a question.

## Phases

- [x] 0. Environment: git init + .gitignore, venv, install requirements, freeze `requirements-lock.txt`, repo layout
- [x] 1. Implement + validate both algorithms on toy graphs (hand-checkable example + random small graphs vs networkx)
- [x] 2. Load/preprocess datasets; record characteristics (n, m, density, degree stats, components, weighted/signed, reachable-pair fraction).
      Record source URL + SHA-256 checksum of every downloaded archive.
- [x] 3. Benchmark harness: wall time, peak memory, timeout, feasibility pre-check (estimate n² memory, n³ ops before running)
- [~] 4. Run datasets smallest → largest; report infeasible runs with complexity-based explanation
      (done: 3 small datasets in all tiers, 2 large in scipy; pending: pure Dijkstra on the 2 large)
- [x] 5. Synthetic density sweep (fixed n, vary density) to locate the crossover
      (scipy crossover 21% at n=1,000, 27% at n=2,000; pure Python 98% at n=400)
- [x] 6. Analysis + write-up (docs/comparison_report.md + .docx, submitted state 2026-10-13)

## Status (2026-10-13)

Draft report: docs/comparison_report.md (Section 8 lists pending items). Results: results/benchmarks.csv,
results/report_tables.md, figures from scripts/make_report.py. Still to decide with the user:
- [x] Pure Dijkstra: Slashdot full (24.8 min); Wiki Conflict sample of 1,000 sources (est. 7.7 h).
- [ ] Optional: full pure Dijkstra on Wiki Conflict (`run_pure_large.py --stages full`); if it
      finishes, regenerate tables, update report sections 1/4.1/7/9 and the .docx.
- Submission: GitHub course repo + Word report + all code (decided 2026-10-13).
- Known measurement caveat: on small datasets, peak memory mostly reflects the 256 MiB chunk size in
  bench_worker (whole table fits in one chunk), not the algorithm.

## Implementation tiers

1. `pure`: from-scratch pure Python (heapq Dijkstra, triple-loop FW). Learning + validation only, small graphs.
2. `numpy`: from-scratch vectorized FW (one broadcast `np.minimum` per k).
3. `scipy`: `scipy.sparse.csgraph.dijkstra` / `floyd_warshall`. Used for the real benchmarks.
networkx is the correctness oracle in tests, not a benchmark contender.
Only compare timings within the same tier.

## Theory to test against

- n× Dijkstra (binary heap): O(n · m log n) time. Floyd-Warshall: Θ(n³) time, Θ(n²) memory.
- Sparse graphs (m ~ n): Dijkstra wins by a wide margin. Dense graphs (m ~ n²): n× Dijkstra becomes
  O(n³ log n), so FW should win. Predicted crossover near m ≈ n² / log n (constants matter; Phase 5 measures it).

## Benchmark methodology

- Timing: 1 warm-up run (discarded), then R repeats (default R = 5, fewer for long runs); report median
  and min. Use `time.perf_counter()`.
- Pin threads for fairness: `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1` set before numpy
  is imported (i.e. in the subprocess environment).
- Fixed random seeds for all random graphs (toy tests and density sweep); store the seed in results.
- Each results CSV row records: dataset, algorithm, tier, n, m, time stats, peak RSS, status
  (ok / timeout / infeasible / error). Store hardware (CPU, RAM, OS) and library versions alongside results.

## Report notes: algorithm variants (MUST appear in the final write-up)

Whenever an implementation is not textbook Dijkstra / textbook Floyd-Warshall, or is a variant, the
report must say so explicitly, with what differs and how it affects correctness or complexity.
Add to this list as soon as a new case is found.

- Our pure Dijkstra uses a binary heap with lazy deletion (stale entries skipped on pop) instead of
  decrease-key. Still O(m log n) per source; heap holds up to m + 1 entries.
- scipy `csgraph.dijkstra` uses a Fibonacci heap (O(m + n log n) per source), not a binary heap.
- scipy `csgraph.dijkstra` on negative weights only warns and re-processes nodes whose distance drops.
  That is a label-correcting method, NOT Dijkstra: no "settled is final" guarantee, and worst-case
  running time can be exponential. Our wrappers forbid negative weights, so every Dijkstra timing in
  the report is genuine Dijkstra.
- What each timing includes (apsp.bench_worker): "algo" time = the shortest-path computation only.
  Building the input (CSR matrix, adjacency list, FW starting table) is untimed. Exception: scipy
  `floyd_warshall` converts the sparse input to a dense n x n table inside the call, so its time
  includes that O(n^2) step (negligible next to n^3). Summarizing the output is reported separately
  as "total" time.
- Dijkstra is run STREAMING in every tier (batches of sources via `indices=` in scipy, one source at
  a time in pure), so it never holds the n x n table. Same algorithm; only the output handling differs.
- The "pure" tier is not uniformly interpreted: our pure Dijkstra's priority queue is `heapq`, which
  is implemented in C. This favors Dijkstra inside the pure tier (US Airports: pure FW/Dijkstra = 32x,
  scipy = 3.3x, step-count theory = 8.3x). Report the ratio per tier, never across tiers.
- scipy `floyd_warshall` evidently also skips the inner loop when i cannot reach k (measured: on
  random graphs with n = 1,000 it takes 0.005 s at 0.1% density vs ~0.46 s at >= 2%; a strict triple
  loop would take the same time). So FW time is ~n x (reachable i-k pairs), bounded by n^3.
  Our numpy FW has no such skip.
- Our pure FW skips the inner j loop when dist[i][k] is inf (same result, fewer operations on sparse
  reachability). Still Theta(n^3) in the worst case.
- Unit-weight graphs (Wiki Conflict under D2, Slashdot under D4): BFS would be the optimal single-source algorithm there.
  We deliberately time genuine Dijkstra anyway, to keep the comparison with FW like-for-like.
- Undirected graphs are stored as two one-way edges per pair; m in complexity formulas = one-way count.
- If Johnson's algorithm is ever used (negative edges, no negative cycles), it is Bellman-Ford +
  reweighting + n x Dijkstra: a variant, not textbook Dijkstra.
- Our numpy FW is the textbook algorithm vectorized: the k loop stays in Python, the i/j loops become
  one broadcast per k. Same Theta(n^3) work; peak memory ~2 n^2 (table + one temporary per sweep).

## Open decisions (must be answered before Phase 2 preprocessing)

Decided items are logged in `docs/decisions.md` (with a plain-language explanation for the report).

- [x] Wiki Conflict: hops (all weights 1), one undirected edge per editor pair, isolated ids dropped
      (n = 116,836). D2, D2b, D3 in docs/decisions.md.
- [x] Slashdot Zoo: friends only, hops, direction kept; users without friend tags dropped
      (n = 69,995). 4,497 mutual-foe pairs = negative 2-cycles, so raw weights were unusable.
      D4, D4b in docs/decisions.md.
- [x] US Airports: distance = 1 / passengers; nodes = the 1,574 airports with routes (D1 in docs/decisions.md).
- [x] Adolescent Health: distance = 1 / weight (weights 1..6), same rule as D1; no nodes dropped (D5).
- [x] Advogato: distance = 1 / trust level; self-certifications and unlinked users dropped
      (n = 5,155). D6, D6b, D6c.
- [ ] Directed vs undirected treatment per dataset (keep native direction unless decided otherwise).
- [ ] Multi-edges (e.g. Wiki Conflict has repeated/timestamped edges): keep min, keep one, or aggregate?

## Layout

```
data/raw/            downloaded archives (gitignored)
data/processed/      distance graphs as .npz (gitignored; rebuild with scripts/preprocess_datasets.py)
data/SOURCES.md      download URLs + SHA-256 of every raw file
docs/decisions.md    modeling decision log (what, why, alternatives, consequences, plain-language)
src/apsp/            package code (algorithms, loaders, characteristics, bench)
tests/               pytest correctness tests
scripts/             runnable entry points
notebooks/           exploration only; anything reported must be reproducible from scripts/
results/             CSV outputs, figures
requirements.txt     minimum versions (what we ask for)
requirements-lock.txt  exact installed versions (what we actually ran; from `pip freeze`)
```

## Known pitfalls (check these whenever relevant)

- Dijkstra requires nonnegative weights. Slashdot Zoo and Wiki Conflict are signed. FW tolerates negative
  edges but not negative cycles. One negative undirected edge is already a negative cycle.
- Some weights measure strength, not distance (airport traffic, Advogato trust). Raw values as distances
  invert the meaning; transforms such as 1/w or -log w must be a deliberate, documented choice.
- scipy COO → CSR conversion SUMS duplicate entries. Multi-edges must be deduplicated (e.g. keep min)
  before building the sparse matrix.
- Zero weights (verified on scipy 1.17.1, pinned by tests/test_scipy_tier.py): an explicit 0 stored in
  a sparse matrix IS an edge, but `eliminate_zeros()` and sparse arithmetic (e.g. `g + g`) silently
  drop it, and in a DENSE matrix 0 means "no edge". Always build via `apsp.scipy_tier.edges_to_csr`.
- `csgraph.dijkstra` only WARNS on negative weights and silently switches to re-processing nodes
  (correct without negative cycles, but no longer O(m log n) Dijkstra). Our wrappers reject them.
- All-pairs output is n² no matter which algorithm. For large n, Dijkstra must stream per-source results
  (aggregate or write to disk) instead of holding the full matrix.
- Unreachable pairs are `inf`. Keep that in mind when computing averages.
- Measure peak memory per run in a fresh subprocess (peak RSS), not just with tracemalloc, because C
  extensions allocate outside Python's tracker.
- `resource.getrusage(...).ru_maxrss` is in BYTES on macOS but KiB on Linux. Normalize by platform.
  psutil does not expose peak RSS on macOS; use it for total RAM (`psutil.virtual_memory().total`) instead.
- Verified scale (processed): Slashdot n = 69,995 (n×n float64 = 36.5 GiB), Wiki Conflict n = 116,836
  (101.7 GiB). Benchmark machine has 24 GiB, so FW is infeasible on both and Dijkstra must stream
  (e.g. batches of sources via the `indices=` argument of `csgraph.dijkstra`).

## Commands

- This project lives in the course repo (see ../CLAUDE.md). Shared venv at the repo root:
  `source ../.venv/bin/activate`
- Install (from this folder): `pip install -r requirements.txt && pip install -e .`
- Tests (from this folder): `pytest -q`
