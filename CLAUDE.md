# MMIE 7372.001 Network Flows and Dynamic Programming (Fall 2026): course repo

One repository for all course projects. Each project lives in its own folder with its own
README.md, CLAUDE.md, pyproject.toml and requirements. **When working on a project, read that
project's CLAUDE.md first.** It holds the working agreement, decisions and status.

## Projects

| Folder | Project | Status |
|---|---|---|
| `computational-study-1-apsp/` | Computational Study 1: all-pairs shortest paths, n x Dijkstra vs Floyd-Warshall | in progress |

## Conventions for every project

- Folder name: `<assignment>-<short-topic>`, e.g. `computational-study-2-<topic>`.
- Each project is self-contained: `pyproject.toml` (its own package under `src/`), `requirements.txt`
  (minimum versions) plus `requirements-lock.txt` (exact versions used), `tests/`, `scripts/`,
  `docs/` (assignment text, decisions, report), `results/`.
- Raw data is never committed: `<project>/data/raw/` is gitignored, and `<project>/data/SOURCES.md`
  records download URLs and SHA-256 checksums.
- One shared virtual environment at the repo root: `.venv/` (gitignored). Install a project with
  `pip install -r <project>/requirements.txt && pip install -e <project>`.
- Add each new project to the table above and to README.md.
