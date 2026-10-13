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
