import unittest

from pyhomerun import BaseOutState, RE24_TABLE, run_expectancy, run_value


class TestRunExpectancy(unittest.TestCase):
    def test_bases_empty_no_outs(self):
        self.assertEqual(run_expectancy(BaseOutState()), 0.461)

    def test_bases_loaded_no_outs_is_highest(self):
        loaded = run_expectancy(BaseOutState(on_first=True, on_second=True, on_third=True))
        self.assertEqual(loaded, max(RE24_TABLE.values()))

    def test_three_outs_is_zero_regardless_of_bases(self):
        self.assertEqual(run_expectancy(BaseOutState(on_first=True, on_third=True, outs=3)), 0.0)

    def test_expectancy_decreases_with_outs(self):
        empty_0 = run_expectancy(BaseOutState(outs=0))
        empty_1 = run_expectancy(BaseOutState(outs=1))
        empty_2 = run_expectancy(BaseOutState(outs=2))
        self.assertGreater(empty_0, empty_1)
        self.assertGreater(empty_1, empty_2)

    def test_all_24_states_present(self):
        self.assertEqual(len(RE24_TABLE), 24)


class TestRunValue(unittest.TestCase):
    def test_walk_with_bases_empty(self):
        before = BaseOutState()
        after = BaseOutState(on_first=True)
        self.assertAlmostEqual(run_value(before, after, runs_scored=0), 0.370, places=3)

    def test_home_run_with_bases_loaded(self):
        before = BaseOutState(on_first=True, on_second=True, on_third=True)
        after = BaseOutState()
        value = run_value(before, after, runs_scored=4)
        self.assertAlmostEqual(value, 4 + 0.461 - 2.292, places=3)

    def test_inning_ending_double_play(self):
        before = BaseOutState(on_first=True, outs=2)
        after = BaseOutState(outs=3)
        value = run_value(before, after, runs_scored=0)
        self.assertAlmostEqual(value, -0.209, places=3)

    def test_custom_table(self):
        custom = dict(RE24_TABLE)
        custom[(False, False, False, 0)] = 1.0
        before = BaseOutState()
        after = BaseOutState()
        self.assertEqual(run_value(before, after, runs_scored=0, table=custom), 0.0)


if __name__ == "__main__":
    unittest.main()
