import unittest

import pyhomerun as bb
from pyhomerun import BattingLine, PitchingLine

# A realistic API hitting split, as returned by MLBClient.player_stats().
HITTING_SPLIT = {
    "season": "2025",
    "stat": {
        "atBats": 550, "hits": 150, "doubles": 30, "triples": 5,
        "homeRuns": 25, "baseOnBalls": 70, "intentionalWalks": 5,
        "hitByPitch": 5, "strikeOuts": 120, "sacFlies": 5, "sacBunts": 2,
        "stolenBases": 30, "caughtStealing": 10,
        "avg": ".273", "irrelevantKey": "ignored",
    },
}

PITCHING_SPLIT = {
    "season": "2025",
    "stat": {
        "outs": 540, "inningsPitched": "180.0", "hits": 160, "runs": 75,
        "earnedRuns": 65, "baseOnBalls": 50, "intentionalWalks": 2,
        "strikeOuts": 190, "homeRuns": 18, "hitBatsmen": 5,
        "battersFaced": 740,
    },
}


class TestBattingLine(unittest.TestCase):
    def setUp(self):
        self.line = BattingLine(
            at_bats=550, hits=150, doubles=30, triples=5, home_runs=25,
            walks=70, intentional_walks=5, hit_by_pitch=5, strikeouts=120,
            sacrifice_flies=5, sacrifice_hits=2, stolen_bases=30, caught_stealing=10,
        )

    def test_derived_counts(self):
        self.assertEqual(self.line.singles, 90)
        self.assertEqual(self.line.total_bases, 265)
        self.assertEqual(self.line.plate_appearances, 632)

    def test_properties_match_module_functions(self):
        self.assertEqual(self.line.avg, bb.batting_average(150, 550))
        self.assertEqual(self.line.obp, bb.on_base_percentage(150, 70, 5, 550, 5))
        self.assertEqual(self.line.slg, bb.slugging_percentage(265, 550))
        self.assertEqual(self.line.ops, self.line.obp + self.line.slg)
        self.assertEqual(self.line.babip, bb.babip(150, 25, 550, 120, 5))
        self.assertEqual(self.line.walk_rate, bb.walk_rate(70, 632))
        self.assertEqual(self.line.stolen_base_percentage, 0.75)

    def test_linear_weight_stats_match_module_functions(self):
        expected_woba = bb.woba(70, 5, 90, 30, 5, 25, 550, 5, 5)
        self.assertEqual(self.line.woba(), expected_woba)
        self.assertEqual(self.line.wraa(), bb.wraa(expected_woba, 632))
        self.assertEqual(self.line.wrc(), bb.wrc(expected_woba, 632))
        self.assertEqual(self.line.wrc_plus(), bb.wrc_plus(expected_woba))
        self.assertEqual(self.line.runs_created(), bb.runs_created(150, 70, 265, 550))

    def test_slash(self):
        self.assertEqual(self.line.slash(), "0.273/0.357/0.482")

    def test_from_mlb_full_split(self):
        self.assertEqual(BattingLine.from_mlb(HITTING_SPLIT), self.line)

    def test_from_mlb_bare_stat_dict(self):
        self.assertEqual(BattingLine.from_mlb(HITTING_SPLIT["stat"]), self.line)

    def test_from_mlb_missing_keys_default_to_zero(self):
        line = BattingLine.from_mlb({"stat": {"atBats": 100, "hits": 30}})
        self.assertEqual(line.hits, 30)
        self.assertEqual(line.home_runs, 0)
        self.assertAlmostEqual(line.avg, 0.300, places=6)

    def test_addition_combines_fields(self):
        combined = self.line + self.line
        self.assertEqual(combined.hits, 300)
        self.assertEqual(combined.plate_appearances, 1264)
        # Rate stats are unchanged when combining identical lines
        self.assertAlmostEqual(combined.avg, self.line.avg, places=9)

    def test_addition_rejects_other_types(self):
        with self.assertRaises(TypeError):
            self.line + 1

    def test_empty_line_rates_are_zero(self):
        empty = BattingLine()
        self.assertEqual(empty.avg, 0.0)
        self.assertEqual(empty.woba(), 0.0)


class TestPitchingLine(unittest.TestCase):
    def setUp(self):
        self.line = PitchingLine(
            outs=540, hits=160, runs=75, earned_runs=65, walks=50,
            intentional_walks=2, strikeouts=190, home_runs=18,
            hit_by_pitch=5, batters_faced=740,
        )

    def test_innings_from_outs(self):
        self.assertEqual(self.line.innings_pitched, 180.0)

    def test_properties_match_module_functions(self):
        self.assertEqual(self.line.era, bb.era(65, 180.0))
        self.assertEqual(self.line.whip, bb.whip(50, 160, 180.0))
        self.assertEqual(self.line.k_per_9, bb.k_per_9(190, 180.0))
        self.assertEqual(self.line.k_bb_ratio, bb.k_bb_ratio(190, 50))
        self.assertEqual(self.line.strikeout_rate, bb.strikeout_rate(190, 740))
        self.assertEqual(
            self.line.left_on_base_percentage,
            bb.left_on_base_percentage(160, 50, 5, 75, 18),
        )

    def test_fip_and_relative_eras(self):
        self.assertEqual(self.line.fip(), bb.fip(18, 50, 5, 190, 180.0))
        self.assertEqual(self.line.era_plus(4.20), bb.era_plus(self.line.era, 4.20))
        self.assertEqual(self.line.era_minus(4.20), bb.era_minus(self.line.era, 4.20))

    def test_from_mlb_prefers_outs(self):
        self.assertEqual(PitchingLine.from_mlb(PITCHING_SPLIT), self.line)

    def test_from_mlb_falls_back_to_innings_pitched(self):
        stat = dict(PITCHING_SPLIT["stat"])
        del stat["outs"]
        stat["inningsPitched"] = "180.2"  # box-score notation: 180 and 2 outs
        line = PitchingLine.from_mlb(stat)
        self.assertEqual(line.outs, 542)

    def test_addition_combines_fields(self):
        combined = self.line + self.line
        self.assertEqual(combined.outs, 1080)
        self.assertAlmostEqual(combined.era, self.line.era, places=9)


if __name__ == "__main__":
    unittest.main()
