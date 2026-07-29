import random
import unittest

from pyhomerun import (
    log5_win_probability,
    mlb_playoff_qualifiers,
    simulate_remaining_season,
    simulation_odds,
    top_n_qualifies,
    win_probability_from_win_pct,
)


class TestSimulateRemainingSeason(unittest.TestCase):
    def test_certain_outcome_is_deterministic(self):
        sims = simulate_remaining_season(
            {"A": 10, "B": 8},
            [("A", "B")],
            win_probability=lambda h, a: 1.0,
            n_simulations=5,
            rng=random.Random(0),
        )
        self.assertEqual(sims["A"], [11] * 5)
        self.assertEqual(sims["B"], [8] * 5)

    def test_certain_away_win(self):
        sims = simulate_remaining_season(
            {"A": 10, "B": 8},
            [("A", "B")],
            win_probability=lambda h, a: 0.0,
            n_simulations=5,
            rng=random.Random(0),
        )
        self.assertEqual(sims["A"], [10] * 5)
        self.assertEqual(sims["B"], [9] * 5)

    def test_no_remaining_games_returns_current_wins(self):
        sims = simulate_remaining_season(
            {"A": 10, "B": 8}, [], win_probability=lambda h, a: 0.5, n_simulations=4
        )
        self.assertEqual(sims["A"], [10] * 4)
        self.assertEqual(sims["B"], [8] * 4)

    def test_zero_simulations_returns_empty_lists(self):
        sims = simulate_remaining_season(
            {"A": 10}, [], win_probability=lambda h, a: 0.5, n_simulations=0
        )
        self.assertEqual(sims, {"A": []})

    def test_team_only_in_remaining_games_is_included(self):
        sims = simulate_remaining_season(
            {"A": 10},
            [("A", "C")],
            win_probability=lambda h, a: 1.0,
            n_simulations=2,
            rng=random.Random(0),
        )
        self.assertIn("C", sims)
        self.assertEqual(sims["C"], [0, 0])

    def test_win_probability_called_once_per_unique_game(self):
        calls = []

        def counting_probability(home, away):
            calls.append((home, away))
            return 0.5

        simulate_remaining_season(
            {"A": 0, "B": 0},
            [("A", "B"), ("A", "B"), ("B", "A")],
            win_probability=counting_probability,
            n_simulations=50,
            rng=random.Random(0),
        )
        self.assertEqual(len(calls), 3)

    def test_deterministic_with_seeded_rng(self):
        kwargs = dict(
            current_wins={"A": 50, "B": 50},
            remaining_games=[("A", "B"), ("B", "A"), ("A", "B")],
            win_probability=lambda h, a: 0.5,
            n_simulations=25,
        )
        first = simulate_remaining_season(rng=random.Random(7), **kwargs)
        second = simulate_remaining_season(rng=random.Random(7), **kwargs)
        self.assertEqual(first, second)

    def test_max_workers_is_reproducible_and_correctly_shaped(self):
        kwargs = dict(
            current_wins={"A": 50, "B": 50},
            remaining_games=[("A", "B"), ("B", "A"), ("A", "B")],
            win_probability=lambda h, a: 0.5,
            n_simulations=20,
        )
        first = simulate_remaining_season(rng=random.Random(3), max_workers=2, **kwargs)
        second = simulate_remaining_season(rng=random.Random(3), max_workers=2, **kwargs)
        self.assertEqual(first, second)
        self.assertEqual(len(first["A"]), 20)
        self.assertEqual(len(first["B"]), 20)
        # Both teams played all 3 remaining games between them, so each
        # simulated season adds exactly 3 wins across the pair.
        for a_wins, b_wins in zip(first["A"], first["B"]):
            self.assertEqual((a_wins - 50) + (b_wins - 50), 3)


class TestSimulationOdds(unittest.TestCase):
    def test_odds_sum_to_one_for_a_single_qualifier(self):
        simulated = {"A": [95, 90, 88], "B": [90, 92, 91]}
        odds = simulation_odds(simulated, top_n_qualifies(["A", "B"], 1))
        self.assertAlmostEqual(sum(odds.values()), 1.0, places=9)
        self.assertAlmostEqual(odds["A"], 1 / 3, places=9)
        self.assertAlmostEqual(odds["B"], 2 / 3, places=9)

    def test_everyone_qualifies_is_all_ones(self):
        simulated = {"A": [95, 90], "B": [90, 92]}
        odds = simulation_odds(simulated, top_n_qualifies(["A", "B"], 2))
        self.assertEqual(odds, {"A": 1.0, "B": 1.0})

    def test_empty_input(self):
        self.assertEqual(simulation_odds({}, top_n_qualifies([], 1)), {})

    def test_zero_simulations_is_zero_odds(self):
        odds = simulation_odds({"A": [], "B": []}, top_n_qualifies(["A", "B"], 1))
        self.assertEqual(odds, {"A": 0.0, "B": 0.0})


class TestTopNQualifies(unittest.TestCase):
    def test_returns_highest_n(self):
        qualifies = top_n_qualifies(["A", "B", "C"], 2)
        self.assertEqual(qualifies({"A": 90, "B": 95, "C": 80}), ["B", "A"])

    def test_missing_team_treated_as_zero(self):
        qualifies = top_n_qualifies(["A", "B"], 1)
        self.assertEqual(qualifies({"A": 90}), ["A"])


class TestMlbPlayoffQualifiers(unittest.TestCase):
    def test_division_winners_and_wildcards(self):
        divisions = {"East": ["A", "B"], "West": ["C", "D"]}
        qualifies = mlb_playoff_qualifiers(divisions, wildcard_spots=1)
        result = qualifies({"A": 90, "B": 80, "C": 85, "D": 70})
        self.assertEqual(result, {"A", "C", "B"})

    def test_wildcard_pool_excludes_division_winners(self):
        # A (East) and C (West) win their divisions by a landslide. If a
        # division winner could still occupy a wildcard slot, the single
        # wildcard would go to (already-qualified) A instead of D, and D
        # would incorrectly miss the playoffs.
        divisions = {"East": ["A", "B"], "West": ["C", "D"]}
        qualifies = mlb_playoff_qualifiers(divisions, wildcard_spots=1)
        result = qualifies({"A": 100, "B": 50, "C": 90, "D": 80})
        self.assertEqual(result, {"A", "C", "D"})


class TestWinProbabilityFromWinPct(unittest.TestCase):
    def test_matches_log5(self):
        win_probability = win_probability_from_win_pct({"A": 0.6, "B": 0.4})
        self.assertAlmostEqual(
            win_probability("A", "B"), log5_win_probability(0.6, 0.4), places=9
        )

    def test_missing_team_defaults_to_500(self):
        win_probability = win_probability_from_win_pct({"A": 0.6})
        self.assertAlmostEqual(win_probability("A", "B"), log5_win_probability(0.6, 0.5), places=9)


if __name__ == "__main__":
    unittest.main()
