# Computational Study 1: all-pairs shortest paths

**n x Dijkstra vs Floyd-Warshall on five real-world networks** (MMIE 7372, Network Flows, Fall 2026).

Author: Abhimanyu Sharotry

- Assignment: [docs/assignment.md](docs/assignment.md)
- Report: [docs/comparison_report.md](docs/comparison_report.md), Word version: [docs/comparison_report.docx](docs/comparison_report.docx)
- Modeling decisions (how each dataset's weights became distances): [docs/decisions.md](docs/decisions.md)
- Data sources and checksums: [data/SOURCES.md](data/SOURCES.md)

## Key findings

- n x Dijkstra beat Floyd-Warshall on all five networks, in every implementation.
- Floyd-Warshall cannot run on Slashdot Zoo and Wiki Conflict: its n x n table needs 36.5 / 101.7 GiB.
- On random networks with fixed n, compiled Floyd-Warshall only wins above ~21-27% density;
  the real networks are at 0.008-1.1%.

## What is implemented

| Version | n x Dijkstra | Floyd-Warshall | Code |
|---|---|---|---|
| pure Python (our implementation) | binary heap (`heapq`) | triple loop | `src/apsp/pure.py` |
| numpy (our implementation) | n/a | one vectorized sweep per k | `src/apsp/vectorized.py` |
| scipy (`scipy.sparse.csgraph`) | Fibonacci heap | dense | `src/apsp/scipy_tier.py` |

## Layout

```
src/apsp/        algorithms, dataset loaders, preprocessing, characteristics, benchmark harness
tests/           correctness tests (pytest), networkx as the reference
scripts/         entry points (see "Run" below)
docs/            assignment, decisions, report
results/         benchmark CSV and log, characteristics, tables, figures
data/raw/        downloaded datasets (not in git; see data/SOURCES.md)
data/processed/  distance graphs built by scripts/preprocess_datasets.py (not in git)
```

## Setup

From the repository root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r computational-study-1-apsp/requirements.txt
pip install -e computational-study-1-apsp
```

`requirements-lock.txt` lists the exact versions used for the reported results.

## Data

Raw files are not committed. Download them into `data/raw/<folder>/` as listed in
[data/SOURCES.md](data/SOURCES.md), which also gives SHA-256 checksums to verify them.

## Run (from this folder)

```bash
python scripts/preprocess_datasets.py   # raw data -> distance graphs (data/processed/)
python scripts/describe_dataset.py      # network characteristics + distribution figures
python scripts/run_benchmarks.py        # benchmark on the five datasets (about 1.5 h)
python scripts/run_pure_large.py --stages slashdot,sample,full --deadline 23:59   # our Dijkstra on the two large networks (~8.5 h)
python scripts/run_density_sweep.py     # density experiment on random networks (about 10 min)
python scripts/make_report.py           # report tables and figures
python scripts/build_word_report.py     # docs/comparison_report.docx (needs pandoc)
pytest -q                               # correctness tests
```
