# Assignment (MMIE 7372, Network Flows): as given by the instructor

You have learned two different approaches for solving the all-pairs shortest path problem:

1. Run Dijkstra's algorithm (n) times, using each node as the source.
2. Use the Floyd-Warshall algorithm.

Implement both approaches and perform a computational study comparing their performance on the
following five real-world network datasets from the KONECT network collection:

- (a) US Airports: http://konect.cc/networks/opsahl-usairport/
- (b) Wikipedia Conflict: http://konect.cc/networks/wikiconflict/
- (c) Slashdot Zoo: https://networks.skewed.de/net/slashdot_zoo
- (d) Adolescent Health (see Canvas).
- (e) Advogato: https://networks.skewed.de/net/advogato

For each dataset, record relevant network characteristics, including the number of nodes and edges,
and compare the computational performance of the two algorithms.

Your discussion should address:

- the computational performance of each algorithm across the five datasets;
- how performance changes with network size and density; and
- under what types of network structures one algorithm performs better than the other.

If an algorithm cannot complete a dataset because of excessive computational time or memory
requirements, report this outcome and explain the reason based on the algorithm's computational
complexity. Please upload the discussion and scripts.
