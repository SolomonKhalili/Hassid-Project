#!/usr/bin/env python3
"""
Betting math: odds conversions, removing the sportsbook's cut, and turning a predicted
margin or total into win / cover / over chances - with pushes handled properly.

Everything here is plain arithmetic with no data in it. Run the file to self-check:

    python3 pricing.py
"""

from __future__ import annotations

import math
from statistics import NormalDist

_N = NormalDist()


# ----------------------------------------------------------------------
# Odds conversions
# ----------------------------------------------------------------------

def breakeven(odds: float) -> float:
    """Win rate needed to break even at American odds.  -110 -> 0.5238,  +150 -> 0.40"""
    return -odds / (-odds + 100) if odds < 0 else 100 / (odds + 100)


def payout(odds: float) -> float:
    """Profit on a winning 1-unit bet.  -110 -> 0.909,  +150 -> 1.5"""
    return 100 / -odds if odds < 0 else odds / 100


def fair_american(prob: float) -> int | None:
    """American odds with no sportsbook cut for a probability.  0.60 -> -150,  0.40 -> +150"""
    if not 0 < prob < 1:
        return None
    return -round(100 * prob / (1 - prob)) if prob >= 0.5 else round(100 * (1 - prob) / prob)


def fmt_american(odds: float | None) -> str:
    if odds is None:
        return "-"
    return f"+{int(odds)}" if odds > 0 else str(int(odds))


# ----------------------------------------------------------------------
# Removing the sportsbook's cut ("de-vig")
# ----------------------------------------------------------------------

def devig(odds_a: float, odds_b: float, method: str = "power") -> tuple[float, float]:
    """The market's fair chance for each side of a two-way bet.

    The two break-evens add up to more than 100% - the extra is the book's cut.
      multiplicative  scale both down by the same factor (fine near even money)
      power           raise both to the same power so they sum to 1 - takes more of the
                      cut off the longshot, which matches how books shade big underdogs
      additive        subtract the same amount from each
    -113 / +103 -> about 51.9% / 48.1% by every method.
    """
    a, b = breakeven(odds_a), breakeven(odds_b)
    if method == "multiplicative":
        return a / (a + b), b / (a + b)
    if method == "additive":
        cut = (a + b - 1) / 2
        return a - cut, b - cut
    if method == "power":
        if a + b <= 1:                     # no cut to remove (rare, stale prices)
            return a / (a + b), b / (a + b)
        lo, hi = 1.0, 10.0
        for _ in range(60):                # solve a^k + b^k = 1 for k
            k = (lo + hi) / 2
            if a ** k + b ** k > 1:
                lo = k
            else:
                hi = k
        return a ** k, b ** k
    raise ValueError(f"unknown de-vig method {method!r}")


def hold(odds_a: float, odds_b: float) -> float:
    """The book's cut on a two-way market.  -110 / -110 -> 4.5%"""
    total = breakeven(odds_a) + breakeven(odds_b)
    return 1 - 1 / total


# ----------------------------------------------------------------------
# Predicted number -> chances
#
# Final margins and totals are whole numbers, so a whole-number line can push (tie, stake
# returned). Each function returns (win, push, lose) for the side named.
# ----------------------------------------------------------------------

def _above(mean: float, sd: float, line: float) -> tuple[float, float, float]:
    """Chances that a whole-number result lands above / exactly on / below `line`."""
    if float(line).is_integer():
        hi = _N.cdf((line + 0.5 - mean) / sd)
        lo = _N.cdf((line - 0.5 - mean) / sd)
        return 1 - hi, hi - lo, lo
    p = 1 - _N.cdf((line - mean) / sd)
    return p, 0.0, 1 - p


def win_prob(margin: float, sd: float) -> float:
    """Chance the team wins the game, from its predicted margin.

    A game can't end level, so the sliver of the curve sitting on "margin 0" is shared
    out between the two sides.
    """
    win, tie, lose = _above(margin, sd, 0.0)
    return win / (win + lose)


def cover_prob(margin: float, sd: float, spread: float) -> tuple[float, float, float]:
    """(win, push, lose) for a team at `spread`, given its predicted margin.

    spread is that team's own line: -5.5 means it must win by 6 or more,
    +5.5 means it can lose by up to 5.
    """
    return _above(margin, sd, -spread)


def over_prob(total: float, sd: float, line: float) -> tuple[float, float, float]:
    """(win, push, lose) for the OVER at `line`, given the predicted total."""
    return _above(total, sd, line)


def flip(wpl: tuple[float, float, float]) -> tuple[float, float, float]:
    """The other side of the same bet."""
    return wpl[2], wpl[1], wpl[0]


# ----------------------------------------------------------------------
# Value of a bet
# ----------------------------------------------------------------------

def expected_value(win: float, lose: float, odds: float) -> float:
    """Expected profit per 1 unit staked. A push returns the stake, so it adds nothing."""
    return win * payout(odds) - lose


def edge_pts(win: float, lose: float, odds: float) -> float:
    """Our chance of winning a bet that doesn't push, minus the break-even, in points."""
    decided = win + lose
    return (win / decided - breakeven(odds)) * 100 if decided > 0 else 0.0


def kelly(win: float, lose: float, odds: float) -> float:
    """Full-Kelly share of bankroll (0 when the bet has no edge). Use a fraction of it."""
    b = payout(odds)
    decided = win + lose
    if decided <= 0:
        return 0.0
    p = win / decided
    return max(0.0, (p * b - (1 - p)) / b) * decided


# ----------------------------------------------------------------------
# Self-check
# ----------------------------------------------------------------------

def _self_check() -> None:
    near = lambda x, y, tol=1e-3: abs(x - y) < tol  # noqa: E731
    assert near(breakeven(-110), 0.5238) and near(breakeven(150), 0.40)
    assert near(payout(-110), 0.9091) and near(payout(150), 1.5)
    assert fair_american(0.60) == -150 and fair_american(0.40) == 150
    assert fair_american(0.65) == -186 and fair_american(0.56) == -127
    for m in ("multiplicative", "power", "additive"):
        a, b = devig(-113, 103, m)
        assert near(a + b, 1.0, 1e-6) and near(a, 0.519, 2e-3), (m, a)
    a, b = devig(-900, 600, "power")             # power takes more off the longshot
    assert a + b > 0.9999 and b < devig(-900, 600, "multiplicative")[1]
    assert near(hold(-110, -110), 0.0455)
    assert near(win_prob(0, 12), 0.5) and win_prob(5, 12) > 0.6
    w, p, l = cover_prob(6.0, 12, -5.5)          # predicted to win by 6, laying 5.5
    assert p == 0 and near(w + l, 1) and near(w, 0.5166)
    w, p, l = cover_prob(6.0, 12, -6)            # whole-number line: some chance of a push
    assert p > 0.03 and near(w + p + l, 1) and near(w, l)
    assert cover_prob(-6.0, 12, 6)[0] == cover_prob(6.0, 12, -6)[2]     # the two sides mirror
    w, p, l = over_prob(225, 18, 220.5)
    assert near(w, 0.5987) and flip((w, p, l)) == (l, p, w)
    assert near(expected_value(0.55, 0.45, -110), 0.05) and expected_value(0.5, 0.5, -110) < 0
    assert near(edge_pts(0.55, 0.45, -110), 2.62, 0.01)
    assert kelly(0.5, 0.5, -110) == 0 and near(kelly(0.55, 0.45, -110), 0.055)
    print("pricing.py: all checks passed")


if __name__ == "__main__":
    _self_check()
