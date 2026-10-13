# APSP Benchmark: n× Dijkstra vs Floyd-Warshall

Course project (MMIE 7372, Network Flows). We compare all-pairs shortest paths computed by
(a) running Dijkstra once from every node and (b) Floyd-Warshall, on five real networks:
US Airports, Adolescent Health, Advogato, Slashdot Zoo, Wiki Conflict.

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
- [ ] 2. Load/preprocess datasets; record characteristics (n, m, density, degree stats, components, weighted/signed, reachable-pair fraction).
      Record source URL + SHA-256 checksum of every downloaded archive.
- [ ] 3. Benchmark harness: wall time, peak memory, timeout, feasibility pre-check (estimate n² memory, n³ ops before running)
- [ ] 4. Run datasets smallest → largest; report infeasible runs with complexity-based explanation
- [ ] 5. Synthetic density sweep (fixed n, vary density) to locate the crossover
- [ ] 6. Analysis + write-up

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
- Our pure FW skips the inner j loop when dist[i][k] is inf (same result, fewer operations on sparse
  reachability). Still Theta(n^3) in the worst case.
- Our numpy FW is the textbook algorithm vectorized: the k loop stays in Python, the i/j loops become
  one broadcast per k. Same Theta(n^3) work; peak memory ~2 n^2 (table + one temporary per sweep).

## Open decisions (must be answered before Phase 2 preprocessing)

- [ ] Signed graphs (Slashdot Zoo, Wiki Conflict): how to turn signs into distances? Options include
      ignoring weights (hop count), |w|, keeping only positive edges, or another documented choice.
- [ ] Strength-type weights (US Airports, Advogato, Adolescent Health): raw, 1/w, -log w, or unweighted?
- [ ] Directed vs undirected treatment per dataset (keep native direction unless decided otherwise).
- [ ] Multi-edges (e.g. Wiki Conflict has repeated/timestamped edges): keep min, keep one, or aggregate?

## Layout

```
data/raw/            downloaded archives (gitignored)
data/processed/      cleaned edge lists (gitignored)
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
- Expected scale (verify in Phase 2): Slashdot Zoo ~79k nodes, Wiki Conflict ~118k nodes. A dense n×n
  float64 matrix is then ~50–110 GB, so FW is infeasible there and Dijkstra must stream
  (e.g. batches of sources via the `indices=` argument of `csgraph.dijkstra`).

## Commands

- Activate env: `source .venv/bin/activate`
- Install: `pip install -r requirements.txt && pip freeze > requirements-lock.txt`
- Tests: `pytest -q`
