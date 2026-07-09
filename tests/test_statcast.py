"""Offline tests for the Statcast (Baseball Savant) client.

Like tests/test_mlb.py, these never touch the network: urllib is patched
with canned responses so the suite runs anywhere, instantly.
"""

import io
import unittest
import urllib.error
from unittest import mock

from pyhomerun import StatcastClient, StatcastError


def _fake_response(body_bytes):
    """Build a file-like object usable as a urlopen() context manager."""
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(body_bytes)
    response.__exit__.return_value = False
    return response


CSV_BODY = (
    b"pitch_type,launch_speed,launch_angle,player_name\n"
    b"FF,101.4,17.0,Aaron Judge\n"
    b"SL,,,\n"
)


class TestSearch(unittest.TestCase):
    def test_parses_rows_and_coerces_numerics(self):
        client = StatcastClient()
        with mock.patch("urllib.request.urlopen", return_value=_fake_response(CSV_BODY)):
            rows = client.search("2024-06-01", "2024-06-30")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["launch_speed"], 101.4)
        self.assertEqual(rows[0]["player_name"], "Aaron Judge")

    def test_empty_cells_become_none(self):
        client = StatcastClient()
        with mock.patch("urllib.request.urlopen", return_value=_fake_response(CSV_BODY)):
            rows = client.search("2024-06-01", "2024-06-30")
        self.assertIsNone(rows[1]["launch_speed"])
        self.assertIsNone(rows[1]["player_name"])

    def test_empty_response_returns_empty_list(self):
        client = StatcastClient()
        with mock.patch("urllib.request.urlopen", return_value=_fake_response(b"")):
            self.assertEqual(client.search("2024-06-01", "2024-06-30"), [])

    def test_html_response_raises_clear_error(self):
        client = StatcastClient()
        html = b"<html><body>Not Found</body></html>"
        with mock.patch("urllib.request.urlopen", return_value=_fake_response(html)):
            with self.assertRaises(StatcastError) as ctx:
                client.search("2024-06-01", "2024-06-30")
        self.assertIn("HTML", str(ctx.exception))

    def test_http_error_becomes_statcasterror(self):
        client = StatcastClient()
        error = urllib.error.HTTPError("url", 500, "Internal Server Error", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(StatcastError) as ctx:
                client.search("2024-06-01", "2024-06-30")
        self.assertIn("500", str(ctx.exception))

    def test_network_error_becomes_statcasterror(self):
        client = StatcastClient()
        error = urllib.error.URLError("dns failure")
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(StatcastError):
                client.search("2024-06-01", "2024-06-30")

    def test_invalid_player_type_raises(self):
        client = StatcastClient()
        with self.assertRaises(ValueError):
            client.search("2024-06-01", "2024-06-30", player_type="catcher")

    def test_builds_url_with_dates_and_player_lookup(self):
        client = StatcastClient()
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response(b"")
        ) as urlopen:
            client.search("2024-06-01", "2024-06-30", player_id=660271, player_type="batter")
        url = urlopen.call_args[0][0].full_url
        self.assertIn("game_date_gt=2024-06-01", url)
        self.assertIn("game_date_lt=2024-06-30", url)
        self.assertIn("batters_lookup%5B%5D=660271", url)

    def test_pitcher_lookup_uses_pitchers_key(self):
        client = StatcastClient()
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response(b"")
        ) as urlopen:
            client.search("2024-06-01", "2024-06-30", player_id=543037, player_type="pitcher")
        url = urlopen.call_args[0][0].full_url
        self.assertIn("pitchers_lookup%5B%5D=543037", url)

    def test_season_sets_hfsea_filter(self):
        client = StatcastClient()
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response(b"")
        ) as urlopen:
            client.search("2024-06-01", "2024-06-30", season=2024)
        url = urlopen.call_args[0][0].full_url
        self.assertIn("hfSea=2024%7C", url)

    def test_extra_params_override_defaults(self):
        client = StatcastClient()
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response(b"")
        ) as urlopen:
            client.search("2024-06-01", "2024-06-30", hfZ="1|")
        url = urlopen.call_args[0][0].full_url
        self.assertIn("hfZ=1%7C", url)

    def test_extra_params_none_removes_key(self):
        client = StatcastClient()
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response(b"")
        ) as urlopen:
            client.search("2024-06-01", "2024-06-30", min_pitches=None)
        url = urlopen.call_args[0][0].full_url
        self.assertNotIn("min_pitches=", url)

    def test_custom_base_url(self):
        client = StatcastClient(base_url="http://localhost:9000/csv")
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response(b"")
        ) as urlopen:
            client.search("2024-06-01", "2024-06-30")
        url = urlopen.call_args[0][0].full_url
        self.assertTrue(url.startswith("http://localhost:9000/csv?"))


if __name__ == "__main__":
    unittest.main()
