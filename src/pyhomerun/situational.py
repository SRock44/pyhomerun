"""Run-expectancy tables and situational run-value helpers.

Ships the published 24 base-out-state run-expectancy (RE24) matrix as
data — the average number of runs a team scores for the rest of the
inning, indexed by which bases are occupied and how many outs there
are — plus helpers to compute the run value of a play as the change in
expectancy across the play, plus any runs that scored on it.

The table is the well-known 1999-2002 MLB average matrix from Tom Tango,
Mitchel Lichtman, and Andrew Dolphin, *The Book: Playing the Percentages
in Baseball* (2007). It's directionally right for any modern season; for
an exact per-season matrix, build your own ``{BaseOutState: float}``
mapping from play-by-play data and pass it to these functions instead of
the default.

Example::

    from pyhomerun import BaseOutState, run_expectancy, run_value

    # Runner on first, nobody out.
    run_expectancy(BaseOutState(on_first=True))   # 0.831

    # A walk with the bases empty and nobody out: how many runs was that worth?
    before = BaseOutState()
    after = BaseOutState(on_first=True)
    run_value(before, after, runs_scored=0)       # 0.37
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Tuple

__all__ = ["BaseOutState", "RE24_TABLE", "run_expectancy", "run_value"]


@dataclass(frozen=True)
class BaseOutState:
    """Which bases are occupied and how many outs there are.

    Three outs ends the inning, so :func:`run_expectancy` treats any
    state with ``outs >= 3`` as worth 0.0 regardless of the bases.
    """

    on_first: bool = False
    on_second: bool = False
    on_third: bool = False
    outs: int = 0

    def _key(self) -> Tuple[bool, bool, bool, int]:
        return (self.on_first, self.on_second, self.on_third, self.outs)


#: Average runs scored for the rest of the inning, by base-out state.
#: 1999-2002 MLB average, from Tango/Lichtman/Dolphin, *The Book* (2007).
RE24_TABLE: Dict[Tuple[bool, bool, bool, int], float] = {
    (False, False, False, 0): 0.461,
    (True, False, False, 0): 0.831,
    (False, True, False, 0): 1.068,
    (False, False, True, 0): 1.277,
    (True, True, False, 0): 1.373,
    (True, False, True, 0): 1.662,
    (False, True, True, 0): 1.964,
    (True, True, True, 0): 2.292,
    (False, False, False, 1): 0.243,
    (True, False, False, 1): 0.489,
    (False, True, False, 1): 0.644,
    (False, False, True, 1): 0.897,
    (True, True, False, 1): 0.876,
    (True, False, True, 1): 1.135,
    (False, True, True, 1): 1.376,
    (True, True, True, 1): 1.541,
    (False, False, False, 2): 0.095,
    (True, False, False, 2): 0.209,
    (False, True, False, 2): 0.305,
    (False, False, True, 2): 0.377,
    (True, True, False, 2): 0.423,
    (True, False, True, 2): 0.478,
    (False, True, True, 2): 0.570,
    (True, True, True, 2): 0.736,
}


def run_expectancy(
    state: BaseOutState,
    table: Mapping[Tuple[bool, bool, bool, int], float] = RE24_TABLE,
) -> float:
    """Average runs scored for the rest of the inning from ``state``.

    >>> run_expectancy(BaseOutState())  # bases empty, nobody out
    0.461
    >>> run_expectancy(BaseOutState(on_second=True, on_third=True, outs=1))
    1.376
    >>> run_expectancy(BaseOutState(outs=3))  # inning over
    0.0
    """
    if state.outs >= 3:
        return 0.0
    return table[state._key()]


def run_value(
    before: BaseOutState,
    after: BaseOutState,
    runs_scored: int,
    table: Mapping[Tuple[bool, bool, bool, int], float] = RE24_TABLE,
) -> float:
    """Run value of a play: the change in expectancy, plus runs it scored.

    ``after`` is the base-out state once the play is over (an out that
    ends the inning should be given ``outs=3``, whatever the bases).

    >>> before = BaseOutState()                        # bases empty, 0 out
    >>> after = BaseOutState(on_first=True)             # walk
    >>> round(run_value(before, after, runs_scored=0), 3)
    0.37
    >>> before = BaseOutState(on_third=True, outs=1)     # runner on 3rd, 1 out
    >>> after = BaseOutState(outs=2)                     # sac fly scores the run
    >>> round(run_value(before, after, runs_scored=1), 3)
    0.198
    """
    return run_expectancy(after, table) + runs_scored - run_expectancy(before, table)
