"""Monte Carlo season simulation and playoff-odds estimation.

Takes a season's remaining schedule plus a way to estimate any single
game's odds -- :class:`~pyhomerun.EloRatings` or plain win percentages via
:func:`win_probability_from_win_pct` both work -- and plays the rest of the
season out ``n_simulations`` times to see how often each team ends up
where you care about (a division title, a wild card, any arbitrary
"top N of this group" question via :func:`top_n_qualifies` or the
MLB-shaped :func:`mlb_playoff_qualifiers`). No dependency needed for any
of it: :mod:`random` and a loop is the whole engine, same as
:mod:`pyhomerun.elo`.

Example::

    from pyhomerun import EloRatings, simulate_remaining_season, simulation_odds, top_n_qualifies

    elo = EloRatings()
    # ... elo.record_game(...) for every game played so far ...

    remaining = [("Yankees", "Red Sox"), ("Red Sox", "Yankees")]
    current_wins = {"Yankees": 88, "Red Sox": 84}
    sims = simulate_remaining_season(current_wins, remaining, elo.win_probability)
    odds = simulation_odds(sims, top_n_qualifies(current_wins, 1))
    odds["Yankees"]  # fraction of simulations the Yankees finished with the most wins

For real MLB data, ``current_wins`` comes from :meth:`~pyhomerun.MLBClient.standings`
and ``remaining`` from the not-yet-``"Final"`` games in
:meth:`~pyhomerun.MLBClient.schedule` (see ``pyhomerun playoff-odds`` in the CLI
for a full worked example).

Performance: the hot loop is what actually gets simulated, so it's built
to stay fast without an external dependency:

* ``win_probability(home, away)`` is evaluated once per *unique remaining
  game*, not once per game per simulation -- a season with 500 games left
  and 10,000 simulations calls it 500 times, not 5,000,000.
* The per-simulation inner loop works over integer team indices into
  plain ``list``s, not team-name dict lookups -- list indexing plus one
  ``int`` add per game is about as fast as pure Python gets.
* For very large workloads (a full 30-team season pulled early, tens of
  thousands of simulations), pass ``max_workers`` to spread simulations
  across a process pool (:mod:`concurrent.futures`, standard library) --
  the same pattern :meth:`~pyhomerun.MLBClient.player_stats_bulk` uses for
  concurrent network calls, applied here to CPU-bound simulation instead.
"""

from __future__ import annotations

import random
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .team import log5_win_probability

__all__ = [
    "simulate_remaining_season",
    "simulation_odds",
    "top_n_qualifies",
    "mlb_playoff_qualifiers",
    "win_probability_from_win_pct",
]

#: ``(home, away) -> P(home wins)``.
WinProbability = Callable[[str, str], float]
#: A snapshot of one simulation's final win totals -> the teams that qualify.
Qualifies = Callable[[Dict[str, int]], Iterable[str]]


def _split(total: int, parts: int) -> List[int]:
    """``total`` split into up to ``parts`` positive, near-equal chunk sizes."""
    parts = min(parts, total) or 1
    base, extra = divmod(total, parts)
    return [base + (1 if i < extra else 0) for i in range(parts)]


def _simulate_chunk(
    base_wins: List[int],
    game_probs: List[Tuple[int, int, float]],
    n_teams: int,
    count: int,
    seed: int,
) -> List[List[int]]:
    """Run ``count`` simulations with a private RNG seeded from ``seed``.

    Module-level, not a closure, so it stays picklable for
    ``ProcessPoolExecutor`` under Windows's spawn-based process start (as
    well as fork/forkserver). Returns one list of final win totals per
    team, indexed the same way as ``base_wins``/``game_probs``.
    """
    rand = random.Random(seed).random
    columns = [[0] * count for _ in range(n_teams)]
    for sim in range(count):
        wins = list(base_wins)
        for home_i, away_i, prob in game_probs:
            if rand() < prob:
                wins[home_i] += 1
            else:
                wins[away_i] += 1
        for i in range(n_teams):
            columns[i][sim] = wins[i]
    return columns


