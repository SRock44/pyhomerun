"""Stat-line dataclasses: raw counting stats in, every derived stat out.

:class:`BattingLine` and :class:`PitchingLine` bundle a player's counting
stats and expose the library's derived statistics as properties, so there
is no field-mapping boilerplate between the MLB Stats API and the math::

    mlb = MLBClient()
    player = mlb.search_players("Juan Soto")[0]
    split = mlb.player_stats(player["id"], group="hitting", season=2025)[0]

    line = BattingLine.from_mlb(split)
    line.woba()      # 0.4...
    line.slash()     # '0.266/0.396/0.525'

Lines support ``+`` for combining (two half-seasons, home/away splits,
career from year-by-year, ...).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Mapping

from . import batting as _batting
from . import pitching as _pitching
from .constants import DEFAULT_FIP_CONSTANT, DEFAULT_WOBA_WEIGHTS, WobaWeights

__all__ = ["BattingLine", "PitchingLine"]


def _stat_dict(split: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept either a full API split (with a ``stat`` key) or a bare stat dict."""
    inner = split.get("stat")
    return inner if isinstance(inner, Mapping) else split


def _count(stat: Mapping[str, Any], key: str, fallback_key: str = "") -> int:
    value = stat.get(key)
    if value is None and fallback_key:
        value = stat.get(fallback_key)
    return int(value or 0)


class _Addable:
    """Mixin: add two lines field-by-field to combine splits or seasons."""

    def __add__(self, other: Any) -> Any:
        if type(other) is not type(self):
            return NotImplemented
        merged = {
            field.name: getattr(self, field.name) + getattr(other, field.name)
            for field in dataclasses.fields(self)  # type: ignore[arg-type]
        }
        return type(self)(**merged)


@dataclass
class BattingLine(_Addable):
    """A batter's counting stats, with every derived stat one call away.

    All fields default to 0, so supply only what you have. ``walks`` is
    total walks, including intentional.

    >>> line = BattingLine(at_bats=550, hits=150, doubles=30, triples=5,
    ...                    home_runs=25, walks=70, hit_by_pitch=5,
    ...                    strikeouts=120, sacrifice_flies=5)
    >>> line.slash()
    '0.273/0.357/0.482'
    >>> round(line.woba(), 3)
    0.362
    >>> (line + line).home_runs  # combine two identical half-seasons
    50
    """

    at_bats: int = 0
    hits: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    walks: int = 0
    intentional_walks: int = 0
    hit_by_pitch: int = 0
    strikeouts: int = 0
    sacrifice_flies: int = 0
    sacrifice_hits: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0

    @classmethod
    def from_mlb(cls, split: Mapping[str, Any]) -> "BattingLine":
        """Build a line from an MLB Stats API hitting split.

        Accepts a split from ``MLBClient.player_stats(..., group="hitting")``
        directly, or its inner ``stat`` dict.
        """
        stat = _stat_dict(split)
        return cls(
            at_bats=_count(stat, "atBats"),
            hits=_count(stat, "hits"),
            doubles=_count(stat, "doubles"),
            triples=_count(stat, "triples"),
            home_runs=_count(stat, "homeRuns"),
            walks=_count(stat, "baseOnBalls"),
            intentional_walks=_count(stat, "intentionalWalks"),
            hit_by_pitch=_count(stat, "hitByPitch"),
            strikeouts=_count(stat, "strikeOuts"),
            sacrifice_flies=_count(stat, "sacFlies"),
            sacrifice_hits=_count(stat, "sacBunts"),
            stolen_bases=_count(stat, "stolenBases"),
            caught_stealing=_count(stat, "caughtStealing"),
        )

    # -- derived counts ------------------------------------------------

    @property
    def singles(self) -> int:
        return self.hits - self.doubles - self.triples - self.home_runs

    @property
    def total_bases(self) -> int:
        return _batting.total_bases(self.hits, self.doubles, self.triples, self.home_runs)

    @property
    def plate_appearances(self) -> int:
        return _batting.plate_appearances(
            self.at_bats, self.walks, self.hit_by_pitch,
            self.sacrifice_hits, self.sacrifice_flies,
        )

    # -- rate stats ------------------------------------------------------

    @property
    def avg(self) -> float:
        return _batting.batting_average(self.hits, self.at_bats)

    @property
    def obp(self) -> float:
        return _batting.on_base_percentage(
            self.hits, self.walks, self.hit_by_pitch, self.at_bats, self.sacrifice_flies
        )

    @property
    def slg(self) -> float:
        return _batting.slugging_percentage(self.total_bases, self.at_bats)

    @property
    def ops(self) -> float:
        return _batting.ops(self.obp, self.slg)

    @property
    def iso(self) -> float:
        return _batting.isolated_power(self.slg, self.avg)

    @property
    def babip(self) -> float:
        return _batting.babip(
            self.hits, self.home_runs, self.at_bats, self.strikeouts, self.sacrifice_flies
        )

    @property
    def walk_rate(self) -> float:
        return _batting.walk_rate(self.walks, self.plate_appearances)

    @property
    def strikeout_rate(self) -> float:
        return _batting.strikeout_rate(self.strikeouts, self.plate_appearances)

    @property
    def stolen_base_percentage(self) -> float:
        return _batting.stolen_base_percentage(self.stolen_bases, self.caught_stealing)

    # -- linear-weight stats (take optional league constants) -----------

    def woba(self, weights: WobaWeights = DEFAULT_WOBA_WEIGHTS) -> float:
        return _batting.woba(
            self.walks, self.hit_by_pitch, self.singles, self.doubles,
            self.triples, self.home_runs, self.at_bats,
            self.intentional_walks, self.sacrifice_flies, weights,
        )

    def wraa(self, weights: WobaWeights = DEFAULT_WOBA_WEIGHTS) -> float:
        return _batting.wraa(self.woba(weights), self.plate_appearances, weights)

    def wrc(self, weights: WobaWeights = DEFAULT_WOBA_WEIGHTS) -> float:
        return _batting.wrc(self.woba(weights), self.plate_appearances, weights)

    def wrc_plus(
        self,
        park_factor: float = 1.0,
        weights: WobaWeights = DEFAULT_WOBA_WEIGHTS,
    ) -> float:
        return _batting.wrc_plus(self.woba(weights), park_factor, weights)

    def runs_created(self) -> float:
        return _batting.runs_created(self.hits, self.walks, self.total_bases, self.at_bats)

    def slash(self) -> str:
        """The classic AVG/OBP/SLG slash line as a string."""
        return f"{self.avg:.3f}/{self.obp:.3f}/{self.slg:.3f}"


