# Dataset sources

The 14 `elist*.txt` files were placed in this folder by the author on 2026-11-08. They are not
committed (see `../.gitignore`). **Still to record:** how they reached the author (Canvas page or URL).

## What the files are

The names, header layout and structure match the `elist` maximum-flow test set of the Zuse Institute
Berlin (`elib.zib.de/pub/mp-testdata/maxflow/`), described in an info file mirrored at
https://fpt.akt.tu-berlin.de/maxflow-data/RMF/info.txt. They are synthetic "grids-on-pipe" graphs
made with the RMFGEN generator (Goldfarb and Grigoriadis, 1988), and do not describe a real system.
The ZIB server could not be reached on 2026-11-08, so byte-identity with the originals is unconfirmed.

Per the info file, `d` files contain double edges (both (v,w) and (w,v)), the other files were made
from them by removing duplicate edges, and the edge lists may be read as directed or undirected.
The main study reads them as directed (author's decision). The 7 sparse files are also solved as
undirected in a separate supplement; the dense files are not.

Measured structure of the dense files. Each is a chain of frames, and each frame is an exact a × a
grid with two-way arcs of one large capacity U. Other arcs join neighbouring frames only, with small
varied capacities. s is a corner of the first frame and t a corner of the last. Max flow equals the
total forward capacity of the weakest gap between frames.

| File | Frames × grid | Forward arcs per node | Backward arcs per node | U | Largest cross capacity (approx.) | Max flow | Weakest gap |
|---|---|---|---|---|---|---|---|
| elist96d | 6 × 4×4 | 1 | 2 | 3.2001 | 0.2 | 1.3784 | frames 5→6 |
| elist160d | 10 × 4×4 | 2 | 1 | 480 | 15 | 211.8491 | frames 2→3 |
| elist200d | 8 × 5×5 | 1 | 3 | 5.0001 | 0.2 | 2.1353 | frames 3→4 |
| elist500d | 20 × 5×5 | 4 | 1 | 1500 | 15 | 702.1112 | frames 1→2 |
| elist640d | 10 × 8×8 | 8 | 10 | 1.2801 | 0.0025 | 0.8817 | frames 4→5 |
| elist960d | 60 × 4×4 | 5 | 2 | 800 | 10 | 335.1562 | frames 52→53 |

Measured structure of the sparse files. Every sparse arc also appears in the matching dense file.
Each node keeps either all of its dense out-arcs or none (22% to 37% of nodes keep them). Some
cross-frame arcs have their capacity raised to U. More than duplicates was removed: `elist96` has 187
arcs, while `elist96d` has 377 distinct node pairs. `elist1440` has no distinct dense companion, and
`elist1440d` has no two-way pairs, unlike every other `d` file.

## File format

Whitespace-separated ASCII with CRLF line endings and no newline after the last line.

| Position | Content |
|---|---|
| Line 1 | number of nodes n |
| Line 2 | number of arcs m |
| Line 3 | source node s (always 1) |
| Line 4 | sink node t (always n) |
| Remaining | one `tail head capacity` per arc |

Capacities mix formats and spacing (`3.200100e+00`, `3.20010`, `8.86000E-02`), so parse by splitting
on any whitespace. Every capacity has at most 4 decimal places.

## SHA-256 checksums (whole file)

| File | SHA-256 |
|---|---|
| elist96.txt | 624d8c3342d4b14d95a34fb50e4fe1c88c3309f37101c439a3eff4592d83a78a |
| elist96d.txt | cbd19d3d02306615eee73201991601d1272d062ea3fe229006b829644840a487 |
| elist160.txt | dbcabfed86a5e357825ff9ea5cad83ced02a48054500d4e84f947884706765ed |
| elist160d.txt | a9fa4eec7c556e00a71e0efe1c043c737aa90fbf3fb8f506f12ca7d9a3865195 |
| elist200.txt | 1f299b591c5da9e36f327dd06ff682a677c1422a0c8dd55606e40d0b0b8502d3 |
| elist200d.txt | 0cd01ec20631cbb68a34ff607c3c3e2c851ca7d0e0784ccef860cb3e98deaadc |
| elist500.txt | 76f238bd8325b8608d83cd5429aab9d1e661605352612967cc63e6d1210c0cba |
| elist500d.txt | 0429ea917efc43077cb24547cca552599455449a59ca2db09f17fe00b6f1e753 |
| elist640.txt | 55a8f00f51efe79d5b96f3ed52cbde71f8a361bd32259cb6b848558685937ffb |
| elist640d.txt | e54f4df6119435acc7a8bdc6e77cb43dd56f895b4f21e3fee48dc522e507af55 |
| elist960.txt | 9640ff0d927219ac83fedc00e7e7aa1a56a42b70071192d1e385509365a110c8 |
| elist960d.txt | b6b1238179e8811762a3dba9737a4847ebafca6056b424303349c6700a8ea9b6 |
| elist1440.txt | 48d9740b20049bfb25efb60a5eb19fe69aa604811fb54b6120a9dcb7e57863e7 |
| elist1440d.txt | 48d9740b20049bfb25efb60a5eb19fe69aa604811fb54b6120a9dcb7e57863e7 |

`elist1440.txt` and `elist1440d.txt` are byte-for-byte identical. See `../docs/plan_of_action.md`.
