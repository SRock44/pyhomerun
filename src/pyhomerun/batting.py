"""Batting (offensive) statistics.

Every function takes plain counting stats (hits, walks, at-bats, ...) and
returns a float, so you can use them with numbers from any data source.

Division-by-zero convention: when a rate stat's denominator is zero (e.g.
AVG with 0 at-bats), functions return ``0.0`` rather than raising.
"""

from __future__ import annotations

from .constants import DEFAULT_WOBA_WEIGHTS, WobaWeights

__all__ = [
    "batting_average",
    "on_base_percentage",
    "slugging_percentage",
    "ops",
    "ops_plus",
    "total_bases",
    "isolated_power",
    "babip",
    "woba",
    "wraa",
    "plate_appearances",
    "walk_rate",
    "strikeout_rate",
    "stolen_base_percentage",
]


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def batting_average(hits: int, at_bats: int) -> float:
    """Batting average (AVG): hits per at-bat.

    Formula: ``H / AB``

    >>> round(batting_average(hits=200, at_bats=600), 3)
    0.333
    """
    return _safe_div(hits, at_bats)


def on_base_percentage(
    hits: int,
    walks: int,
    hit_by_pitch: int,
    at_bats: int,
    sacrifice_flies: int = 0,
) -> float:
    """On-base percentage (OBP): how often a batter reaches base.

    Formula: ``(H + BB + HBP) / (AB + BB + HBP + SF)``

    >>> round(on_base_percentage(180, 70, 5, 550, 5), 3)
    0.405
    """
    return _safe_div(
        hits + walks + hit_by_pitch,
        at_bats + walks + hit_by_pitch + sacrifice_flies,
    )


def total_bases(hits: int, doubles: int, triples: int, home_runs: int) -> int:
    """Total bases (TB) from hits and extra-base hit counts.

    ``hits`` is *all* hits (singles included); extra-base hits are counted
    again for their additional bases.

    Formula: ``H + 2B + 2*3B + 3*HR``

    >>> total_bases(hits=150, doubles=30, triples=5, home_runs=25)
    265
    """
    return hits + doubles + 2 * triples + 3 * home_runs


def slugging_percentage(total_bases_: int, at_bats: int) -> float:
    """Slugging percentage (SLG): total bases per at-bat.

    Formula: ``TB / AB`` — use :func:`total_bases` to get TB from hit counts.

    >>> round(slugging_percentage(total_bases_=300, at_bats=550), 3)
    0.545
    """
    return _safe_div(total_bases_, at_bats)


def ops(on_base: float, slugging: float) -> float:
    """On-base plus slugging (OPS).

    Formula: ``OBP + SLG``

    >>> round(ops(0.400, 0.550), 3)
    0.95
    """
    return on_base + slugging


def ops_plus(
    on_base: float,
    slugging: float,
    league_obp: float,
    league_slg: float,
) -> float:
    """OPS+ — OPS normalized to league average, where 100 is average.

    This is the un-park-adjusted form; a full OPS+ also divides by a park
    factor, which you can apply to the league rates before calling.

    Formula: ``100 * (OBP/lgOBP + SLG/lgSLG - 1)``

    >>> round(ops_plus(0.400, 0.550, 0.320, 0.410), 0)
    159.0
    """
    if not league_obp or not league_slg:
        return 0.0
    return 100 * (on_base / league_obp + slugging / league_slg - 1)


def isolated_power(slugging: float, average: float) -> float:
    """Isolated power (ISO): extra bases per at-bat.

    Formula: ``SLG - AVG``

    >>> round(isolated_power(0.550, 0.300), 3)
    0.25
    """
    return slugging - average


def babip(
    hits: int,
    home_runs: int,
    at_bats: int,
    strikeouts: int,
    sacrifice_flies: int = 0,
) -> float:
    """Batting average on balls in play (BABIP).

    Measures results on balls put in play, excluding home runs and
    strikeouts. League average sits near .300; large deviations often
    signal luck rather than skill.

    Formula: ``(H - HR) / (AB - K - HR + SF)``

    >>> round(babip(hits=160, home_runs=20, at_bats=550, strikeouts=120, sacrifice_flies=5), 3)
    0.337
    """
    return _safe_div(hits - home_runs, at_bats - strikeouts - home_runs + sacrifice_flies)


