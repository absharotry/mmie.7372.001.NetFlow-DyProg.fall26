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

---

## D4. Slashdot Zoo: friends only, distance = hops (decided 2026-10-12)

### What we chose
Keep only **friend** tags (+1). Remove all **foe** tags (-1). Each friend tag "A -> B" becomes a
one-way edge of length 1, **direction kept** (A calling B a friend does not mean B calls A a friend).
The shortest path from A to B is the fewest "friend of a friend of ..." steps from A to B.

### Plain-language explanation
On Slashdot, users tag other users as **friend** or **foe**. In the raw data a friend tag is +1 and a
foe tag is -1. We cannot use those numbers as distances:

- **A foe tag is not a "negative distance".** Disliking someone does not bring you closer than zero.
- **Negative loops exist.** 4,497 pairs of users tag *each other* as foes. Going A -> B -> A then
  costs -1 + -1 = -2, and every extra lap lowers it further, so "shortest" has no answer. (Johnson's
  algorithm, which handles some negative edges, needs the graph to have no negative loops, so it
  does not apply.)

We keep the friend tags because they have a clear meaning: a path is a chain of people who vouch
for the next person, like "a friend of a friend of a friend". A short path means two users are
close in the network of goodwill. Foe tags express the opposite, so they do not belong in a chain
of friendships, and we leave them out.

### Alternatives considered
| Option | Why not chosen |
|---|---|
| Raw +1 / -1 weights | 4,497 negative 2-cycles, so shortest paths are undefined |
| Hops on all tags, ignoring sign (the Wiki Conflict rule, D2) | treats "foe" as a connection like "friend"; the friend-only network has a clearer meaning |
| Foes only | keeps just 24% of tags; "chains of hostility" are hard to interpret |

### Consequences (must be discussed in the report)
- **Different rule from Wiki Conflict.** Wiki Conflict (D2) keeps every interaction and ignores the
  sign; Slashdot keeps only friend tags. The report should state this and the reason: in Slashdot
  the sign marks the relationship itself (friend vs foe), while in Wiki Conflict both kinds of
  interaction show that two editors worked on the same text.
- **Smaller graph:** 123,218 foe tags removed (24% of edges), leaving 392,179 friend tags.
- **Low reachability:** only 36.3% of ordered user pairs are connected by a chain of friend tags,
  mostly because 41% of the remaining users never tagged anyone as a friend.
- **All weights are 1,** so the BFS note from D2 applies: BFS would be the optimal single-source
  algorithm, and we time genuine Dijkstra for a like-for-like comparison.
- **Floyd-Warshall is infeasible:** a 69,995 x 69,995 table is about 36.5 GiB, more than the 24 GiB
  of RAM on the benchmark machine.

## D4b. Slashdot Zoo: drop users with no friend tags (decided 2026-10-12)

The D2b rule (keep only nodes with at least one edge), applied **after** removing foe tags.
4 users have no tags at all, and 9,121 users had only foe tags, so they have no edges left in the
friend network. All 9,125 are dropped: **n = 79,120 -> 69,995**.

*Plain language:* someone who only ever tagged (or was tagged by) foes has no friendship links, so
they cannot appear in any friend chain. Keeping them would only add empty rows to the distance table.

### Observation for the report (not a decision)
The out-degree distribution drops sharply near 200 tags, and a handful of users sit at about 400
(max 426). This looks like a **site limit** on how many users one person could tag. We have not found
a source that confirms it.

---

## D5. Adolescent Health: distance = 1 / weight (decided 2026-10-12)

### What we chose
The same rule as US Airports (D1). Each friendship nomination "A named B" has a weight from 1 to 6,
equal to 1 + the number of five activities the two did together. We set **distance = 1 / weight**,
direction kept. All 2,539 students have at least one friendship, so no nodes are dropped.

| Weight | Meaning | Distance |
|---|---|---|
| 1 | named as a friend, no shared activity | 1 |
| 2 | one shared activity | 0.5 |
| 3 | two | 0.33 |
| 4 | three | 0.25 |
| 5 | four | 0.2 |
| 6 | all five | 0.17 |

### Plain-language explanation
Students who do more things together are closer friends. Shortest-path algorithms need the
opposite (a smaller number means closer), so we flip the scale with 1 / weight: a friendship with
all five shared activities becomes a short step (0.17), and a "named but did nothing together"
friendship becomes a long step (1).

Sometimes this means the closest route between two students is not their direct link. If A named B
but they did nothing together (cost 1), while A and C are close friends and C and B are close
friends (cost 0.17 + 0.17 = 0.33), the shortest route from A to B goes through C. That matches how
news or influence could plausibly travel: through the close mutual friend.

### Why this option
- **Consistency:** the same rule as the other strength-weighted dataset (US Airports, D1), so the
  report can state one rule for "strength" weights.
- It is the standard transformation in the literature (Opsahl, Agneessens, Skvoretz, 2010).
- It behaves mildly here: only **8.0%** of direct friendships lose to a multi-step path, almost all
  of them weight-1 ("no shared activity") ties, 25% of which are bypassed. Compare 86.9% for US
  Airports, where weights span a million-fold range instead of six-fold.

