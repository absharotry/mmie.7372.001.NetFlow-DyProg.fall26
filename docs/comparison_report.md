# All-pairs shortest paths: n x Dijkstra vs Floyd-Warshall on five real networks

MMIE 7372, Network Flows. Computational study.

> **Status: draft (2026-10-13).** Items still open are listed in Section 8 and marked *pending*
> in the text.

## 1. Summary

We computed all-pairs shortest paths (APSP) on five real networks in two ways: by running
Dijkstra's algorithm once from every node ("n x Dijkstra") and by Floyd-Warshall (FW).

- **n x Dijkstra was faster on every dataset, in every implementation.** In the compiled
  (scipy) implementation, FW was 3.4x slower on US Airports, 5.1x on Adolescent Health and 16.7x on
  Advogato.
- **FW could not run on the two large networks** (Slashdot Zoo, n = 69,995; Wiki Conflict,
  n = 116,836). It must keep the full n x n distance table in memory: 36.5 GiB and 101.7 GiB,
  against 24 GiB of RAM. Even with enough memory, the measured speed of FW predicts 21.5 hours and
  about 4 days. n x Dijkstra finished them in 3.2 and 30.5 minutes using at most 1.2 GiB.
- **The gap widens with network size**, as the complexities predict: FW's Theta(n^3) work does not
  depend on the number of edges, while Dijkstra's work grows with n x m, and all five networks are
  sparse (density 0.008% to 1.1%).
- **Implementation matters as much as the algorithm for the size of the gap**, but not its
  direction: FW was 3.4x slower in scipy and 35x slower in pure Python on the same network.

## 2. Datasets and network characteristics

Raw data came from the sources named in the assignment (KONECT, Netzschleuder, Canvas). Download
URLs and SHA-256 checksums are in `data/SOURCES.md`. Each dataset needed decisions about what an
edge weight means as a distance; these are documented in `docs/decisions.md` (D1-D6) and summarized
here.

### 2.1 Raw data

| Dataset | Nodes | Edges (rows) | Directed | Weights |
|---|---|---|---|---|
| US Airports (2010) | 1,574 | 28,236 | yes | passengers per route (1 to 1,489,618) |
| Adolescent Health | 2,539 | 12,969 | yes | 1..6 = 1 + number of shared activities |
| Advogato | 6,541 | 51,127 | yes | trust level 0.6 / 0.8 / 1.0 |
| Slashdot Zoo | 79,120 | 515,397 | yes | +1 friend / -1 foe |
| Wiki Conflict | 118,100 | 2,917,785 | no | signed, +-ln(k) |

### 2.2 From weights to distances

- **Strength weights** (passengers, shared activities, trust): bigger means closer, so
  **distance = 1 / weight** (Opsahl, Agneessens and Skvoretz, 2010).
- **Signed weights** cannot be distances. Both signed networks contain negative cycles (Slashdot:
  4,497 pairs of users who mark each other as foes; Wiki Conflict: every negative edge, because the
  network is undirected), so shortest paths are undefined for *any* algorithm. Slashdot Zoo keeps
  friend edges only; Wiki Conflict keeps every interacting pair. Both use **hop counts**.
- Nodes with no links, self-loops and repeated edges are removed; none of them can change a
  shortest path.

### 2.3 Networks as used in the benchmark

| Dataset | n | m (one-way edges) | Density m / (n(n-1)) | Mean out-degree m/n | Max degree (out / in) | Reciprocity | Reachable ordered pairs | Distance |
|---|---|---|---|---|---|---|---|---|
| US Airports | 1,574 | 28,236 | 1.14% | 17.9 | 302 / 294 | 78% | 89.3% | 1 / passengers |
| Adolescent Health | 2,539 | 12,969 | 0.20% | 5.1 | 10 / 27 | 39% | 84.9% | 1 / weight |
| Advogato | 5,155 | 47,135 | 0.18% | 9.1 | 785 / 721 | 33% | 60.9% | 1 / trust level |
| Slashdot Zoo | 69,995 | 392,179 | 0.008% | 5.6 | 426 / 2,498 | 21% | 36.3% | hops (friend edges) |
| Wiki Conflict | 116,836 | 4,055,742 | 0.030% | 34.7 | 20,153 (undirected) | (undirected) | 93.8% | hops |

