"""Synthetic random networks for the density experiment (Phase 5).

Real networks change size and density together; random networks with a FIXED number of nodes n and
a varying edge probability p isolate the effect of density.
"""

import numpy as np

from apsp.loaders import Dataset

WEIGHT_LOW, WEIGHT_HIGH = 1.0, 10.0


def random_digraph(n, p, seed):
    """Directed G(n, p): every ordered pair (i, j), i != j, is an edge independently with
    probability p. Weights uniform in [1, 10). Same (n, p, seed) -> same graph."""
    rng = np.random.default_rng(seed)
    mask = rng.random((n, n)) < p
    np.fill_diagonal(mask, False)  # no self-loops
    u, v = np.nonzero(mask)
    w = rng.uniform(WEIGHT_LOW, WEIGHT_HIGH, size=len(u))
    return Dataset(name=f"G(n={n}, p={p:g})", n=n, u=u.astype(np.int64), v=v.astype(np.int64), w=w,
                   directed=True, weight_meaning=f"uniform [{WEIGHT_LOW:g}, {WEIGHT_HIGH:g})",
                   source=f"synthetic, numpy default_rng seed {seed}")


def slug(n, p):
    return f"density-n{n}-p{p:.4f}"
