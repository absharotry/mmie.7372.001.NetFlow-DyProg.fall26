## Machine

Apple M2, 24 GiB RAM, macOS-26.7.1-arm64-arm-64bit; Python 3.11.8, numpy 2.4.6, scipy 1.17.1. Single thread.

## Table 1. Algorithm time (median), by dataset and version

| Dataset | n | m | scipy Dijkstra | scipy FW | numpy FW | pure Dijkstra | pure FW |
|---|---|---|---|---|---|---|---|
| US Airports | 1,574 | 28,236 | 372 ms | 1.25 s | 3.11 s | 2.13 s | 74.20 s (1 run) |
| Adolescent Health | 2,539 | 12,969 | 695 ms | 3.54 s | 23.94 s (1 run) | 2.95 s | 3.3 min (1 run) |
| Advogato | 5,155 | 47,135 | 1.85 s | 30.96 s (1 run) | 3.7 min (1 run) | 10.41 s (1 run) | 29.3 min (1 run) |
| Slashdot Zoo | 69,995 | 392,179 | 3.2 min (1 run) | **infeasible** | not run | not run | not run |
| Wiki Conflict | 116,836 | 4,055,742 | 30.5 min (1 run) | **infeasible** | not run | not run | not run |

## Table 2. Floyd-Warshall time / Dijkstra time

| Dataset | Theory n^3 / (n m log2 n) | scipy (measured) | pure (measured) |
|---|---|---|---|
| US Airports | 8.3x | 3.4x | 34.8x |
| Adolescent Health | 43.9x | 5.1x | 66.2x |
| Advogato | 45.7x | 16.7x | 169.0x |
| Slashdot Zoo | 776.2x | - | - |
| Wiki Conflict | 199.9x | - | - |

## Table 3. Peak memory (MiB): measured, and the n x n table it implies

| Dataset | Version | Peak RSS | Baseline (before algorithm) | Peak - baseline | n^2 x 8 bytes |
|---|---|---|---|---|---|
| US Airports | scipy FW | 131 | 89 | 42 | 19 |
| US Airports | scipy Dijkstra | 131 | 88 | 43 | 19 |
| US Airports | pure FW | 163 | 82 | 82 | 19 |
| US Airports | pure Dijkstra | 87 | 86 | 0 | 19 |
| US Airports | numpy FW | 152 | 80 | 72 | 19 |
| Adolescent Health | scipy FW | 200 | 84 | 116 | 49 |
| Adolescent Health | numpy FW | 239 | 81 | 157 | 49 |
| Adolescent Health | pure Dijkstra | 84 | 84 | 1 | 49 |
| Adolescent Health | pure FW | 300 | 82 | 218 | 49 |
| Adolescent Health | scipy Dijkstra | 188 | 85 | 104 | 49 |
| Advogato | numpy FW | 696 | 82 | 614 | 203 |
| Advogato | scipy FW | 439 | 93 | 346 | 203 |
| Advogato | scipy Dijkstra | 440 | 93 | 347 | 203 |
| Advogato | pure FW | 764 | 82 | 682 | 203 |
| Advogato | pure Dijkstra | 92 | 92 | 0 | 203 |
| Slashdot Zoo | scipy Dijkstra | 801 | 193 | 609 | 37,379 |
| Wiki Conflict | scipy Dijkstra | 1,192 | 1,192 | 0 | 104,146 |

## Table 4. Runs not performed

| Dataset | Version | Status | Reason | Predicted time if memory allowed |
|---|---|---|---|---|
| Slashdot Zoo | scipy FW | infeasible | needs ~36.5 GiB, budget 14.4 GiB (60% of 24 GiB RAM) | 21.5 h |
| Wiki Conflict | scipy FW | infeasible | needs ~101.7 GiB, budget 14.4 GiB (60% of 24 GiB RAM) | 4 days |

## Table 5. Step-count model: calibrated on Advogato, checked on the others

| Version | ns per step | Dataset | Predicted | Measured | Measured / predicted |
|---|---|---|---|---|---|
| scipy Dijkstra | 0.617 | US Airports | 291 ms | 372 ms | 1.28 |
| scipy Dijkstra | 0.617 | Adolescent Health | 230 ms | 695 ms | 3.02 |
| scipy Dijkstra | 0.617 | Advogato | 1.85 s | 1.85 s | 1.00 |
| scipy Dijkstra | 0.617 | Slashdot Zoo | 4.5 min | 3.2 min | 0.69 |
| scipy Dijkstra | 0.617 | Wiki Conflict | 82.1 min | 30.5 min | 0.37 |
| scipy FW | 0.226 | US Airports | 881 ms | 1.25 s | 1.41 |
| scipy FW | 0.226 | Adolescent Health | 3.70 s | 3.54 s | 0.96 |
| scipy FW | 0.226 | Advogato | 30.96 s | 30.96 s | 1.00 |
| scipy FW | 0.226 | Slashdot Zoo | 21.5 h |  |  |
| scipy FW | 0.226 | Wiki Conflict | 4 days |  |  |
| numpy FW | 1.61 | US Airports | 6.28 s | 3.11 s | 0.50 |
| numpy FW | 1.61 | Adolescent Health | 26.36 s | 23.94 s | 0.91 |
| numpy FW | 1.61 | Advogato | 3.7 min | 3.7 min | 1.00 |
| pure Dijkstra | 3.47 | US Airports | 1.64 s | 2.13 s | 1.30 |
| pure Dijkstra | 3.47 | Adolescent Health | 1.29 s | 2.95 s | 2.28 |
| pure Dijkstra | 3.47 | Advogato | 10.41 s | 10.41 s | 1.00 |
| pure FW | 12.8 | US Airports | 50.08 s | 74.20 s | 1.48 |
| pure FW | 12.8 | Adolescent Health | 3.5 min | 3.3 min | 0.93 |
| pure FW | 12.8 | Advogato | 29.3 min | 29.3 min | 1.00 |

## Table 6. Correctness: every version must agree

| Dataset | Versions run | Reachable pairs (all equal?) | Mean distance (max relative spread) | Max distance |
|---|---|---|---|---|
| US Airports | 5 | 2,209,653 (yes) | 0.133396 (1.5e-15) | 4.07155 |
| Adolescent Health | 5 | 5,473,916 (yes) | 2.35853 (5.6e-16) | 8.6 |
| Advogato | 5 | 16,177,614 (yes) | 4.70593 (7.5e-16) | 14.3333 |
| Slashdot Zoo | 1 | 1,777,768,126 (yes) | 4.8811 (0.0e+00) | 16 |
| Wiki Conflict | 1 | 12,796,704,262 (yes) | 3.32244 (0.0e+00) | 10 |
