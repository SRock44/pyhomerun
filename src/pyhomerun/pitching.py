"""Pitching statistics.

Innings-pitched note: baseball box scores display partial innings as
``.1`` (one out) and ``.2`` (two outs), but math needs true thirds
(6.1 innings is really 6 1/3). Use :func:`innings` to convert the display
form, or :func:`innings_from_outs` if you have an out count.

Division-by-zero convention: rate stats with a zero denominator return
``0.0`` when the numerator is also zero, and ``math.inf`` when runs/hits
were allowed without recording an out (matching how ERA is reported).
"""

from __future__ import annotations

import math

from .constants import DEFAULT_FIP_CONSTANT

__all__ = [
    "innings",
    "innings_from_outs",
    "era",
    "era_plus",
    "era_minus",
    "whip",
    "fip",
    "xfip",
    "k_per_9",
    "bb_per_9",
    "hr_per_9",
    "h_per_9",
    "k_bb_ratio",
    "left_on_base_percentage",
    "game_score",
]


def innings(displayed: float) -> float:
    """Convert box-score innings notation to true innings.

    In box scores, ``6.1`` means 6 innings plus 1 out and ``6.2`` means
    6 innings plus 2 outs. This converts that notation to real thirds so
    rate stats compute correctly.

    >>> round(innings(6.2), 4)
    6.6667
    >>> innings(7.0)
    7.0
    """
    whole = int(displayed)
    outs = round((displayed - whole) * 10)
    if outs not in (0, 1, 2):
        raise ValueError(
            f"invalid innings notation {displayed!r}: the decimal part must be .0, .1, or .2"
        )
    return whole + outs / 3


def innings_from_outs(outs: int) -> float:
    """True innings pitched from a total out count.

    >>> innings_from_outs(20)  # 6 innings and 2 outs
    6.666666666666667
    """
    return outs / 3


def _per_inning_rate(numerator: float, innings_pitched: float, scale: float) -> float:
    if innings_pitched:
        return scale * numerator / innings_pitched
    return math.inf if numerator else 0.0


def era(earned_runs: int, innings_pitched: float) -> float:
    """Earned run average (ERA): earned runs allowed per 9 innings.

    Formula: ``9 * ER / IP`` (pass *true* innings — see :func:`innings`)

    >>> round(era(earned_runs=65, innings_pitched=180), 2)
    3.25
    """
    return _per_inning_rate(earned_runs, innings_pitched, 9)


def era_plus(era_: float, league_era: float, park_factor: float = 1.0) -> float:
    """ERA+ — ERA relative to league, where 100 is average and higher is
    better (an ERA+ of 150 means 50% better than league average).

    Formula: ``100 * (lgERA * PF) / ERA``

    >>> round(era_plus(3.00, 4.20))
    140
    """
    if not era_:
        return math.inf if league_era * park_factor else 0.0
    return 100 * (league_era * park_factor) / era_


def era_minus(era_: float, league_era: float, park_factor: float = 1.0) -> float:
    """ERA- — ERA relative to league, where 100 is average and *lower* is
    better (an ERA- of 75 means 25% better than league average).

    Formula: ``100 * ERA / (lgERA * PF)``

    >>> round(era_minus(3.00, 4.20), 1)
    71.4
    """
    denominator = league_era * park_factor
    if not denominator:
        return 0.0
    return 100 * era_ / denominator


def whip(walks: int, hits: int, innings_pitched: float) -> float:
    """Walks plus hits per inning pitched (WHIP).

    Formula: ``(BB + H) / IP``

    >>> round(whip(walks=50, hits=160, innings_pitched=180), 2)
    1.17
    """
    return _per_inning_rate(walks + hits, innings_pitched, 1)


def fip(
    home_runs: int,
    walks: int,
    hit_by_pitch: int,
    strikeouts: int,
    innings_pitched: float,
    constant: float = DEFAULT_FIP_CONSTANT,
) -> float:
    """Fielding independent pitching (FIP).

    Estimates a pitcher's ERA from only the outcomes a pitcher controls
    (strikeouts, walks, hit batters, home runs), stripping out defense
    and batted-ball luck.

    Formula: ``(13*HR + 3*(BB+HBP) - 2*K) / IP + constant``

    The constant puts FIP on the league ERA scale and varies slightly by
    season (exact values on FanGraphs Guts!); the default is a
    representative modern value.

    >>> round(fip(home_runs=18, walks=45, hit_by_pitch=5, strikeouts=190,
    ...           innings_pitched=180), 2)
    3.19
    """
    if not innings_pitched:
        return 0.0
    core = (13 * home_runs + 3 * (walks + hit_by_pitch) - 2 * strikeouts) / innings_pitched
    return core + constant


