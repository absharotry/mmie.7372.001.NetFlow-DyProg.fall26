# Data sources

Raw files live in `data/raw/` (gitignored). This file records where each came from and its SHA-256,
so anyone can re-download and verify they have the exact same data.

## US Airports (`data/raw/opsahl-usairport/`)

| File | Source | SHA-256 |
|---|---|---|
| `out.opsahl-usairport` | KONECT, http://konect.cc/networks/opsahl-usairport (supplied by the user) | `0634f31f431b83acf5c57bc2bb6c0c3040392828bd24ddb4bf88c2b0288502a7` |
| `README.opsahl-usairport` | KONECT (same archive) | `aa4ad6b05a2bb5fa73e2653509028ef0df1f67c2761d17f6e3eba4ae1759f138` |
| `meta.opsahl-usairport` | KONECT (same archive) | `f84f5d6ed67c3c7c70068a0e14c6bcb48be6a0c0eb4b9efe786d72b7e21678f1` |
| `USairport_2010.txt` | http://opsahl.co.uk/tnet/datasets/USairport_2010.txt (downloaded 2026-10-12) | `dba90f87bd64aa22c3ed57c66afb885fabd54b6dd404c0f2671fd20f20fb9593` |
| `USairport_2010_codes.txt` | http://opsahl.co.uk/tnet/datasets/USairport_2010_codes.txt (downloaded 2026-10-12) | `d359688eb7cc3215cb96b251292f844d2e1b56da0d1262ae61c754fda4cfe869` |

Notes:
- **Loaded from:** the original Opsahl files (`apsp.loaders.load_usairport`), because they come with
  airport codes.
- **Same network as KONECT:** after renumbering ids in order of first appearance (`compact_ids`),
  the original file is identical row for row to KONECT's `out.opsahl-usairport` (verified 2026-10-12).
