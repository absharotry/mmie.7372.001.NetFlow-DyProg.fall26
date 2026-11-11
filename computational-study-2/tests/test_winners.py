"""Tests for the winner rule: the 27-of-30 count, the 5% ratio, symmetry, and ties."""

import pytest

from maxflow.winners import decide


def paired(a_better: int, ratio: float, orders: int = 30):
    """A's values are `ratio` times B's in `a_better` orders and 1 / ratio times in the rest."""
    a = [ratio if k < a_better else 1 / ratio for k in range(orders)]
    return a, [1.0] * orders


def test_clear_win_needs_27_of_30():
    assert decide("SAP", "PP", *paired(27, 0.9)).verdict == "SAP clear win"
    assert decide("SAP", "PP", *paired(26, 0.9)).verdict == "no clear winner"


def test_clear_win_needs_a_5_percent_median_ratio():
    # Better in all 30 orders, but only about 3% faster: not a clear win.
    assert decide("SAP", "PP", *paired(30, 0.97)).verdict == "no clear winner"
    assert decide("SAP", "PP", *paired(30, 1 / 1.05)).verdict == "SAP clear win"  # exactly 5% counts


def test_the_rule_treats_both_directions_alike():
    # Distinct ratios, so the Wilcoxon ranks cannot hinge on last-digit rounding of exact ties.
    a = [0.8 + 0.001 * k for k in range(28)] + [1.2 + 0.01 * k for k in range(2)]
    b = [1.0] * 30
    forward, backward = decide("SAP", "PP", a, b), decide("PP", "SAP", b, a)
    assert forward.verdict == "SAP clear win" and backward.verdict == "SAP clear win"
    assert forward.median_ratio == pytest.approx(1 / backward.median_ratio)
    assert (forward.a_wins, forward.b_wins) == (backward.b_wins, backward.a_wins)
    assert forward.p_value == pytest.approx(backward.p_value)


def test_ties_and_identical_values():
    same = decide("SAP", "PP", [2.0] * 30, [2.0] * 30)
    assert (same.ties, same.verdict, same.p_value, same.median_ratio) == (30, "no clear winner", None, 1.0)


def test_wilcoxon_is_reported_but_never_decides():
    result = decide("SAP", "PP", *paired(26, 0.5))
    assert result.p_value < 0.001 and result.verdict == "no clear winner"


def test_mismatched_lists_are_refused():
    with pytest.raises(ValueError):
        decide("SAP", "PP", [1.0, 2.0], [1.0])