def xfip(
    fly_balls: int,
    walks: int,
    hit_by_pitch: int,
    strikeouts: int,
    innings_pitched: float,
    league_hr_per_fb: float = 0.105,
    constant: float = DEFAULT_FIP_CONSTANT,
) -> float:
    """Expected FIP (xFIP): FIP with home runs replaced by an expectation.

    Home-run-per-fly-ball rate is noisy, so xFIP substitutes the league
    rate (historically 9-13%; pass the exact season value if you have it)
    applied to the pitcher's fly balls allowed.

    Formula: ``(13*(FB * lgHR/FB) + 3*(BB+HBP) - 2*K) / IP + constant``

    >>> round(xfip(fly_balls=200, walks=45, hit_by_pitch=5, strikeouts=190,
    ...            innings_pitched=180), 2)
    3.41
    """
    if not innings_pitched:
        return 0.0
    expected_hr = fly_balls * league_hr_per_fb
    core = (13 * expected_hr + 3 * (walks + hit_by_pitch) - 2 * strikeouts) / innings_pitched
    return core + constant


def k_per_9(strikeouts: int, innings_pitched: float) -> float:
    """Strikeouts per 9 innings (K/9).

    >>> round(k_per_9(190, 180), 2)
    9.5
    """
    return _per_inning_rate(strikeouts, innings_pitched, 9)


def bb_per_9(walks: int, innings_pitched: float) -> float:
    """Walks per 9 innings (BB/9).

    >>> round(bb_per_9(45, 180), 2)
    2.25
    """
    return _per_inning_rate(walks, innings_pitched, 9)


def hr_per_9(home_runs: int, innings_pitched: float) -> float:
    """Home runs allowed per 9 innings (HR/9).

    >>> round(hr_per_9(18, 180), 2)
    0.9
    """
    return _per_inning_rate(home_runs, innings_pitched, 9)


def h_per_9(hits: int, innings_pitched: float) -> float:
    """Hits allowed per 9 innings (H/9).

    >>> round(h_per_9(160, 180), 2)
    8.0
    """
    return _per_inning_rate(hits, innings_pitched, 9)


def k_bb_ratio(strikeouts: int, walks: int) -> float:
    """Strikeout-to-walk ratio (K/BB).

    >>> round(k_bb_ratio(190, 45), 2)
    4.22
    """
    if walks:
        return strikeouts / walks
    return math.inf if strikeouts else 0.0


def left_on_base_percentage(
    hits: int,
    walks: int,
    hit_by_pitch: int,
    runs: int,
    home_runs: int,
) -> float:
    """Left-on-base percentage (LOB%): share of baserunners stranded.

    League average is roughly 72%; extreme values tend to regress.

    Formula: ``(H + BB + HBP - R) / (H + BB + HBP - 1.4*HR)``

    >>> round(left_on_base_percentage(hits=160, walks=50, hit_by_pitch=5,
    ...                               runs=70, home_runs=18), 3)
    0.764
    """
    denominator = hits + walks + hit_by_pitch - 1.4 * home_runs
    if not denominator:
        return 0.0
    return (hits + walks + hit_by_pitch - runs) / denominator


def game_score(
    outs: int,
    strikeouts: int,
    hits: int,
    earned_runs: int,
    unearned_runs: int,
    walks: int,
) -> float:
    """Bill James Game Score (v1) for a single start.

    Starts at 50; 90+ is a gem, below 20 is a disaster.

    Scoring: +1 per out, +2 per completed inning after the 4th, +1 per
    strikeout, -2 per hit, -4 per earned run, -2 per unearned run,
    -1 per walk.

    >>> game_score(outs=27, strikeouts=10, hits=3, earned_runs=0,
    ...            unearned_runs=0, walks=1)  # a dominant complete game
    90
    """
    completed_innings = outs // 3
    innings_past_fourth = max(0, completed_innings - 4)
    return (
        50
        + outs
        + 2 * innings_past_fourth
        + strikeouts
        - 2 * hits
        - 4 * earned_runs
        - 2 * unearned_runs
        - walks
    )
