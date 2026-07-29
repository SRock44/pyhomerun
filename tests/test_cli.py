"""Offline CLI tests: a stub client is injected, so nothing hits the network."""

import contextlib
import io
import unittest
from unittest import mock

import pyhomerun.cli
from pyhomerun.cli import main
from pyhomerun.mlb import MLBAPIError


class StubClient:
    """Canned responses for every client method the CLI touches."""

    def get(self, path, **params):
        if path == "/divisions":
            return {"divisions": [{"id": 201, "name": "American League East"}]}
        raise AssertionError(f"unexpected path {path}")

    def standings(self, season=None):
        return [
            {
                "division": {"id": 201},
                "league": {"id": 103},
                "teamRecords": [
                    {"team": {"id": 147, "name": "New York Yankees"}, "wins": 90, "losses": 60,
                     "winningPercentage": ".600", "gamesBack": "-"},
                    {"team": {"id": 111, "name": "Boston Red Sox"}, "wins": 84, "losses": 66,
                     "winningPercentage": ".560", "gamesBack": "6.0"},
                ],
            }
        ]

    def schedule(self, date=None, team_id=None, start_date=None, end_date=None):
        if start_date or end_date:
            return [
                {
                    "gameType": "R",
                    "gameDate": "2025-04-01T17:05:00Z",
                    "status": {"abstractGameState": "Final", "detailedState": "Final"},
                    "teams": {
                        "away": {"team": {"id": 111, "name": "Boston Red Sox"}, "score": 3},
                        "home": {"team": {"id": 147, "name": "New York Yankees"}, "score": 5},
                    },
                },
                {
                    "gameType": "R",
                    "gameDate": "2025-04-02T17:05:00Z",
                    "status": {"abstractGameState": "Final", "detailedState": "Final"},
                    "teams": {
                        "away": {"team": {"id": 147, "name": "New York Yankees"}, "score": 2},
                        "home": {"team": {"id": 111, "name": "Boston Red Sox"}, "score": 6},
                    },
                },
                {
                    "gameType": "S",  # spring training -- must be excluded
                    "gameDate": "2025-03-01T17:05:00Z",
                    "status": {"abstractGameState": "Final", "detailedState": "Final"},
                    "teams": {
                        "away": {"team": {"id": 111, "name": "Boston Red Sox"}, "score": 1},
                        "home": {"team": {"id": 147, "name": "New York Yankees"}, "score": 10},
                    },
                },
                {
                    "gameType": "R",
                    "gameDate": "2025-09-28T17:05:00Z",
                    "status": {"abstractGameState": "Preview", "detailedState": "Scheduled"},
                    "teams": {
                        "away": {"team": {"id": 111, "name": "Boston Red Sox"}, "score": None},
                        "home": {"team": {"id": 147, "name": "New York Yankees"}, "score": None},
                    },
                },
            ]
        return [
            {
                "teams": {
                    "away": {"team": {"name": "Boston Red Sox"}, "score": 3},
                    "home": {"team": {"name": "New York Yankees"}, "score": 5},
                },
                "status": {"detailedState": "Final"},
            }
        ]

    def find_player(self, name):
        return {
            "id": 592450,
            "fullName": "Aaron Judge",
            "primaryPosition": {"name": "Outfielder"},
            "currentTeam": {"name": "New York Yankees"},
        }

    def player_stats(self, player_id, group="hitting", stat_type="season", season=None):
        if group == "hitting":
            return [{"stat": {"atBats": 550, "hits": 180, "doubles": 30, "triples": 1,
                              "homeRuns": 53, "baseOnBalls": 110, "hitByPitch": 5,
                              "strikeOuts": 150, "sacFlies": 3, "stolenBases": 10}}]
        return []

    def teams(self, season=None):
        return [
            {"id": 147, "name": "New York Yankees", "teamName": "Yankees", "abbreviation": "NYY"},
            {"id": 111, "name": "Boston Red Sox", "teamName": "Red Sox", "abbreviation": "BOS"},
        ]

    def roster(self, team_id, season=None):
        assert team_id == 147
        return [
            {"jerseyNumber": "99", "person": {"id": 592450, "fullName": "Aaron Judge"},
             "position": {"abbreviation": "RF"}},
        ]


