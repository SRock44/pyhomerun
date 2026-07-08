"""Offline tests for the MLB Stats API client.

These tests never touch the network: urllib is patched with canned
responses so the suite runs anywhere, instantly.
"""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
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


class TestRetries(unittest.TestCase):
    def test_no_retry_by_default(self):
        client = MLBClient()
        error = urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error) as urlopen:
            with self.assertRaises(MLBAPIError):
                client.get("/teams")
        self.assertEqual(urlopen.call_count, 1)

    def test_retries_5xx_then_succeeds(self):
        client = MLBClient(retries=2, backoff_factor=0)
        error = urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None)
        with mock.patch(
            "urllib.request.urlopen", side_effect=[error, _fake_response({"teams": []})]
        ) as urlopen:
            with mock.patch("time.sleep") as sleep:
                result = client.get("/teams")
        self.assertEqual(result, {"teams": []})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(0)

    def test_does_not_retry_4xx(self):
        client = MLBClient(retries=3)
        error = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error) as urlopen:
            with self.assertRaises(MLBAPIError):
                client.get("/nope")
        self.assertEqual(urlopen.call_count, 1)

    def test_retries_network_errors(self):
        client = MLBClient(retries=1, backoff_factor=0)
        error = urllib.error.URLError("timed out")
        with mock.patch(
            "urllib.request.urlopen", side_effect=[error, _fake_response({})]
        ) as urlopen:
            with mock.patch("time.sleep"):
                client.get("/teams")
        self.assertEqual(urlopen.call_count, 2)

    def test_exhausts_retries_then_raises(self):
        client = MLBClient(retries=2, backoff_factor=0)
        error = urllib.error.HTTPError("url", 500, "Internal Server Error", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error) as urlopen:
            with mock.patch("time.sleep"):
                with self.assertRaises(MLBAPIError):
                    client.get("/teams")
        self.assertEqual(urlopen.call_count, 3)


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

    def test_play_by_play_unwraps_all_plays(self):
        client = self._client_returning({"allPlays": [{"result": {"event": "Single"}}]})
        plays = client.play_by_play(717465)
        self.assertEqual(plays[0]["result"]["event"], "Single")

    def test_venues_unwraps(self):
        client = self._client_returning({"venues": [{"id": 3313, "name": "Yankee Stadium"}]})
        self.assertEqual(client.venues()[0]["name"], "Yankee Stadium")

    def test_awards_unwraps(self):
        client = self._client_returning({"awards": [{"id": "ALMVP", "name": "AL MVP"}]})
        self.assertEqual(client.awards()[0]["id"], "ALMVP")

    def test_award_recipients_unwraps(self):
        client = self._client_returning({"recipients": [{"player": {"fullName": "Shohei Ohtani"}}]})
        recipients = client.award_recipients("ALMVP", season=2024)
        self.assertEqual(recipients[0]["player"]["fullName"], "Shohei Ohtani")

    def test_draft_flattens_rounds(self):
        client = self._client_returning({
            "drafts": {
                "rounds": [
                    {"picks": [{"pickNumber": 1}, {"pickNumber": 2}]},
                    {"picks": [{"pickNumber": 31}]},
                ]
            }
        })
        picks = client.draft(2025)
        self.assertEqual([p["pickNumber"] for p in picks], [1, 2, 31])


class _SearchStubClient(MLBClient):
    """MLBClient with search_players replaced by canned responses."""

    def __init__(self, responses):
        super().__init__()
        self.responses = responses
        self.queries = []

    def search_players(self, name):
        self.queries.append(name)
        return self.responses.get(name, [])


class TestFindPlayer(unittest.TestCase):
    JUDGE = {"id": 592450, "fullName": "Aaron Judge"}
    BOONE = {"id": 111, "fullName": "Aaron Boone"}

    def test_direct_hit_uses_api_search(self):
        client = _SearchStubClient({"Aaron Judge": [self.JUDGE]})
        self.assertEqual(client.find_player("Aaron Judge"), self.JUDGE)

    def test_misspelling_falls_back_to_tokens_and_fuzzy_ranks(self):
        client = _SearchStubClient({"Judge": [self.JUDGE], "Aaron": [self.BOONE, self.JUDGE]})
        self.assertEqual(client.find_player("Arron Judge"), self.JUDGE)

    def test_short_tokens_skipped(self):
        client = _SearchStubClient({"Judge": [self.JUDGE]})
        client.find_player("AJ Judge")
        self.assertNotIn("AJ", client.queries)

    def test_no_match_raises(self):
        client = _SearchStubClient({})
        with self.assertRaises(MLBAPIError):
            client.find_player("Nobody Realman")


class TestCaching(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client = MLBClient(cache_ttl=3600, cache_dir=self.tmp.name)

    def test_second_call_served_from_cache(self):
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response({"teams": [1]})
        ) as urlopen:
            first = self.client.get("/teams", sportId=1)
        with mock.patch("urllib.request.urlopen") as urlopen_again:
            second = self.client.get("/teams", sportId=1)
        self.assertEqual(first, second)
        self.assertEqual(urlopen.call_count, 1)
        urlopen_again.assert_not_called()

    def test_stale_entry_refetches(self):
        with mock.patch("urllib.request.urlopen", return_value=_fake_response({"v": 1})):
            self.client.get("/teams")
        # Age the single cache entry past the TTL
        cache_file = next(Path(self.tmp.name).glob("*.json"))
        entry = json.loads(cache_file.read_text("utf-8"))
        entry["time"] -= 7200
        cache_file.write_text(json.dumps(entry), "utf-8")
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response({"v": 2})
        ) as urlopen:
            refreshed = self.client.get("/teams")
        self.assertEqual(refreshed, {"v": 2})
        self.assertEqual(urlopen.call_count, 1)

    def test_corrupt_cache_entry_is_a_miss(self):
        with mock.patch("urllib.request.urlopen", return_value=_fake_response({"v": 1})):
            self.client.get("/teams")
        next(Path(self.tmp.name).glob("*.json")).write_text("not json", "utf-8")
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response({"v": 2})
        ) as urlopen:
            self.assertEqual(self.client.get("/teams"), {"v": 2})
        self.assertEqual(urlopen.call_count, 1)

    def test_caching_disabled_by_default(self):
        client = MLBClient()
        with mock.patch(
            "urllib.request.urlopen", side_effect=lambda *a, **k: _fake_response({})
        ) as urlopen:
            client.get("/teams")
            client.get("/teams")
        self.assertEqual(urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
