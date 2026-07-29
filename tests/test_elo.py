import unittest

from pyhomerun import DEFAULT_RATING, EloRatings, expected_score, update_elo


class TestExpectedScore(unittest.TestCase):
    def test_equal_ratings_is_half(self):
        self.assertEqual(expected_score(1500, 1500), 0.5)

    def test_higher_rating_favored(self):
        self.assertGreater(expected_score(1600, 1500), 0.5)

    def test_symmetric(self):
        self.assertAlmostEqual(
            expected_score(1600, 1500), 1 - expected_score(1500, 1600), places=9
        )


class TestUpdateElo(unittest.TestCase):
    def test_winner_gains_loser_loses(self):
        new_a, new_b = update_elo(1500, 1500, score_a=1.0)
        self.assertGreater(new_a, 1500)
        self.assertLess(new_b, 1500)

    def test_zero_sum(self):
        new_a, new_b = update_elo(1550, 1480, score_a=0.0, k=10)
        self.assertAlmostEqual((new_a - 1550) + (new_b - 1480), 0.0, places=9)

    def test_upset_changes_rating_more_than_an_expected_result(self):
        upset_after, _ = update_elo(1400, 1600, score_a=1.0)  # underdog (A) wins: a surprise
        expected_after, _ = update_elo(1600, 1400, score_a=1.0)  # favorite (A) wins: expected
        self.assertGreater(upset_after - 1400, expected_after - 1600)


class TestEloRatings(unittest.TestCase):
    def test_unseen_team_starts_at_default(self):
        elo = EloRatings()
        self.assertEqual(elo.rating("Yankees"), DEFAULT_RATING)

    def test_record_game_updates_both_teams(self):
        elo = EloRatings()
        elo.record_game("Yankees", "Red Sox", home_score=5, away_score=3)
        self.assertGreater(elo.rating("Yankees"), DEFAULT_RATING)
        self.assertLess(elo.rating("Red Sox"), DEFAULT_RATING)

    def test_tie_raises(self):
        elo = EloRatings()
        with self.assertRaises(ValueError):
            elo.record_game("Yankees", "Red Sox", home_score=4, away_score=4)

    def test_home_field_advantage_helps_win_probability(self):
        elo = EloRatings()
        self.assertGreater(elo.win_probability("Yankees", "Red Sox"), 0.5)

    def test_no_home_field_advantage_is_even(self):
        elo = EloRatings(home_field_advantage=0.0)
        self.assertEqual(elo.win_probability("Yankees", "Red Sox"), 0.5)

    def test_ranked_sorted_descending(self):
        elo = EloRatings(initial={"A": 1600.0, "B": 1400.0, "C": 1500.0})
        self.assertEqual(elo.ranked(), [("A", 1600.0), ("C", 1500.0), ("B", 1400.0)])

    def test_ratings_snapshot_is_a_copy(self):
        elo = EloRatings(initial={"A": 1600.0})
        snapshot = elo.ratings()
        snapshot["A"] = 0.0
        self.assertEqual(elo.rating("A"), 1600.0)

    def test_regress_to_mean_pulls_toward_average(self):
        elo = EloRatings(initial={"A": 1700.0, "B": 1300.0})
        elo.regress_to_mean(factor=0.5)
        self.assertEqual(elo.rating("A"), 1600.0)
        self.assertEqual(elo.rating("B"), 1400.0)

    def test_repeated_wins_keep_increasing_rating(self):
        elo = EloRatings()
        ratings = []
        for _ in range(5):
            elo.record_game("Dodgers", "Rockies", home_score=4, away_score=1)
            ratings.append(elo.rating("Dodgers"))
        self.assertEqual(ratings, sorted(ratings))


if __name__ == "__main__":
    unittest.main()