Wiki Conflict is undirected; each of its 2,027,871 editor pairs is stored as two one-way edges,
which is what the algorithms scan.

**Structure worth noting.** All five networks are very sparse. US Airports, Advogato, Slashdot and
Wiki Conflict have heavy-tailed degree distributions (a few hubs with hundreds to tens of thousands
of links). Adolescent Health has no hubs, because the survey limited each student to 10 friends.
Slashdot has low reachability: 41% of its users never tagged anyone as a friend, so no path starts
from them.

## 3. Implementations and method

### 3.1 Implementations

| Version | n x Dijkstra | Floyd-Warshall |
|---|---|---|
| **pure** (our code, plain Python) | binary heap (`heapq`) with lazy deletion | textbook triple loop, k outermost |
| **numpy** (our code, vectorized) | (none: Dijkstra is sequential and does not vectorize) | k loop in Python; each sweep is one broadcast `np.minimum` over the whole table |
| **scipy** (`scipy.sparse.csgraph`, compiled) | `dijkstra` (Fibonacci heap) | `floyd_warshall` |

All versions were tested against networkx (Bellman-Ford) on a hand-checked graph and on random
graphs with zero weights, self-loops, multi-edges, negative edges and negative cycles (397 tests).

**Algorithm variants (stated explicitly, as they affect complexity or fairness):**
- Our pure Dijkstra uses lazy deletion instead of decrease-key: still O(m log n) per source.
- scipy's Dijkstra uses a Fibonacci heap: O(m + n log n) per source.
- scipy's Dijkstra only *warns* on negative weights and then re-processes nodes, which is no longer
  Dijkstra's algorithm. Our wrappers reject negative weights, so every Dijkstra timing here is
  genuine Dijkstra. (No dataset as used has negative weights.)
- On the hop-count networks (Slashdot, Wiki Conflict), breadth-first search would be the optimal
  single-source method. We time Dijkstra anyway, to compare like with like.
- The pure tier is not purely interpreted: Python's `heapq` is written in C, which favors Dijkstra
  within that tier.
- Our pure FW skips the inner loop when node i cannot reach node k (same result; still Theta(n^3) in
  the worst case).
- scipy's FW time includes converting the sparse input to a dense table (O(n^2), negligible next to
  n^3).

### 3.2 Measurement

- One measurement per **fresh Python process**, so peak memory belongs to that run alone.
- **Time = the shortest-path computation only.** Loading data and building the input are not timed.
- Short runs (< 10 s): one warm-up run, then **median of 5**. Longer runs: a single run.
- **Single thread** for every library.
- Dijkstra is run **streaming**: a batch of sources is solved, summarized and discarded, so the
  n x n table is never stored. Every run produces the same summary (number of reachable pairs, mean
  and maximum distance), which is how all versions are cross-checked at full scale.
- **Feasibility pre-check:** a run is not started if its estimated memory exceeds 60% of RAM. FW
  needs n^2 cells: 8 bytes each (scipy), 16 (numpy: table plus one temporary per sweep), up to 32
  (pure Python objects).
- Machine: Apple M2, 24 GiB RAM, macOS 26.7.1; Python 3.11.8, numpy 2.4.6, scipy 1.17.1.

## 4. Results

### 4.1 Running time

| Dataset | n | m | scipy Dijkstra | scipy FW | numpy FW | pure Dijkstra | pure FW |
|---|---|---|---|---|---|---|---|
| US Airports | 1,574 | 28,236 | 0.37 s | 1.25 s | 3.11 s | 2.13 s | 74 s |
| Adolescent Health | 2,539 | 12,969 | 0.70 s | 3.54 s | 24 s | 2.95 s | 3.3 min |
| Advogato | 5,155 | 47,135 | 1.85 s | 31 s | 3.7 min | 10.4 s | 29.3 min |
| Slashdot Zoo | 69,995 | 392,179 | **3.2 min** | infeasible | infeasible | *pending* | infeasible |
| Wiki Conflict | 116,836 | 4,055,742 | **30.5 min** | infeasible | infeasible | *pending* | infeasible |

![Time vs network size](../results/fig_time_vs_n.png)

*Figure 1. Algorithm time against n (both axes logarithmic). Blue: n x Dijkstra; orange:
Floyd-Warshall. Hollow circles: predicted scipy FW times for the two networks where FW does not fit
in memory.*

