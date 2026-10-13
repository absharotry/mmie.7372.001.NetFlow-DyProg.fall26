# Modeling decisions

Every choice that changes what a "shortest path" means is recorded here: what we chose, why, the
alternatives, and the consequences. Each decision has a plain-language explanation for the report.

---

## D1. US Airports: distance = 1 / passengers (decided 2026-10-12)

### What we chose
Each route's weight is the number of passengers who flew it in 2010. We set the **distance** of a
route to **1 / passengers**. Nodes: the 1,574 airports that have at least one passenger route.
The 284 airports in the code list with no 2010 passenger routes are not included, which matches both
published versions of the network.

### Plain-language explanation
Shortest-path algorithms look for the route with the **smallest total cost**, like a navigation app
finding the quickest drive. Our data does not contain costs. It contains **passenger counts**, where
a *bigger* number means a *more important* connection. Used directly, the algorithm would hunt for
the emptiest, least-used routes, which is backwards.

So we flip the number: **cost = 1 / passengers**.

- A busy route with 1,000,000 passengers costs 1/1,000,000 = **0.000001** (very cheap).
- A route that carried 1 passenger all year costs 1/1 = **1** (very expensive).

Think of passenger traffic as the width of a road. A wide highway is cheap to travel, a dirt track is
expensive, and the "shortest" path is the one that sticks to the highways.

**A real example from the data:** Oakland (OAK) to Washington National (DCA) has a direct route, but
it carried just **1 passenger** in 2010, so its cost is 1. The algorithm instead picks
OAK → LAX → ORD → DCA. Each of those legs carried 374,091 to 1,081,616 passengers, and the total cost
is about 0.000005, roughly 200,000 times cheaper than the direct route. The answer is "the route the
traffic actually flows along", not "the fewest flights".

### Why this option
- It uses the passenger data. Counting every route as 1 (hops) would throw that data away.
- It is the standard transformation for "strength" weights in network science, used by the
  dataset's own author: T. Opsahl, F. Agneessens, J. Skvoretz (2010), "Node centrality in weighted
  networks: Generalizing degree and shortest paths", *Social Networks* 32(3).

### Alternatives considered
| Option | Meaning of "shortest" | Why not chosen |
|---|---|---|
| Hops (every route = 1) | fewest flights | discards all passenger information |
| Raw passengers | least-used routes | meaning is inverted |
| 1 / passengers | busiest routes | **chosen** |

### Consequences (must be discussed in the report)
- **Hubs dominate.** For 24,523 of the 28,236 direct routes (86.9%), the cheapest path is a
  multi-stop path rather than the direct flight. A few very busy legs cost less in total than one
  moderately busy direct route, because 1/w shrinks so fast as w grows. So distances measure "how
  well connected through heavy traffic", not "how many flights". Opsahl et al. (2010) discuss this
  effect and propose a tuning parameter that blends hops and weights; we do not use it.
- **No effect on the timing comparison.** Floyd-Warshall does n^3 work whatever the weights are, and
  Dijkstra's work depends mainly on n and m. The choice changes what the distances *mean*, not how
  long the algorithms take, so the benchmark stays a fair comparison.
- **Floating point.** Costs range from about 6.7e-7 to 1. Different algorithms add them in a
  different order, so results can differ in the last few digits. Tests compare with a tolerance
  (`np.allclose`), never exact equality.

---

## D2. Wiki Conflict: distance = hops (decided 2026-10-12)

### What we chose
Every pair of editors who interacted at least once becomes **one undirected edge of length 1**. The
sign (agreement / disagreement) and the size (ln k) are **not** used as distances. The shortest path
between two editors is the smallest number of interaction steps that connects them.

### Plain-language explanation
In this network an edge means "these two editors worked on the same text", and its sign says whether
they agreed (+) or one undid the other's work (-). It is tempting to use the signed numbers as
distances, but that does not work, for two reasons.

**1. A negative number is not a distance.** Two editors who clashed are not "closer than zero apart".
A distance has to be zero or more.

**2. Negative numbers make the question meaningless.** The network is *undirected*: if A interacted
with B, then B interacted with A. So a single disagreement A-B with weight -0.69 already forms a
loop: A -> B -> A costs -1.39, going round twice costs -2.77, and so on forever. There is no
"shortest" path, just as there is no "smallest number". This is not a weakness of one algorithm; no
algorithm can answer a question that has no answer.
- Dijkstra would silently give wrong answers (its rule "once settled, a node's distance is final"
  assumes extra road can never make a trip shorter), so our code refuses negative weights.
- Floyd-Warshall would detect the loop and stop.
- Asking instead for the shortest path that never revisits an editor ("simple path") is NP-hard with
  negative weights, so it is not a practical alternative.

So we measure distance the simplest honest way: **how many hand-offs separate two editors**, like
"degrees of separation". About 96% of editors belong to one connected group, and they are on average
about 3.3 steps apart.

### Alternatives considered
| Option | Why not chosen |
|---|---|
| Raw signed weights | negative loops everywhere, so shortest paths are undefined |
| Agreements only (+) | discards 61% of editor pairs; the network falls apart into pieces |
| Disagreements only (-) | discards 37% of editor pairs |
| 1 / size, ignoring the sign | treats fights and agreements as the same thing; what "size" counts is undocumented |
| Johnson's algorithm (handles negative edges) | only works when there are NO negative loops, which is not the case here |

### Consequences (must be discussed in the report)
- All weights are 1. On such a graph **breadth-first search (BFS)** is the optimal single-source
  algorithm (O(n + m), with no priority queue). We still time **genuine Dijkstra**, so the comparison
  with Floyd-Warshall stays like-for-like. The report must say that BFS would be faster here.
- The sign and size information is not part of the distance. It is still reported in the dataset
  characteristics.
- Undirected edges are stored in both directions for the algorithms: 2,027,871 pairs become
  4,055,742 one-way edges, and m in the complexity formulas uses the one-way count.

## D2b. Wiki Conflict: drop editors with no interactions (decided 2026-10-12)

Editor ids run from 1 to 118,100, but 1,264 ids appear in no edge at all. We **drop them**, so
**n = 116,836**.

*Plain language:* these ids belong to editors who never interacted with anyone in this data. They
cannot be reached and cannot reach anyone, so every distance to or from them is "infinite". Keeping
them would add rows and columns of nothing, make Floyd-Warshall's table bigger, and lower the share of
reachable pairs for no real reason. The same rule was applied to US Airports (D1: airports with no
routes are not nodes).

*For the report:* KONECT lists n = 118,100. Our n = 116,836 is the same network minus isolated nodes.

## D3. Wiki Conflict: repeated interactions (decided 2026-10-12)

Under D2, any number of interactions between the same two editors (up to 562 for one pair) becomes
**one** edge of length 1. The 2,917,785 interaction rows become 2,027,871 edges.
