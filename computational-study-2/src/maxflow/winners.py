"""The winner rule (docs/data_modeling.md, Section 10.4), fixed before any results existed.

For one data case, one pair of settings (A against B) and one measure (time or total work), there is
one paired value per shuffled door order: both settings ran on the same shuffled building.

- Clear win: the same setting is better in at least 27 of the 30 orders, and the median ratio differs
  from 1 by at least 5%: the median, over the orders, of slower / faster is at least 1.05.
- Anything else: no clear winner.

The median ratio is taken on the log scale, exp(median(log(A / B))), so it is exactly symmetric: the
A-against-B ratio is the reciprocal of the B-against-A ratio, and neither direction is favoured.

A Wilcoxon signed-rank test on the paired log ratios (two-sided) is reported alongside. It never
decides the verdict.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from scipy.stats import wilcoxon

MIN_WINS = 27  # of 30 orders
MIN_RATIO = 1.05  # slower / faster


@dataclass
class Verdict:
    a: str
    b: str
    orders: int
    a_wins: int  # orders where A had the smaller value
    b_wins: int
    ties: int
    median_ratio: float  # A / B on the log scale; below 1 means A was faster or did less work
    p_value: float | None  # Wilcoxon signed-rank, two-sided; None if every pair was tied
    verdict: str  # "<A> clear win", "<B> clear win" or "no clear winner"


def decide(a: str, b: str, a_values: list[float], b_values: list[float],
           min_wins: int = MIN_WINS, min_ratio: float = MIN_RATIO) -> Verdict:
    """Apply the winner rule to paired values (same order, same position in both lists)."""
    if len(a_values) != len(b_values) or not a_values:
        raise ValueError("need the same, non-zero number of paired values for both settings")
    pairs = list(zip(a_values, b_values))
    a_wins = sum(x < y for x, y in pairs)
    b_wins = sum(x > y for x, y in pairs)
    logs = [math.log(x / y) for x, y in pairs]
    median_log = statistics.median(logs)
    p_value = float(wilcoxon(logs).pvalue) if any(logs) else None
    big_enough = abs(median_log) >= math.log(min_ratio) - 1e-12  # tolerance: a ratio of exactly 1.05 counts
    if a_wins >= min_wins and median_log < 0 and big_enough:
        verdict = f"{a} clear win"
    elif b_wins >= min_wins and median_log > 0 and big_enough:
        verdict = f"{b} clear win"
    else:
        verdict = "no clear winner"
    return Verdict(a, b, len(pairs), a_wins, b_wins, len(pairs) - a_wins - b_wins, math.exp(median_log),
                   p_value, verdict)