### 4.2 How many times slower Floyd-Warshall is

| Dataset | Theory n^3 / (n m log2 n) | scipy | pure Python |
|---|---|---|---|
| US Airports | 8.3x | 3.4x | 35x |
| Adolescent Health | 44x | 5.1x | 66x |
| Advogato | 46x | 16.7x | 169x |

![Ratio vs network size](../results/fig_ratio_vs_n.png)

*Figure 2. FW time divided by Dijkstra time. Above 1 means Dijkstra is faster. The step-count
theory is shown for reference.*

### 4.3 Correctness

On each of the three small networks, all five versions found exactly the same number of reachable
pairs (2,209,653; 5,473,916; 16,177,614), and their mean distances agree to within 2e-15 (floating
point rounding). On the large networks, scipy Dijkstra found 1,777,768,126 and 12,796,704,262
reachable pairs, matching the reachable fractions computed independently from the network structure
(36.3% and 93.8%).

### 4.4 Memory

| Dataset | FW table (n^2 x 8 bytes) | Peak memory, scipy Dijkstra | Peak memory, pure Dijkstra |
|---|---|---|---|
| Advogato | 203 MiB | 440 MiB | 92 MiB |
| Slashdot Zoo | **36.5 GiB** (not run) | 801 MiB | *pending* |
| Wiki Conflict | **101.7 GiB** (not run) | 1,192 MiB | *pending* |

Pure Dijkstra, which handles one source at a time, never rose above the memory used to hold the
network itself. On the small networks, the scipy figures mostly reflect our 256 MiB batch size (the
whole n x n table fits in one batch there), so they do not separate the two algorithms. The decisive
memory evidence is the large networks. The full per-run table is in `results/report_tables.md`
(Table 3).

## 5. Runs that could not complete, explained by complexity

| Dataset | Version | Memory needed | Available (60% of 24 GiB) | Predicted time if it fitted |
|---|---|---|---|---|
| Slashdot Zoo | scipy FW | 36.5 GiB | 14.4 GiB | 21.5 h |
| Wiki Conflict | scipy FW | 101.7 GiB | 14.4 GiB | ~4 days |

numpy FW (twice the memory) and pure FW (up to four times) are infeasible for the same reason.

**Why: memory.** FW works on the full n x n table. Each of its n sweeps reads and may update every
cell, so the whole table must stay in memory for the entire run: Theta(n^2) space, independent of
how many edges the network has. For n = 116,836 that is 13.65 billion cells, or 101.7 GiB at 8 bytes
each. Keeping the table on disk does not help: n sweeps over 36.5 GiB (Slashdot) would mean roughly
70,000 full passes, about 2.5 petabytes of disk traffic.

**Why: time.** FW performs exactly n^3 relaxations whatever the density: 3.4 x 10^14 for Slashdot and
1.6 x 10^15 for Wiki Conflict. At the rate measured on Advogato (0.23 ns per relaxation in scipy),
that is 21.5 hours and about 4 days. This model is reliable: calibrated on Advogato, it predicted
the other two FW timings to within 0.96x-1.41x (Table 5 in `results/report_tables.md`).

**Why n x Dijkstra still works.** Each single-source run needs only the network plus one row of
distances: O(n + m) memory. Rows can be summarized and discarded as they are produced, so the
n x n table never has to exist. Its time, n x O(m log n), stays small because m is small.

## 6. Discussion

### (a) Performance of each algorithm across the five datasets

n x Dijkstra was the faster method on every dataset and in every implementation where both could
run. Floyd-Warshall's disadvantage grew from 3.4x (US Airports) to 16.7x (Advogato) in scipy, and
from 35x to 169x in pure Python. On the two large networks Floyd-Warshall could not run at all,
while n x Dijkstra finished in minutes.

The measured gaps are smaller than the step-count theory in scipy (3.4x measured vs 8.3x predicted
on US Airports) and larger in pure Python (35x). The reason is the cost of a single step. An FW step
("add, compare, maybe overwrite") is about as cheap as an operation can be, and it walks through
memory in order, so compiled FW does better than its step count suggests. In pure Python, every FW
step goes through the interpreter, while Dijkstra's priority-queue work runs in C (`heapq`). The
complexity predicts the *winner* correctly every time; the *size* of the win depends on the
implementation.

