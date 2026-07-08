"""pyhomerun — baseball statistics and MLB data for Python.

Two things, zero dependencies:

* **Sabermetrics** — pure functions for batting, pitching, and fielding
  stats (AVG, OBP, SLG, OPS, wOBA, wRAA, ERA, FIP, WHIP, ...).
* **MLB data** — :class:`MLBClient`, a tiny standard-library client for
  the free MLB Stats API (players, stats, teams, schedules, standings).

Quick start::

    import pyhomerun as bb

    bb.batting_average(hits=200, at_bats=600)   # 0.333...

    mlb = bb.MLBClient()
    judge = mlb.search_players("Aaron Judge")[0]
"""

from .batting import (
    babip,
    batting_average,
    isolated_power,
    on_base_percentage,
    ops,
    ops_plus,
    plate_appearances,
    slugging_percentage,
    stolen_base_percentage,
    strikeout_rate,
    total_bases,
    walk_rate,
    woba,
    wraa,
)
from .constants import DEFAULT_FIP_CONSTANT, DEFAULT_WOBA_WEIGHTS, WobaWeights
from .fielding import (
    caught_stealing_percentage,
    fielding_percentage,
    range_factor_per_9,
    range_factor_per_game,
)
from .mlb import MLBAPIError, MLBClient
from .pitching import (
    bb_per_9,
    era,
    fip,
    game_score,
    h_per_9,
    hr_per_9,
    innings,
    innings_from_outs,
    k_bb_ratio,
    k_per_9,
    left_on_base_percentage,
    whip,
)

__version__ = "0.1.0"

__all__ = [
    # batting
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
    # pitching
    "innings",
    "innings_from_outs",
    "era",
    "whip",
    "fip",
    "k_per_9",
    "bb_per_9",
    "hr_per_9",
    "h_per_9",
    "k_bb_ratio",
    "left_on_base_percentage",
    "game_score",
    # fielding
    "fielding_percentage",
    "range_factor_per_game",
    "range_factor_per_9",
    "caught_stealing_percentage",
    # constants
    "WobaWeights",
    "DEFAULT_WOBA_WEIGHTS",
    "DEFAULT_FIP_CONSTANT",
    # MLB Stats API
    "MLBClient",
    "MLBAPIError",
    "__version__",
]
