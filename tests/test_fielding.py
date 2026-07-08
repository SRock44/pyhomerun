import unittest

import pyhomerun as bb


class TestFieldingPercentage(unittest.TestCase):
    def test_typical_season(self):
        value = bb.fielding_percentage(putouts=250, assists=400, errors=10)
        self.assertAlmostEqual(value, 650 / 660, places=6)

    def test_perfect_fielder(self):
        self.assertEqual(bb.fielding_percentage(100, 100, 0), 1.0)

    def test_no_chances(self):
        self.assertEqual(bb.fielding_percentage(0, 0, 0), 0.0)


class TestRangeFactor(unittest.TestCase):
    def test_per_game(self):
        self.assertAlmostEqual(bb.range_factor_per_game(250, 400, 150), 650 / 150, places=6)

    def test_per_9(self):
        self.assertAlmostEqual(bb.range_factor_per_9(250, 400, 1300), 9 * 650 / 1300, places=6)

    def test_zero_denominators(self):
        self.assertEqual(bb.range_factor_per_game(1, 1, 0), 0.0)
        self.assertEqual(bb.range_factor_per_9(1, 1, 0), 0.0)


class TestCaughtStealing(unittest.TestCase):
    def test_typical_season(self):
        self.assertAlmostEqual(bb.caught_stealing_percentage(25, 60), 25 / 85, places=6)

    def test_no_attempts(self):
        self.assertEqual(bb.caught_stealing_percentage(0, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
