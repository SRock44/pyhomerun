"""Team-level statistics: win expectation and standings math.

Division-by-zero convention: rate stats return ``0.0`` when the
denominator is zero.
"""

from __future__ import annotations

from typing import Optional

__all__ = [
    "run_differential",
    "pythagorean_expectation",
    "pythagenpat_exponent",
    "expected_wins",
    "magic_number",
    "log5_win_probability",
]

#: Exponent used by the Pythagenpat formula (David Smyth / Patriot).
_PYTHAGENPAT_POWER = 0.287


def run_differential(runs_scored: int, runs_allowed: int) -> int:
    """Run differential: runs scored minus runs allowed.

    >>> run_differential(800, 700)
    100
    """
    return runs_scored - runs_allowed


def pythagorean_expectation(
    runs_scored: int,
    runs_allowed: int,
    exponent: float = 2.0,
) -> float:
    """Pythagorean win expectation: expected winning percentage from runs.

    Bill James's classic estimator; teams whose actual record beats it
    tend to regress. The classic exponent is 2; use
    :func:`pythagenpat_exponent` for a run-environment-aware exponent.

    Formula: ``RS^x / (RS^x + RA^x)``

    >>> round(pythagorean_expectation(800, 700), 3)
    0.566
    """
    scored = runs_scored**exponent
    allowed = runs_allowed**exponent
    if not scored + allowed:
        return 0.0
    return scored / (scored + allowed)


def pythagenpat_exponent(runs_scored: int, runs_allowed: int, games: int) -> float:
    """Pythagenpat exponent: adapts the Pythagorean exponent to the
    scoring environment (higher-scoring games warrant a larger exponent).

    Formula: ``((RS + RA) / G) ** 0.287``

    >>> round(pythagenpat_exponent(800, 700, 162), 2)
    1.89
    """
    if not games:
        return 0.0
    runs_per_game = (runs_scored + runs_allowed) / games
    return runs_per_game**_PYTHAGENPAT_POWER


def expected_wins(
    runs_scored: int,
    runs_allowed: int,
    games: int,
    exponent: Optional[float] = None,
) -> float:
    """Expected win total from runs scored and allowed.

    Uses the Pythagenpat exponent by default; pass ``exponent=2.0`` for
    the classic Pythagorean version.

    >>> round(expected_wins(800, 700, 162), 1)
    91.2
    """
    if exponent is None:
        exponent = pythagenpat_exponent(runs_scored, runs_allowed, games)
    return games * pythagorean_expectation(runs_scored, runs_allowed, exponent)


def magic_number(
    leader_wins: int,
    second_place_losses: int,
    season_games: int = 162,
) -> int:
    """Magic number: wins (or trailer losses) needed to clinch.

    Any combination of leader wins and second-place-team losses totalling
    the magic number clinches the title. Zero or below means clinched.

    Formula: ``G + 1 - W(leader) - L(second place)``

    >>> magic_number(leader_wins=90, second_place_losses=60)
    13
    """
    return season_games + 1 - leader_wins - second_place_losses


def log5_win_probability(win_pct_a: float, win_pct_b: float) -> float:
    """Bill James's log5: probability team A beats team B, from each
    team's overall winning percentage (e.g. from :func:`pythagorean_expectation`
    or a raw W-L record).

    Formula: ``(a - a*b) / (a + b - 2*a*b)``

    Degenerates to ``0.5`` when the denominator is zero, which only
    happens at the extremes (e.g. both teams 0.000 or both 1.000) where
    there's no information to break the tie.

    >>> round(log5_win_probability(0.600, 0.400), 3)
    0.692
    >>> log5_win_probability(0.500, 0.500)
    0.5
    """
    denominator = win_pct_a + win_pct_b - 2 * win_pct_a * win_pct_b
    if not denominator:
        return 0.5
    return (win_pct_a - win_pct_a * win_pct_b) / denominator
