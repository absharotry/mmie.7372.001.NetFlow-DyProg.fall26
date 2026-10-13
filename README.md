# mmie.7372.001.NetFlow-DyProg.fall26

Network Flows and Dynamic Programming (MMIE 7372.001, Fall 2026): course projects.

| Project | Topic | Report |
|---|---|---|
| [Computational Study 1](computational-study-1-apsp/) | All-pairs shortest paths: running Dijkstra from every node vs Floyd-Warshall, on five real networks | [report](computational-study-1-apsp/docs/comparison_report.md) |

## Setup (shared by all projects)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r computational-study-1-apsp/requirements.txt
pip install -e computational-study-1-apsp
```

Each project's README explains how to get its data and run it.