### Alternatives considered
| Option | Why not chosen |
|---|---|
| 7 - weight (reverse the scale: 6 .. 1) | reasonable (4.2% of direct ties bypassed), but a less common choice that would need its own justification, and it differs from D1 |
| Hops (ignore activities) | discards the activity information |

### Consequences (must be discussed in the report)
- The weight mapping (1 + number of activities) is **inferred**: KONECT's README sentence about it is
  garbled, and a secondary source confirms only the 1..6 range and the five activities. See
  data/SOURCES.md.
- **No hubs:** the survey allowed at most 10 nominations, so out-degree is at most 10 and the most
  popular student has in-degree 27. Paths are long: 6.3 hops on average, up to 18, about twice the
  airports' 3.2. Fewer hubs means fewer shortcuts.
- **Floating point:** distances like 1/3 and 1/6 are not exact in binary, so tests compare with a
  tolerance (as for D1).

---

## D6. Advogato: distance = 1 / trust level (decided 2026-10-12)

### What we chose
The same rule as US Airports (D1) and Adolescent Health (D5): **distance = 1 / weight**, direction
kept. An edge "A certified B" has a trust level of apprentice (0.6), journeyer (0.8) or master (1.0).

| Level | Weight | Distance |
|---|---|---|
| master | 1.0 | 1.00 |
| journeyer | 0.8 | 1.25 |
| apprentice | 0.6 | 1.67 |

### Plain-language explanation
On Advogato, open-source developers vouched for each other's skill. A higher level means stronger
trust, so we flip it (1 / level) to get a distance where stronger trust means closer.

Something special happens with this dataset: **a direct certification is always the shortest
route.** The cheapest possible step costs 1.00 (master) and the most expensive costs 1.67
(apprentice). Any chain of two or more steps costs at least 1.00 + 1.00 = 2.00, which is more than
the dearest single step. So the trust levels never make a detour worthwhile. They only decide
between routes with the *same* number of steps, preferring those through "master" certifications.
In practice, distance here means "the fewest certification steps, with ties broken by trust level".

### Why this option
- **One rule for all three strength-weighted datasets** (D1, D5, D6).
- The standard transformation in the literature (Opsahl et al., 2010).

### Alternatives considered
| Option | Why not chosen |
|---|---|
| Hops (ignore levels) | discards the trust levels; under 1/w they still break ties |
| -log(level) (trust as a probability multiplied along a chain) | master = -log 1 = 0, so chains of masters would cost nothing (zero-weight edges, and an odd meaning) |

### Consequences (must be discussed in the report)
- **The same rule behaves very differently depending on how spread out the weights are.** Share of
  direct links that lose to a multi-step chain under 1/w:

  | Dataset | Weight range | Direct links bypassed |
  |---|---|---|
  | US Airports | 1 .. 1,489,618 | 86.9% |
  | Adolescent Health | 1 .. 6 | 8.0% |
  | Advogato | 0.6 .. 1.0 | 0% (impossible: 2 x 1.00 > 1.67) |

- The "observer" level (0.4) is documented but never occurs in the data.

## D6b. Advogato: drop self-certifications (decided 2026-10-12)

3,992 edges (7.8%) are users certifying themselves. We **remove them**.

*Plain language:* rating your own skill is not a link between two people. Your distance to yourself
is 0 by definition, so a self-loop can never be part of a shortest path. Keeping them would only
give Dijkstra 3,992 extra edges to scan for nothing, and would inflate m in the complexity formulas.

## D6c. Advogato: drop users with no links to others (decided 2026-10-12)

The D2b rule, applied **after** D6b. 2 users appear in no edge, and 1,384 more only certified
themselves, so 1,386 users have no link to anyone else: **n = 6,541 -> 5,155**, edges 51,127 -> 47,135.

---

## Summary: all five datasets after preprocessing

| Dataset | Directed | n | One-way edges | Distance | Decisions | FW table (float64) |
|---|---|---|---|---|---|---|
| US Airports | yes | 1,574 | 28,236 | 1 / passengers | D1 | 19 MiB |
| Adolescent Health | yes | 2,539 | 12,969 | 1 / (1 + shared activities) | D5 | 49 MiB |
| Advogato | yes | 5,155 | 47,135 | 1 / trust level | D6, D6b, D6c | 203 MiB |
| Slashdot Zoo | yes | 69,995 | 392,179 | hops, friend tags only | D4, D4b | 36.5 GiB |
| Wiki Conflict | no (stored both ways) | 116,836 | 4,055,742 | hops, all interactions | D2, D2b, D3 | 101.7 GiB |

Rules in one sentence each:
- **Strength weights** (passengers, shared activities, trust): distance = 1 / weight.
- **Signed weights** (friend/foe, agree/disagree): negative loops make raw weights unusable. Slashdot
  keeps friend tags only (the sign defines the relationship); Wiki Conflict keeps every interaction
  (both signs show two editors worked on the same text). Both use hops.
- **Nodes with no links** are dropped everywhere; **self-loops and repeats** never affect a
  shortest path and are removed.