### (b) How performance changes with network size and density

- **Floyd-Warshall depends on n only.** Its time followed n^3 closely: calibrated on one dataset, n^3
  predicted the others to within a factor of 1.5 for scipy and pure Python (2 for numpy), even
  though their densities differ about sixfold.
  Doubling n multiplies FW's time by about 8. Memory grows as n^2.
- **n x Dijkstra depends on n and m.** It ran 116,836 Dijkstra searches over 4 million edges in
  30.5 minutes. Its times follow n x m x log n less closely (0.4x-3x of the prediction), for two
  reasons. First, a search only explores what it can reach: on Slashdot only 36% of ordered pairs are
  connected, so many searches stop early, and the run was faster than predicted. Second, log n is a
  worst-case bound on heap operations.
- **Density.** Dijkstra's cost grows with density, FW's does not. So density shrinks Dijkstra's
  advantage. US Airports, the densest network (1.1%), shows the smallest ratio (3.4x). However, in
  these five networks size and density vary together (the largest networks are also the sparsest),
  so the real data cannot separate the two effects. *Pending:* a controlled experiment on random
  networks with fixed n and increasing density, to measure where FW starts to win.

### (c) Which network structures favor which algorithm

**n x Dijkstra is better for:**
- **Sparse networks** (m much smaller than n^2), which includes all five studied here and most real
  networks. Its work scales with m, while FW pays n^3 regardless.
- **Large networks.** FW's n^2 memory alone rules it out beyond about n = 44,000 on a 24 GiB
  machine (where n^2 x 8 bytes reaches 60% of RAM). Dijkstra's memory is O(n + m).
- **Networks with limited reachability** (many sources reach only part of the network, as in
  Slashdot). Dijkstra's searches stop early; FW still performs all n^3 checks.
- When only some sources are needed: Dijkstra can be run for just those.

**Floyd-Warshall is better for:**
- **Dense networks** (m close to n^2). n x Dijkstra then costs O(n^3 log n) with a binary heap
  (O(n^3) with a Fibonacci heap), no better than FW, and FW's simple, memory-friendly inner loop wins
  on constants. Step-count theory places the crossover near m = n^2 / log2 n, about 9% density for
  n = 1,574. Our densest network (1.1%) is far below that. *Pending:* measuring the crossover.
- **Small networks**, where the n x n table fits easily and simplicity matters more.
- **Negative edge weights without negative cycles.** FW handles them directly; Dijkstra does not
  (Johnson's algorithm, Bellman-Ford plus reweighting plus n x Dijkstra, is the alternative).
  Negative *cycles* defeat every method; FW at least detects them.

**Neither is ideal for unweighted networks** (hop counts, as in Slashdot and Wiki Conflict): n x BFS
solves them in O(n(n + m)) time without a priority queue.

## 7. Reproducing the results

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
python scripts/preprocess_datasets.py   # raw data -> distance graphs (data/raw must be filled; see data/SOURCES.md)
python scripts/describe_dataset.py      # network characteristics and distribution figures
python scripts/run_benchmarks.py        # the benchmark (about 1.5 hours)
python scripts/make_report.py           # tables and figures for this report
pytest -q                               # 397 correctness tests
```

Scripts and modules (deliverables):
- `src/apsp/pure.py`: our Dijkstra and Floyd-Warshall in plain Python.
- `src/apsp/vectorized.py`: our numpy Floyd-Warshall.
- `src/apsp/scipy_tier.py`: guarded scipy wrappers.
- `src/apsp/loaders.py`, `src/apsp/preprocess.py`: dataset loading and the decisions in `docs/decisions.md`.
- `src/apsp/characteristics.py`: network characteristics.
- `src/apsp/bench.py`, `src/apsp/bench_worker.py`: the benchmark harness.
- `scripts/`: the entry points listed above.
- `tests/`: correctness tests.

## 8. Pending items

1. **Our own n x Dijkstra on Slashdot Zoo and Wiki Conflict** (pure Python, streaming). Estimated
   10-20 minutes and about 7 hours. Decision pending: full run, or a sample of sources extrapolated
   and labelled as an estimate.
2. **Density experiment** (fixed n, increasing density) to measure the crossover between the two
   algorithms, for discussion points (b) and (c).
3. **Submission format** (Markdown, PDF or Word) for the discussion.
