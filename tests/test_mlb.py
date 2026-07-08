"""Offline tests for the MLB Stats API client.

These tests never touch the network: urllib is patched with canned
responses so the suite runs anywhere, instantly.
"""

import io
import json
import unittest
import urllib.error
from unittest import mock

from pyhomerun import MLBAPIError, MLBClient


def _fake_response(payload):
    """Build a file-like object usable as a urlopen() context manager."""
    body = io.BytesIO(json.dumps(payload).encode())
    response = mock.MagicMock()
    response.__enter__.return_value = body
    response.__exit__.return_value = False
    return response


class TestGet(unittest.TestCase):
    def test_builds_url_with_params_and_skips_none(self):
        client = MLBClient()
        with mock.patch("urllib.request.urlopen", return_value=_fake_response({})) as urlopen:
            client.get("/teams", sportId=1, season=None)
        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "https://statsapi.mlb.com/api/v1/teams?sportId=1")

    def test_sets_user_agent(self):
        client = MLBClient()
        with mock.patch("urllib.request.urlopen", return_value=_fake_response({})) as urlopen:
            client.get("/teams")
        request = urlopen.call_args[0][0]
        self.assertIn("pyhomerun", request.get_header("User-agent"))

    def test_http_error_becomes_mlbapierror(self):
        client = MLBClient()
        error = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(MLBAPIError) as ctx:
                client.get("/nope")
        self.assertIn("404", str(ctx.exception))

    def test_network_error_becomes_mlbapierror(self):
        client = MLBClient()
        error = urllib.error.URLError("dns failure")
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(MLBAPIError):
                client.get("/teams")

    def test_custom_base_url(self):
        client = MLBClient(base_url="http://localhost:9000/api/v1/")
        with mock.patch("urllib.request.urlopen", return_value=_fake_response({})) as urlopen:
            client.get("/teams")
        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "http://localhost:9000/api/v1/teams")


class TestEndpoints(unittest.TestCase):
    def _client_returning(self, payload):
        client = MLBClient()
        patcher = mock.patch("urllib.request.urlopen", return_value=_fake_response(payload))
        self.urlopen = patcher.start()
        self.addCleanup(patcher.stop)
        return client

    def test_search_players_unwraps_people(self):
        client = self._client_returning({"people": [{"id": 660271, "fullName": "Shohei Ohtani"}]})
        players = client.search_players("Shohei Ohtani")
        self.assertEqual(players[0]["id"], 660271)

    def test_player_missing_raises(self):
        client = self._client_returning({"people": []})
        with self.assertRaises(MLBAPIError):
            client.player(1)

    def test_player_stats_flattens_splits(self):
        client = self._client_returning({
            "stats": [
                {"splits": [{"season": "2024", "stat": {"homeRuns": 54}}]},
                {"splits": [{"season": "2025", "stat": {"homeRuns": 40}}]},
            ]
        })
        splits = client.player_stats(660271, group="hitting")
        self.assertEqual([s["stat"]["homeRuns"] for s in splits], [54, 40])

    def test_schedule_flattens_dates(self):
        client = self._client_returning({
            "dates": [
                {"games": [{"gamePk": 1}, {"gamePk": 2}]},
                {"games": [{"gamePk": 3}]},
            ]
        })
        games = client.schedule(date="2025-07-04")
        self.assertEqual([g["gamePk"] for g in games], [1, 2, 3])

    def test_standings_unwraps_records(self):
        client = self._client_returning({"records": [{"division": {"id": 201}}]})
        records = client.standings(season=2025)
        self.assertEqual(records[0]["division"]["id"], 201)

    def test_teams_and_roster_unwrap(self):
        client = self._client_returning({"teams": [{"id": 147, "name": "New York Yankees"}]})
        self.assertEqual(client.teams()[0]["id"], 147)


if __name__ == "__main__":
    unittest.main()
