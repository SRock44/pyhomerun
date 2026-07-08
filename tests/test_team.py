import unittest

import pyhomerun as bb


class TestRunDifferential(unittest.TestCase):
    def test_positive_and_negative(self):
        self.assertEqual(bb.run_differential(800, 700), 100)
        self.assertEqual(bb.run_differential(650, 700), -50)


class TestPythagorean(unittest.TestCase):
    def test_even_runs_is_500(self):
        self.assertAlmostEqual(bb.pythagorean_expectation(700, 700), 0.5, places=6)

    def test_classic_exponent(self):
        expected = 800**2 / (800**2 + 700**2)
        self.assertAlmostEqual(bb.pythagorean_expectation(800, 700), expected, places=6)

    def test_custom_exponent(self):
        expected = 800**1.83 / (800**1.83 + 700**1.83)
        self.assertAlmostEqual(
            bb.pythagorean_expectation(800, 700, exponent=1.83), expected, places=6
        )

    def test_no_runs(self):
        self.assertEqual(bb.pythagorean_expectation(0, 0), 0.0)


class TestPythagenpat(unittest.TestCase):
    def test_exponent(self):
        expected = (1500 / 162) ** 0.287
        self.assertAlmostEqual(bb.pythagenpat_exponent(800, 700, 162), expected, places=6)

    def test_zero_games(self):
        self.assertEqual(bb.pythagenpat_exponent(800, 700, 0), 0.0)


class TestExpectedWins(unittest.TestCase):
    def test_uses_pythagenpat_by_default(self):
        exponent = bb.pythagenpat_exponent(800, 700, 162)
        expected = 162 * bb.pythagorean_expectation(800, 700, exponent)
        self.assertAlmostEqual(bb.expected_wins(800, 700, 162), expected, places=6)

    def test_explicit_exponent(self):
        expected = 162 * bb.pythagorean_expectation(800, 700, 2.0)
        self.assertAlmostEqual(bb.expected_wins(800, 700, 162, exponent=2.0), expected, places=6)

    def test_even_team_wins_half(self):
        self.assertAlmostEqual(bb.expected_wins(700, 700, 162), 81.0, places=6)


class TestMagicNumber(unittest.TestCase):
    def test_mid_season(self):
        self.assertEqual(bb.magic_number(leader_wins=90, second_place_losses=60), 13)

    def test_clinched_is_zero_or_less(self):
        self.assertLessEqual(bb.magic_number(leader_wins=100, second_place_losses=63), 0)


if __name__ == "__main__":
    unittest.main()