def simulate_remaining_season(
    current_wins: Mapping[str, int],
    remaining_games: Iterable[Tuple[str, str]],
    win_probability: WinProbability,
    n_simulations: int = 10000,
    rng: Optional[random.Random] = None,
    max_workers: Optional[int] = None,
) -> Dict[str, List[int]]:
    """Play out the rest of a season ``n_simulations`` times.

    Args:
        current_wins: Each team's win total so far.
        remaining_games: Every game left to play, as ``(home, away)``
            pairs of team names. A team can appear here without an entry
            in ``current_wins`` (treated as 0 wins so far).
        win_probability: ``(home, away) -> P(home wins)`` for one game.
            :meth:`~pyhomerun.EloRatings.win_probability` and
            :func:`win_probability_from_win_pct` both fit this signature.
        n_simulations: How many times to replay the remaining schedule.
        rng: A seeded :class:`random.Random` for reproducible results;
            omit for a fresh, unseeded one.
        max_workers: If given and greater than 1, spread simulations
            across a :class:`~concurrent.futures.ProcessPoolExecutor` of
            this many worker processes instead of running sequentially.
            Only worth it for large workloads -- process startup has a
            fixed cost that a small simulation won't recoup.

    Returns:
        ``{team: [final_win_total, ...]}``, one entry per simulation, in
        the same order for every team -- index ``i`` across every team's
        list describes one consistent simulated season.

    >>> remaining = [("A", "B")]
    >>> sims = simulate_remaining_season(
    ...     {"A": 10, "B": 8}, remaining, lambda h, a: 1.0, n_simulations=3, rng=random.Random(0)
    ... )
    >>> sims["A"]
    [11, 11, 11]
    >>> sims["B"]
    [8, 8, 8]
    """
    rng = rng or random.Random()
    remaining = list(remaining_games)

    teams = list(current_wins)
    seen = set(teams)
    for home, away in remaining:
        if home not in seen:
            seen.add(home)
            teams.append(home)
        if away not in seen:
            seen.add(away)
            teams.append(away)

    index = {team: i for i, team in enumerate(teams)}
    base_wins = [current_wins.get(team, 0) for team in teams]
    n_teams = len(teams)

    # Each unique game's probability is computed once here, not once per
    # simulation -- see the module docstring's Performance note.
    game_probs = [
        (index[home], index[away], win_probability(home, away)) for home, away in remaining
    ]

    if not n_simulations:
        return {team: [] for team in teams}

    if max_workers and max_workers > 1:
        chunk_sizes = _split(n_simulations, max_workers)
        seeds = [rng.randrange(2**32) for _ in chunk_sizes]
        columns = [[] for _ in range(n_teams)]  # type: List[List[int]]
        with ProcessPoolExecutor(max_workers=len(chunk_sizes)) as pool:
            for chunk in pool.map(
                _simulate_chunk,
                repeat(base_wins),
                repeat(game_probs),
                repeat(n_teams),
                chunk_sizes,
                seeds,
            ):
                for i in range(n_teams):
                    columns[i].extend(chunk[i])
    else:
        columns = _simulate_chunk(base_wins, game_probs, n_teams, n_simulations, rng.randrange(2**32))

    return {team: columns[i] for team, i in index.items()}