- **Weight = passengers.** The weight is the number of passengers on the route in 2010 (BTS T-100
  table, per http://toreopsahl.com/datasets/). KONECT's README says "number of flights", which is
  incorrect. The original source summed duplicate routes and removed cargo-only (0-passenger) routes
  and self-loops.
- **Node count:** the codes file lists 1,858 airports, but only 1,574 appear in the network. The
  other 284 had no passenger routes in 2010 and are not nodes.

## Wiki Conflict (`data/raw/wikiconflict/`)

| File | Source | SHA-256 |
|---|---|---|
| `out.wikiconflict` | KONECT, http://konect.cc/networks/wikiconflict (supplied by the user) | `1232385ecae796ca800a1a0ba1d96f3e7ff1582c48f8ada1379cda943a7c6d3e` |
| `README.wikiconflict` | KONECT (same archive) | `3d79b0256e267fe5d70c03e7daef15895819d6867c2804c1efa054bfbfe74eae` |
| `meta.wikiconflict` | KONECT (same archive) | `3af20b374c90665a48985cb92f4fee9e8ba5425d0c091d26fab8e7ae79897402` |

Notes (verified 2026-10-12):
- **Format:** `% sym multisigned`: undirected, multi-edges, signed. Columns: user, user, weight,
  Unix timestamp (2001-08-27 .. 2009-03-24). Every row has u < v, so each pair is stored one way only.
- **Edge count:** the `%` header says 2,985,759 edges, but the file has **2,917,785** rows, which
  matches the KONECT website and Netzschleuder (https://networks.skewed.de/net/wikiconflict).
  The header is stale.
- **Distinct pairs:** we count 2,027,871 distinct pairs; KONECT reports 2,014,062 "unique edges".
  The difference is not explained.
- **Nodes:** ids run 1..118,100, but only 116,836 appear in any edge (1,264 have no edges).
- **Weights:** sign = agreement (+) or disagreement/revert (-) (README, Netzschleuder). Every
  magnitude is exactly ln(k) for a whole number k (k up to 257,935). What k counts is not documented
  on KONECT or Netzschleuder. Original study: Brandes, Kenis, Lerner, van Raaij (2009), "Network
  Analysis of Collaboration Structure in Wikipedia", WWW 2009, pp. 731-740.
- **Zero weights:** 0.1% of rows have w = 0 (k = 1, ln 1 = 0), so their sign is lost.

## Slashdot Zoo (`data/raw/slashdot_zoo/`)

The user pointed to graph-tool's `gt.collection.ns["slashdot_zoo"]`. That call downloads from
Netzschleuder, so we downloaded the same network directly from Netzschleuder as CSV instead of
installing graph-tool (which is not pip-installable). Same data, pure-pip environment.

| File | Source | SHA-256 |
|---|---|---|
| `slashdot_zoo.csv.zip` | https://networks.skewed.de/net/slashdot_zoo/files/slashdot_zoo.csv.zip (downloaded 2026-10-12) | `13a1bb7385b481048d09be61f6fdec3ae65617e57ecff26011f02ed6c18afa28` |
| `edges.csv` (in zip) | source, target, weight | `96e70022d94834ce3384e092a975797ec58ad8d496b62823f2b17af4eb08fb64` |
| `nodes.csv` (in zip) | node index + drawing position only (no user names) | `563f6745fee47b024cbd0f5ee54991c988c3014956d33bd34337b62b4b9bd778` |
| `gprops.csv` (in zip) | metadata, incl. the KONECT README and meta | `95d8842e6948509996c497d6713a6e11b770589b731efe0903822c7c2f5858ae` |

Metadata: https://networks.skewed.de/api/net/slashdot_zoo. Original: KONECT slashdot-zoo;
J. Kunegis, A. Lommatzsch, C. Bauckhage (2009), "The Slashdot Zoo: Mining a Social Network with
Negative Edges", WWW 2009, pp. 741-750.

Notes (verified 2026-10-12):
- **Directed:** A -> B means "A marked B". Ids are already 0-based, 0..79,119.
- **Size:** 515,397 rows, matching Netzschleuder's num_edges. No self-loops, no duplicate rows.
- **Weights:** +1 = friend (392,179 rows), -1 = foe (123,218 rows).
- **Nodes:** 79,120 ids; 79,116 appear in an edge (4 have no edges).
- **Negative cycles:** 4,497 pairs of users mark each other as foes. Each is a negative 2-cycle
  (-1 + -1 = -2), so with raw weights as distances, shortest paths are undefined.

## Adolescent Health (`data/raw/health/`)

| File | Source | SHA-256 |
|---|---|---|
| `out.moreno_health_health` | KONECT moreno_health, http://konect.uni-koblenz.de/networks/moreno_health (supplied by the user; file date 2019-09-23) | `3452e794d6b92ace0d5484d1aa89c12d1566753a1838fc8d0943970b378a6105` |
| `README.moreno_health` | KONECT (same archive) | `7b19b98b89e0847562de4bcea72bd35e9dbe396b881ad86f9789e10741518b55` |
| `meta.moreno_health_health` | KONECT (same archive) | `a8c72b1a576783f0246aab5783c60f2b08ef0542e80dc3b2c9dc23ac2f96f1ad` |

The folder also contains `.ipynb_checkpoints/` (two 2019 notebooks, Dijkstra and Floyd_Warshall).
They are not data and are not used by this project.

Original study: J. Moody (2001), "Peer influence groups: identifying dense clusters in large
networks", *Social Networks* 23(4), 261-283. Data: National Longitudinal Study of Adolescent Health
(Add Health), 1994/95 survey.

Notes (verified 2026-10-12):
- **Format:** `% asym posweighted`, header `% 12969 2539 2539`, which matches the file: 12,969 rows,
  2,539 nodes, every id used, no self-loops, no duplicate rows.
- **Directed:** u -> v means "student u named student v as a friend". Students could name up to
  5 female and 5 male friends, so out-degree is at most 10 (verified: max 10).
- **Weights 1..6:** 1 + the number of 5 shared activities (visited the friend's house, met after
  school, spent time last weekend, talked about a problem, talked on the phone), so 1 = named as a
  friend but no shared activity, 6 = all five. KONECT's README sentence on this is garbled ("a edge
  weight shows that there is no common activity at all", number missing). The 1..6 range and the
  5-activity design are described in a secondary source (arXiv:0912.0161); the exact "1 + count"
  mapping is our inference, consistent with both.
