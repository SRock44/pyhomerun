"""Fielding and catching statistics.

Division-by-zero convention: rate stats return ``0.0`` when the
denominator is zero.
"""

from __future__ import annotations

__all__ = [
    "fielding_percentage",
    "range_factor_per_game",
    "range_factor_per_9",
    "caught_stealing_percentage",
]


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def fielding_percentage(putouts: int, assists: int, errors: int) -> float:
    """Fielding percentage (FPCT): share of chances handled cleanly.

    Formula: ``(PO + A) / (PO + A + E)``

    >>> round(fielding_percentage(putouts=250, assists=400, errors=10), 3)
    0.985
    """
    return _safe_div(putouts + assists, putouts + assists + errors)


def range_factor_per_game(putouts: int, assists: int, games: int) -> float:
    """Range factor per game (RF/G): successful chances per game.

    Formula: ``(PO + A) / G``

    >>> round(range_factor_per_game(250, 400, 150), 2)
    4.33
    """
    return _safe_div(putouts + assists, games)


def range_factor_per_9(putouts: int, assists: int, innings_played: float) -> float:
    """Range factor per 9 innings (RF/9).

    Formula: ``9 * (PO + A) / INN`` (pass *true* innings — see
    :func:`pyhomerun.innings`)

    >>> round(range_factor_per_9(250, 400, 1300), 2)
    4.5
    """
    return _safe_div(9 * (putouts + assists), innings_played)


def caught_stealing_percentage(caught_stealing: int, stolen_bases_allowed: int) -> float:
    """Catcher caught-stealing rate (CS%).

    Formula: ``CS / (CS + SB)``

    >>> round(caught_stealing_percentage(caught_stealing=25, stolen_bases_allowed=60), 3)
    0.294
    """
    return _safe_div(caught_stealing, caught_stealing + stolen_bases_allowed)
