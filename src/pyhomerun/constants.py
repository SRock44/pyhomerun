"""League constants used by linear-weight statistics.

Sabermetric stats such as wOBA and FIP depend on *league environment*
constants that change slightly from season to season. This module ships a
representative set of modern-era defaults so the library works out of the
box, and a small dataclass so you can supply exact season values yourself.

Exact per-season values are published for free on the FanGraphs "Guts!"
page: https://www.fangraphs.com/guts.aspx
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["WobaWeights", "DEFAULT_WOBA_WEIGHTS", "DEFAULT_FIP_CONSTANT"]


@dataclass(frozen=True)
class WobaWeights:
    """Linear weights for computing wOBA (weighted on-base average).

    Each field is the average run value of that event relative to an out,
    scaled so that league-average wOBA matches league-average OBP.

    Attributes:
        bb: Run value of an unintentional walk.
        hbp: Run value of a hit-by-pitch.
        single: Run value of a single.
        double: Run value of a double.
        triple: Run value of a triple.
        home_run: Run value of a home run.
        league_woba: League-average wOBA for the season (used by wRAA).
        woba_scale: Scale factor mapping wOBA points to runs (used by wRAA).
    """

    bb: float
    hbp: float
    single: float
    double: float
    triple: float
    home_run: float
    league_woba: float
    woba_scale: float


#: Representative modern-era (approximately 2024) league weights.
#: Fine for exploration and teaching; for published research, pull the exact
#: season values from FanGraphs Guts! and construct your own ``WobaWeights``.
DEFAULT_WOBA_WEIGHTS = WobaWeights(
    bb=0.69,
    hbp=0.72,
    single=0.88,
    double=1.25,
    triple=1.59,
    home_run=2.05,
    league_woba=0.310,
    woba_scale=1.24,
)

#: Representative modern-era FIP constant (the value that puts FIP on the
#: same scale as league ERA; roughly 3.1-3.2 in recent seasons).
DEFAULT_FIP_CONSTANT = 3.17
