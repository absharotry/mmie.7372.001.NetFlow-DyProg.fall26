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
