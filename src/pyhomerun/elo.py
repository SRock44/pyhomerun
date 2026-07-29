"""Self-updating Elo team power ratings.

A team's Elo rating is a single number that summarizes its strength
relative to every other team, updated one game at a time from the
result alone (:func:`update_elo`) -- no schedule-strength bookkeeping,
no simultaneous system of equations to solve. It only needs
standard-library arithmetic (``**`` for the logistic curve), which makes
it a natural, zero-dependency complement to the classic
:func:`~pyhomerun.pythagorean_expectation`/:func:`~pyhomerun.log5_win_probability`
pair in :mod:`pyhomerun.team` -- and a ready-made ``win_probability``
input for :func:`~pyhomerun.simulate_remaining_season`.

Example::

    from pyhomerun import EloRatings

    elo = EloRatings()
    elo.record_game("Yankees", "Red Sox", home_score=5, away_score=3)
    elo.record_game("Red Sox", "Yankees", home_score=6, away_score=2)
    elo.ranked()  # [("Red Sox", ~1500.9), ("Yankees", ~1499.1)]

Ratings start at :data:`DEFAULT_RATING` (1500) for any team not seen yet,
so there's no setup step -- just start calling :meth:`EloRatings.record_game`
as results come in.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Tuple

__all__ = [
    "DEFAULT_RATING",
    "DEFAULT_K",
    "DEFAULT_HOME_FIELD_ADVANTAGE",
    "expected_score",
    "update_elo",
    "EloRatings",
]

#: Starting rating for a team with no game history yet.
DEFAULT_RATING = 1500.0

#: Points transferred between two teams' ratings per game, scaled by how
#: surprising the result was. Kept conservative (relative to e.g. chess's
#: usual 20-32) because a 162-game MLB season generates a lot of games to
#: converge over, and single-game variance in baseball is high -- a huge
#: K would make ratings swing wildly on noise rather than signal.
DEFAULT_K = 4.0

#: Elo points added to the home team's rating before computing a win
#: probability, reflecting the modest-but-real home-field edge in MLB.
DEFAULT_HOME_FIELD_ADVANTAGE = 24.0


def expected_score(rating_a: float, rating_b: float) -> float:
    """Probability team A beats team B, from their current ratings alone.

    This is the standard Elo logistic curve; it does not apply a
    home-field adjustment -- add that to a rating yourself before calling,
    or use :meth:`EloRatings.win_probability`.

    >>> expected_score(1500, 1500)
    0.5
    >>> round(expected_score(1600, 1500), 3)
    0.64
    """
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def update_elo(
    rating_a: float, rating_b: float, score_a: float, k: float = DEFAULT_K
) -> Tuple[float, float]:
    """New (rating_a, rating_b) after a game between them.

    Args:
        rating_a: Team A's rating before the game.
        rating_b: Team B's rating before the game.
        score_a: ``1.0`` if A won, ``0.0`` if A lost (baseball games don't
            end in ties, so there's no draw value).
        k: How many rating points change hands for a maximally surprising
            result; see :data:`DEFAULT_K`.

    >>> update_elo(1500, 1500, score_a=1.0)
    (1502.0, 1498.0)
    """
    expected_a = expected_score(rating_a, rating_b)
    change = k * (score_a - expected_a)
    return rating_a + change, rating_b - change


class EloRatings:
    """A live set of team Elo ratings, updated game by game.

    Args:
        initial: Starting ratings for teams you already have a prior for
            (e.g. carried over from last season via :meth:`regress_to_mean`).
            Any team not present here starts at :data:`DEFAULT_RATING` the
            first time it's referenced.
        k: See :data:`DEFAULT_K`.
        home_field_advantage: See :data:`DEFAULT_HOME_FIELD_ADVANTAGE`.
    """

    def __init__(
        self,
        initial: Optional[Mapping[str, float]] = None,
        k: float = DEFAULT_K,
        home_field_advantage: float = DEFAULT_HOME_FIELD_ADVANTAGE,
    ) -> None:
        self.k = k
        self.home_field_advantage = home_field_advantage
        self._ratings: Dict[str, float] = dict(initial) if initial else {}

    def rating(self, team: str) -> float:
        """A team's current rating (:data:`DEFAULT_RATING` if unseen)."""
        return self._ratings.get(team, DEFAULT_RATING)

    def win_probability(self, home: str, away: str) -> float:
        """Probability the home team beats the away team, including home-field.

        >>> elo = EloRatings()
        >>> round(elo.win_probability("Yankees", "Red Sox"), 3)
        0.534
        """
        return expected_score(
            self.rating(home) + self.home_field_advantage, self.rating(away)
        )

    def record_game(self, home: str, away: str, home_score: int, away_score: int) -> None:
        """Update both teams' ratings from a final score.

        Raises:
            ValueError: ``home_score == away_score`` -- baseball games
                are always decisive, so a tie means bad input, not a draw.

        >>> elo = EloRatings()
        >>> elo.record_game("Yankees", "Red Sox", home_score=5, away_score=3)
        >>> round(elo.rating("Yankees"), 2)
        1501.86
        >>> round(elo.rating("Red Sox"), 2)
        1498.14
        """
        if home_score == away_score:
            raise ValueError("record_game() requires a decisive result, got a tie")
        home_won = 1.0 if home_score > away_score else 0.0
        home_rating = self.rating(home) + self.home_field_advantage
        away_rating = self.rating(away)
        new_home, new_away = update_elo(home_rating, away_rating, home_won, self.k)
        self._ratings[home] = new_home - self.home_field_advantage
        self._ratings[away] = new_away

    def regress_to_mean(self, factor: float = 1.0 / 3.0, mean: float = DEFAULT_RATING) -> None:
        """Pull every known team's rating partway back toward ``mean``.

        Call this once between seasons: a team's talent level doesn't
        fully carry over (rosters turn over, players age), so most public
        Elo systems regress a third to a half of the way back to average
        rather than starting the new season exactly where the last one
        ended.

        >>> elo = EloRatings(initial={"Yankees": 1600.0})
        >>> elo.regress_to_mean()
        >>> round(elo.rating("Yankees"), 1)
        1566.7
        """
        for team, rating in self._ratings.items():
            self._ratings[team] = rating + (mean - rating) * factor

    def ranked(self) -> List[Tuple[str, float]]:
        """Every known team and its rating, strongest first."""
        return sorted(self._ratings.items(), key=lambda item: item[1], reverse=True)

    def ratings(self) -> Dict[str, float]:
        """A plain ``{team: rating}`` snapshot (safe to mutate)."""
        return dict(self._ratings)
