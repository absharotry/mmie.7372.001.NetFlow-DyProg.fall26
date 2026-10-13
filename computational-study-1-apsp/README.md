# Computational Study 1: all-pairs shortest paths

**n x Dijkstra vs Floyd-Warshall on five real-world networks** (MMIE 7372, Network Flows, Fall 2026).

- Assignment: [docs/assignment.md](docs/assignment.md)
- Report: [docs/comparison_report.md](docs/comparison_report.md) (Word version: `docs/comparison_report.docx`)
- Modeling decisions (how each dataset's weights became distances): [docs/decisions.md](docs/decisions.md)
- Data sources and checksums: [data/SOURCES.md](data/SOURCES.md)

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
python scripts/make_report.py           # report tables and figures
pytest -q                               # correctness tests
```
