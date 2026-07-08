import unittest

import pyhomerun as bb


class TestBattingAverage(unittest.TestCase):
    def test_typical_season(self):
        self.assertAlmostEqual(bb.batting_average(200, 600), 0.3333, places=4)

    def test_zero_at_bats(self):
        self.assertEqual(bb.batting_average(0, 0), 0.0)


class TestOnBasePercentage(unittest.TestCase):
    def test_typical_season(self):
        obp = bb.on_base_percentage(hits=180, walks=70, hit_by_pitch=5, at_bats=550, sacrifice_flies=5)
        self.assertAlmostEqual(obp, 255 / 630, places=6)

    def test_zero_denominator(self):
        self.assertEqual(bb.on_base_percentage(0, 0, 0, 0), 0.0)


class TestSlugging(unittest.TestCase):
    def test_total_bases(self):
        # 150 hits: 30 2B, 5 3B, 25 HR -> 150 + 30 + 10 + 75
        self.assertEqual(bb.total_bases(150, 30, 5, 25), 265)

    def test_slugging(self):
        self.assertAlmostEqual(bb.slugging_percentage(265, 550), 265 / 550, places=6)

    def test_ops_is_sum(self):
        self.assertAlmostEqual(bb.ops(0.400, 0.550), 0.950, places=6)

    def test_iso(self):
        self.assertAlmostEqual(bb.isolated_power(0.550, 0.300), 0.250, places=6)


class TestOpsPlus(unittest.TestCase):
    def test_league_average_hitter_is_100(self):
        self.assertAlmostEqual(bb.ops_plus(0.320, 0.410, 0.320, 0.410), 100.0, places=6)

    def test_above_average(self):
        self.assertGreater(bb.ops_plus(0.400, 0.550, 0.320, 0.410), 100.0)

    def test_zero_league_rates(self):
        self.assertEqual(bb.ops_plus(0.4, 0.5, 0.0, 0.410), 0.0)


class TestBabip(unittest.TestCase):
    def test_typical_season(self):
        value = bb.babip(hits=160, home_runs=20, at_bats=550, strikeouts=120, sacrifice_flies=5)
        self.assertAlmostEqual(value, 140 / 415, places=6)

    def test_zero_balls_in_play(self):
        self.assertEqual(bb.babip(0, 0, 0, 0), 0.0)


class TestWoba(unittest.TestCase):
    def test_league_average_line_near_league_woba(self):
        # A roughly league-average batting line should give a wOBA near
        # the league constant baked into the default weights.
        value = bb.woba(
            walks=50, hit_by_pitch=5, singles=95, doubles=25, triples=2,
            home_runs=15, at_bats=540, sacrifice_flies=4,
        )
        self.assertAlmostEqual(value, bb.DEFAULT_WOBA_WEIGHTS.league_woba, delta=0.03)

    def test_intentional_walks_excluded(self):
        with_ibb = bb.woba(walks=60, hit_by_pitch=0, singles=100, doubles=20,
                           triples=0, home_runs=10, at_bats=500, intentional_walks=10)
        without = bb.woba(walks=50, hit_by_pitch=0, singles=100, doubles=20,
                          triples=0, home_runs=10, at_bats=500)
        self.assertAlmostEqual(with_ibb, without, places=9)

    def test_custom_weights(self):
        weights = bb.WobaWeights(bb=1, hbp=1, single=1, double=1, triple=1,
                                 home_run=1, league_woba=0.5, woba_scale=1.0)
        # With all weights 1 and no SF/HBP/IBB, wOBA reduces to (BB+H)/(AB+BB)
        value = bb.woba(walks=50, hit_by_pitch=0, singles=100, doubles=20,
                        triples=5, home_runs=25, at_bats=500, weights=weights)
        self.assertAlmostEqual(value, 200 / 550, places=6)

    def test_zero_denominator(self):
        self.assertEqual(bb.woba(0, 0, 0, 0, 0, 0, 0), 0.0)


class TestWraa(unittest.TestCase):
    def test_league_average_is_zero(self):
        weights = bb.DEFAULT_WOBA_WEIGHTS
        self.assertAlmostEqual(bb.wraa(weights.league_woba, 600), 0.0, places=6)

    def test_above_average_positive(self):
        self.assertGreater(bb.wraa(0.400, 600), 0.0)


class TestRatesAndCounts(unittest.TestCase):
    def test_plate_appearances(self):
        pa = bb.plate_appearances(at_bats=550, walks=70, hit_by_pitch=5,
                                  sacrifice_hits=2, sacrifice_flies=5)
        self.assertEqual(pa, 632)

    def test_walk_rate(self):
        self.assertAlmostEqual(bb.walk_rate(70, 632), 70 / 632, places=6)

    def test_strikeout_rate(self):
        self.assertAlmostEqual(bb.strikeout_rate(120, 632), 120 / 632, places=6)

    def test_stolen_base_percentage(self):
        self.assertAlmostEqual(bb.stolen_base_percentage(30, 10), 0.75, places=6)

    def test_stolen_base_percentage_no_attempts(self):
        self.assertEqual(bb.stolen_base_percentage(0, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