def woba(
    walks: int,
    hit_by_pitch: int,
    singles: int,
    doubles: int,
    triples: int,
    home_runs: int,
    at_bats: int,
    intentional_walks: int = 0,
    sacrifice_flies: int = 0,
    weights: WobaWeights = DEFAULT_WOBA_WEIGHTS,
) -> float:
    """Weighted on-base average (wOBA).

    Like OBP, but each way of reaching base is credited with its actual
    run value, making it one of the best single-number offensive stats.
    ``walks`` should be *total* walks; intentional walks are excluded via
    the ``intentional_walks`` argument.

    Formula::

        (wBB*(BB-IBB) + wHBP*HBP + w1B*1B + w2B*2B + w3B*3B + wHR*HR)
        / (AB + BB - IBB + SF + HBP)

    Season-exact weights can be passed via ``weights``; see
    :class:`pyhomerun.WobaWeights` and the FanGraphs Guts! page.

    >>> round(woba(walks=70, hit_by_pitch=5, singles=100, doubles=30,
    ...            triples=5, home_runs=25, at_bats=550,
    ...            intentional_walks=5, sacrifice_flies=5), 3)
    0.373
    """
    numerator = (
        weights.bb * (walks - intentional_walks)
        + weights.hbp * hit_by_pitch
        + weights.single * singles
        + weights.double * doubles
        + weights.triple * triples
        + weights.home_run * home_runs
    )
    denominator = at_bats + walks - intentional_walks + sacrifice_flies + hit_by_pitch
    return _safe_div(numerator, denominator)


def wraa(
    woba_: float,
    plate_appearances_: int,
    weights: WobaWeights = DEFAULT_WOBA_WEIGHTS,
) -> float:
    """Weighted runs above average (wRAA): offensive runs vs. an average hitter.

    Formula: ``((wOBA - lgwOBA) / wOBA scale) * PA``

    >>> round(wraa(0.380, 600), 1)
    33.9
    """
    if not weights.woba_scale:
        return 0.0
    return ((woba_ - weights.league_woba) / weights.woba_scale) * plate_appearances_


def plate_appearances(
    at_bats: int,
    walks: int,
    hit_by_pitch: int,
    sacrifice_hits: int = 0,
    sacrifice_flies: int = 0,
    catcher_interference: int = 0,
) -> int:
    """Plate appearances (PA): every completed trip to the plate.

    Formula: ``AB + BB + HBP + SH + SF + CI``

    >>> plate_appearances(at_bats=550, walks=70, hit_by_pitch=5,
    ...                   sacrifice_hits=2, sacrifice_flies=5)
    632
    """
    return at_bats + walks + hit_by_pitch + sacrifice_hits + sacrifice_flies + catcher_interference


def walk_rate(walks: int, plate_appearances_: int) -> float:
    """Walk rate (BB%): walks per plate appearance.

    Formula: ``BB / PA``

    >>> round(walk_rate(70, 632), 3)
    0.111
    """
    return _safe_div(walks, plate_appearances_)


def strikeout_rate(strikeouts: int, plate_appearances_: int) -> float:
    """Strikeout rate (K%): strikeouts per plate appearance.

    Formula: ``K / PA``

    >>> round(strikeout_rate(120, 632), 3)
    0.19
    """
    return _safe_div(strikeouts, plate_appearances_)


def stolen_base_percentage(stolen_bases: int, caught_stealing: int) -> float:
    """Stolen-base success rate (SB%).

    Formula: ``SB / (SB + CS)``

    >>> round(stolen_base_percentage(30, 10), 3)
    0.75
    """
    return _safe_div(stolen_bases, stolen_bases + caught_stealing)