def simulation_odds(
    simulated_wins: Mapping[str, Sequence[int]],
    qualifies: Qualifies,
) -> Dict[str, float]:
    """Fraction of simulations in which each team qualifies.

    Args:
        simulated_wins: :func:`simulate_remaining_season`'s return value
            (or anything shaped like it -- same win totals, aligned by
            index across every team).
        qualifies: Given one simulation's ``{team: final_wins}`` snapshot,
            returns which teams qualify in that simulation.
            :func:`top_n_qualifies` and :func:`mlb_playoff_qualifiers`
            both build one of these.

    Returns:
        ``{team: odds}``, ``odds`` in ``[0.0, 1.0]``.

    >>> simulated = {"A": [95, 90, 88], "B": [90, 92, 91]}
    >>> odds = simulation_odds(simulated, top_n_qualifies(["A", "B"], 1))
    >>> round(odds["A"], 3)
    0.333
    >>> round(odds["B"], 3)
    0.667
    """
    teams = list(simulated_wins)
    if not teams:
        return {}
    n = len(simulated_wins[teams[0]])
    if not n:
        return {team: 0.0 for team in teams}

    counts = {team: 0 for team in teams}
    for i in range(n):
        snapshot = {team: simulated_wins[team][i] for team in teams}
        for team in qualifies(snapshot):
            if team in counts:
                counts[team] += 1
    return {team: counts[team] / n for team in teams}


def top_n_qualifies(teams: Iterable[str], n: int) -> Qualifies:
    """``qualifies`` factory: the ``n`` teams (from ``teams``) with the most wins.

    Ties are broken arbitrarily (by :func:`sorted`'s stable order) -- real
    tiebreaker games aren't modeled.

    >>> qualifies = top_n_qualifies(["A", "B", "C"], 2)
    >>> qualifies({"A": 90, "B": 95, "C": 80})
    ['B', 'A']
    """
    pool = list(teams)

    def qualifies(final_wins: Dict[str, int]) -> List[str]:
        ranked = sorted(pool, key=lambda team: final_wins.get(team, 0), reverse=True)
        return ranked[:n]

    return qualifies


def mlb_playoff_qualifiers(
    divisions: Mapping[str, Iterable[str]],
    wildcard_spots: int = 3,
) -> Callable[[Dict[str, int]], Set[str]]:
    """``qualifies`` factory shaped like MLB's real playoff format.

    Each division's win-total leader qualifies as the division winner;
    the ``wildcard_spots`` teams with the next-most wins, pooled across
    every division given here (division winners excluded), qualify as
    wild cards. Pass every division in one league (or both leagues, if
    you don't need to distinguish AL/NL playoff odds) as ``divisions``.

    >>> divisions = {"East": ["A", "B"], "West": ["C", "D"]}
    >>> qualifies = mlb_playoff_qualifiers(divisions, wildcard_spots=1)
    >>> sorted(qualifies({"A": 90, "B": 80, "C": 85, "D": 70}))
    ['A', 'B', 'C']
    """
    division_pools = {name: list(teams) for name, teams in divisions.items()}

    def qualifies(final_wins: Dict[str, int]) -> Set[str]:
        winners = {
            max(teams, key=lambda team: final_wins.get(team, 0))
            for teams in division_pools.values()
            if teams
        }
        pool = [team for teams in division_pools.values() for team in teams if team not in winners]
        wildcards = sorted(pool, key=lambda team: final_wins.get(team, 0), reverse=True)
        return winners | set(wildcards[:wildcard_spots])

    return qualifies


def win_probability_from_win_pct(win_pct: Mapping[str, float]) -> WinProbability:
    """Adapter: a ``win_probability`` callable built from plain winning percentages.

    Uses :func:`~pyhomerun.log5_win_probability`. A team missing from
    ``win_pct`` is treated as exactly 0.500 -- the log5-neutral value.
    This is the no-:class:`~pyhomerun.EloRatings`-required path: build
    ``win_pct`` from :func:`~pyhomerun.pythagorean_expectation` (or raw
    ``wins / games``) and go straight to :func:`simulate_remaining_season`.

    >>> win_probability = win_probability_from_win_pct({"A": 0.600, "B": 0.400})
    >>> round(win_probability("A", "B"), 3)
    0.692
    """

    def win_probability(home: str, away: str) -> float:
        return log5_win_probability(win_pct.get(home, 0.5), win_pct.get(away, 0.5))

    return win_probability