@dataclass
class PitchingLine(_Addable):
    """A pitcher's counting stats, with every derived stat one call away.

    Innings are stored as ``outs`` so lines add together exactly; use the
    :attr:`innings_pitched` property to read back true innings.

    >>> line = PitchingLine(outs=540, hits=160, runs=75, earned_runs=65,
    ...                     walks=50, strikeouts=190, home_runs=18,
    ...                     hit_by_pitch=5)
    >>> line.innings_pitched
    180.0
    >>> round(line.era, 2)
    3.25
    >>> round(line.fip(), 2)
    3.28
    """

    outs: int = 0
    hits: int = 0
    runs: int = 0
    earned_runs: int = 0
    walks: int = 0
    intentional_walks: int = 0
    strikeouts: int = 0
    home_runs: int = 0
    hit_by_pitch: int = 0
    batters_faced: int = 0

    @classmethod
    def from_mlb(cls, split: Mapping[str, Any]) -> "PitchingLine":
        """Build a line from an MLB Stats API pitching split.

        Accepts a split from ``MLBClient.player_stats(..., group="pitching")``
        directly, or its inner ``stat`` dict. Prefers the API's ``outs``
        field; falls back to parsing box-score ``inningsPitched`` (e.g.
        ``"180.2"``).
        """
        stat = _stat_dict(split)
        outs = stat.get("outs")
        if outs is None:
            outs = round(_pitching.innings(float(stat.get("inningsPitched", 0) or 0)) * 3)
        return cls(
            outs=int(outs),
            hits=_count(stat, "hits"),
            runs=_count(stat, "runs"),
            earned_runs=_count(stat, "earnedRuns"),
            walks=_count(stat, "baseOnBalls"),
            intentional_walks=_count(stat, "intentionalWalks"),
            strikeouts=_count(stat, "strikeOuts"),
            home_runs=_count(stat, "homeRuns"),
            hit_by_pitch=_count(stat, "hitBatsmen", "hitByPitch"),
            batters_faced=_count(stat, "battersFaced"),
        )

    @property
    def innings_pitched(self) -> float:
        """True innings pitched (6 2/3, not the box-score 6.2)."""
        return _pitching.innings_from_outs(self.outs)

    # -- rate stats ------------------------------------------------------

    @property
    def era(self) -> float:
        return _pitching.era(self.earned_runs, self.innings_pitched)

    @property
    def whip(self) -> float:
        return _pitching.whip(self.walks, self.hits, self.innings_pitched)

    @property
    def k_per_9(self) -> float:
        return _pitching.k_per_9(self.strikeouts, self.innings_pitched)

    @property
    def bb_per_9(self) -> float:
        return _pitching.bb_per_9(self.walks, self.innings_pitched)

    @property
    def hr_per_9(self) -> float:
        return _pitching.hr_per_9(self.home_runs, self.innings_pitched)

    @property
    def h_per_9(self) -> float:
        return _pitching.h_per_9(self.hits, self.innings_pitched)

    @property
    def k_bb_ratio(self) -> float:
        return _pitching.k_bb_ratio(self.strikeouts, self.walks)

    @property
    def strikeout_rate(self) -> float:
        """K% — strikeouts per batter faced (0.0 if batters_faced unset)."""
        return _batting.strikeout_rate(self.strikeouts, self.batters_faced)

    @property
    def walk_rate(self) -> float:
        """BB% — walks per batter faced (0.0 if batters_faced unset)."""
        return _batting.walk_rate(self.walks, self.batters_faced)

    @property
    def left_on_base_percentage(self) -> float:
        return _pitching.left_on_base_percentage(
            self.hits, self.walks, self.hit_by_pitch, self.runs, self.home_runs
        )

    # -- stats that take optional league constants ----------------------

    def fip(self, constant: float = DEFAULT_FIP_CONSTANT) -> float:
        return _pitching.fip(
            self.home_runs, self.walks, self.hit_by_pitch,
            self.strikeouts, self.innings_pitched, constant,
        )

    def era_plus(self, league_era: float, park_factor: float = 1.0) -> float:
        return _pitching.era_plus(self.era, league_era, park_factor)

    def era_minus(self, league_era: float, park_factor: float = 1.0) -> float:
        return _pitching.era_minus(self.era, league_era, park_factor)
