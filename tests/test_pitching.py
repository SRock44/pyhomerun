import math
import unittest

import pyhomerun as bb


class TestInnings(unittest.TestCase):
    def test_box_score_notation(self):
        self.assertAlmostEqual(bb.innings(6.1), 6 + 1 / 3, places=9)
        self.assertAlmostEqual(bb.innings(6.2), 6 + 2 / 3, places=9)
        self.assertEqual(bb.innings(7.0), 7.0)

    def test_invalid_notation_rejected(self):
        with self.assertRaises(ValueError):
            bb.innings(6.5)

    def test_from_outs(self):
        self.assertAlmostEqual(bb.innings_from_outs(20), 6 + 2 / 3, places=9)
        self.assertEqual(bb.innings_from_outs(27), 9.0)


class TestEra(unittest.TestCase):
    def test_typical_season(self):
        self.assertAlmostEqual(bb.era(65, 180), 3.25, places=6)

    def test_partial_innings(self):
        # 3 ER in 6.2 (6 2/3) innings
        self.assertAlmostEqual(bb.era(3, bb.innings(6.2)), 4.05, places=2)

    def test_runs_without_outs_is_infinite(self):
        self.assertEqual(bb.era(2, 0), math.inf)

    def test_no_runs_no_innings(self):
        self.assertEqual(bb.era(0, 0), 0.0)


class TestWhip(unittest.TestCase):
    def test_typical_season(self):
        self.assertAlmostEqual(bb.whip(50, 160, 180), 210 / 180, places=6)

    def test_zero_innings(self):
        self.assertEqual(bb.whip(0, 0, 0), 0.0)


class TestFip(unittest.TestCase):
    def test_matches_formula(self):
        value = bb.fip(home_runs=18, walks=45, hit_by_pitch=5, strikeouts=190,
                       innings_pitched=180, constant=3.10)
        expected = (13 * 18 + 3 * 50 - 2 * 190) / 180 + 3.10
        self.assertAlmostEqual(value, expected, places=6)

    def test_uses_default_constant(self):
        value = bb.fip(0, 0, 0, 0, 9)
        self.assertAlmostEqual(value, bb.DEFAULT_FIP_CONSTANT, places=6)

    def test_zero_innings(self):
        self.assertEqual(bb.fip(1, 1, 1, 1, 0), 0.0)


class TestRelativeEra(unittest.TestCase):
    def test_era_plus_league_average_is_100(self):
        self.assertAlmostEqual(bb.era_plus(4.20, 4.20), 100.0, places=6)

    def test_era_plus_better_than_league(self):
        self.assertAlmostEqual(bb.era_plus(3.00, 4.20), 140.0, places=6)

    def test_era_plus_zero_era_is_infinite(self):
        self.assertEqual(bb.era_plus(0.0, 4.20), math.inf)

    def test_era_minus_better_than_league_is_below_100(self):
        self.assertAlmostEqual(bb.era_minus(3.00, 4.20), 100 * 3 / 4.2, places=6)

    def test_era_minus_zero_league(self):
        self.assertEqual(bb.era_minus(3.00, 0.0), 0.0)


class TestXfip(unittest.TestCase):
    def test_matches_formula(self):
        value = bb.xfip(fly_balls=200, walks=45, hit_by_pitch=5, strikeouts=190,
                        innings_pitched=180, league_hr_per_fb=0.105, constant=3.17)
        expected = (13 * (200 * 0.105) + 3 * 50 - 2 * 190) / 180 + 3.17
        self.assertAlmostEqual(value, expected, places=6)

    def test_zero_innings(self):
        self.assertEqual(bb.xfip(1, 1, 1, 1, 0), 0.0)


class TestPerNineRates(unittest.TestCase):
    def test_k_per_9(self):
        self.assertAlmostEqual(bb.k_per_9(190, 180), 9.5, places=6)

    def test_bb_per_9(self):
        self.assertAlmostEqual(bb.bb_per_9(45, 180), 2.25, places=6)

    def test_hr_per_9(self):
        self.assertAlmostEqual(bb.hr_per_9(18, 180), 0.9, places=6)

    def test_h_per_9(self):
        self.assertAlmostEqual(bb.h_per_9(160, 180), 8.0, places=6)

    def test_k_bb_ratio(self):
        self.assertAlmostEqual(bb.k_bb_ratio(190, 45), 190 / 45, places=6)

    def test_k_bb_ratio_no_walks(self):
        self.assertEqual(bb.k_bb_ratio(10, 0), math.inf)
        self.assertEqual(bb.k_bb_ratio(0, 0), 0.0)


class TestLobPercentage(unittest.TestCase):
    def test_typical_season(self):
        value = bb.left_on_base_percentage(hits=160, walks=50, hit_by_pitch=5,
                                           runs=70, home_runs=18)
        expected = (160 + 50 + 5 - 70) / (160 + 50 + 5 - 1.4 * 18)
        self.assertAlmostEqual(value, expected, places=6)

    def test_zero_denominator(self):
        self.assertEqual(bb.left_on_base_percentage(0, 0, 0, 0, 0), 0.0)


class TestGameScore(unittest.TestCase):
    def test_average_start_is_near_50(self):
        # 6 IP, 3 ER, 6 H, 5 K, 2 BB: 50 + 18 + 4 + 5 - 12 - 12 - 2 = 51
        value = bb.game_score(outs=18, strikeouts=5, hits=6, earned_runs=3,
                              unearned_runs=0, walks=2)
        self.assertEqual(value, 51)

    def test_dominant_complete_game(self):
        # 50 + 27 outs + 2*5 innings past the 4th + 10 K - 6 - 1
        value = bb.game_score(outs=27, strikeouts=10, hits=3, earned_runs=0,
                              unearned_runs=0, walks=1)
        self.assertEqual(value, 90)

    def test_no_inning_bonus_before_fifth(self):
        # 3 IP with nothing else: 50 + 9 outs, no completed-inning bonus
        self.assertEqual(bb.game_score(9, 0, 0, 0, 0, 0), 59)


if __name__ == "__main__":
    unittest.main()
