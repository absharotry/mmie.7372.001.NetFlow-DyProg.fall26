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