def run_cli(*argv, client=None):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(list(argv), client=client or StubClient())
    return code, out.getvalue()


class TestCli(unittest.TestCase):
    def test_standings(self):
        code, out = run_cli("standings")
        self.assertEqual(code, 0)
        self.assertIn("American League East", out)
        self.assertIn("New York Yankees", out)
        self.assertIn("90", out)

    def test_scores(self):
        code, out = run_cli("scores", "2025-10-01")
        self.assertEqual(code, 0)
        self.assertIn("Final", out)
        self.assertIn("Boston Red Sox", out)

    def test_player_shows_batting_line(self):
        code, out = run_cli("player", "Arron", "Judge")  # typo, resolved by the stub
        self.assertEqual(code, 0)
        self.assertIn("Aaron Judge", out)
        self.assertIn("HR 53", out)
        self.assertIn("wRC+", out)
        self.assertNotIn("Pitching:", out)

    def test_teams(self):
        code, out = run_cli("teams")
        self.assertEqual(code, 0)
        self.assertIn("NYY", out)

    def test_roster_fuzzy_team_name(self):
        code, out = run_cli("roster", "yankees")
        self.assertEqual(code, 0)
        self.assertIn("Aaron Judge", out)
        self.assertIn("RF", out)

    def test_roster_by_id(self):
        code, out = run_cli("roster", "147")
        self.assertEqual(code, 0)
        self.assertIn("Aaron Judge", out)

    def test_export_writes_csv_to_stdout(self):
        code, out = run_cli("export", "hitting", "yankees")
        self.assertEqual(code, 0)
        self.assertIn("Aaron Judge", out)
        self.assertIn("home_runs", out.splitlines()[0])

    def test_export_writes_csv_to_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "yankees.csv"
            code, out = run_cli("export", "hitting", "yankees", "--out", str(out_path))
            self.assertEqual(code, 0)
            self.assertEqual(out, "")
            self.assertIn("Aaron Judge", out_path.read_text())

    def test_elo_ranks_teams_from_completed_games(self):
        code, out = run_cli("elo", "--season", "2025")
        self.assertEqual(code, 0)
        self.assertIn("New York Yankees", out)
        self.assertIn("Boston Red Sox", out)
        # Only the two "R" games count; the "S" (spring training) blowout
        # must not have moved either rating.
        self.assertNotIn("1600", out)

    def test_playoff_odds_reports_every_standings_team(self):
        code, out = run_cli("playoff-odds", "--season", "2025", "--simulations", "50")
        self.assertEqual(code, 0)
        self.assertIn("New York Yankees", out)
        self.assertIn("Boston Red Sox", out)
        self.assertIn("Playoff odds", out)

    def test_playoff_odds_uses_requested_simulation_count(self):
        captured = {}
        real_simulate = pyhomerun.cli.simulate_remaining_season

        def spy(*args, **kwargs):
            captured["n_simulations"] = kwargs.get("n_simulations")
            return real_simulate(*args, **kwargs)

        with mock.patch("pyhomerun.cli.simulate_remaining_season", side_effect=spy):
            code, _ = run_cli("playoff-odds", "--season", "2025", "--simulations", "77")
        self.assertEqual(code, 0)
        self.assertEqual(captured["n_simulations"], 77)

    def test_api_error_returns_nonzero(self):
        class FailingClient(StubClient):
            def standings(self, season=None):
                raise MLBAPIError("boom")

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = run_cli("standings", client=FailingClient())
        self.assertEqual(code, 1)
        self.assertIn("boom", err.getvalue())


if __name__ == "__main__":
    unittest.main()
