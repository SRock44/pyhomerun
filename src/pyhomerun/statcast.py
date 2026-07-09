"""Statcast data (exit velocity, launch angle, spin rate, ...) via Baseball
Savant's CSV export.

Baseball Savant (baseballsavant.mlb.com) publishes advanced Statcast metrics
that never made it into the MLB Stats API. It exposes them through a CSV
download built for its own search UI, not a documented, versioned API --
there's no contract that the URL, its parameters, or its column names stay
stable from one day to the next.

Because of that, this module is written defensively rather than as a thin
``.get()``-style passthrough like :meth:`~pyhomerun.mlb.MLBClient.get`.
Every failure mode -- network error, HTTP error, an HTML page returned
instead of CSV because the endpoint changed shape -- is caught and
re-raised as a :class:`StatcastError` with a message that says what
actually went wrong, rather than a raw ``csv.Error`` or a silently empty
result. If Savant changes its export format, expect a clear
``StatcastError`` here, not corrupted data -- and please open an issue.

Example::

    from pyhomerun import StatcastClient

    savant = StatcastClient()
    pitches = savant.search("2024-06-01", "2024-06-30", player_id=660271)
    speeds = [p["launch_speed"] for p in pitches if p["launch_speed"]]
"""

from __future__ import annotations

import csv
import io
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Union

__all__ = ["StatcastClient", "StatcastError"]

_BASE_URL = "https://baseballsavant.mlb.com/statcast_search/csv"
_USER_AGENT = "pyhomerun (https://github.com/SRock44/pyhomerun)"

#: Default query parameters mirroring Baseball Savant's own search form.
#: Only the handful pyhomerun exposes as :meth:`StatcastClient.search`
#: arguments vary per call; the rest pin Savant's many optional filters to
#: "no filter" so results aren't silently narrowed by a stale default.
_DEFAULT_PARAMS: Dict[str, str] = {
    "hfPT": "",
    "hfAB": "",
    "hfBBT": "",
    "hfPR": "",
    "hfZ": "",
    "stadium": "",
    "hfBBL": "",
    "hfNewZones": "",
    "hfGT": "R|",
    "hfC": "",
    "hfSit": "",
    "hfOuts": "",
    "opponent": "",
    "pitcher_throws": "",
    "batter_stands": "",
    "hfSA": "",
    "hfInfield": "",
    "team": "",
    "position": "",
    "hfOutfield": "",
    "hfRO": "",
    "home_road": "",
    "hfFlag": "",
    "hfPull": "",
    "metric_1": "",
    "hfInn": "",
    "min_pitches": "0",
    "min_results": "0",
    "group_by": "name",
    "sort_col": "pitches",
    "player_event_sort": "api_p_release_speed",
    "sort_order": "desc",
    "min_pas": "0",
    "type": "details",
}


class StatcastError(Exception):
    """Raised when a Statcast query fails, or Savant's CSV export changed shape."""


class StatcastClient:
    """Client for Baseball Savant's Statcast CSV export.

    Unlike :class:`~pyhomerun.mlb.MLBClient`, this talks to an undocumented,
    UI-oriented CSV download rather than a stable JSON API. Treat failures
    as expected: catch :class:`StatcastError` and degrade gracefully
    rather than assuming a query will always succeed.

    Args:
        timeout: Per-request timeout in seconds. Statcast queries can
            return a lot of rows, so this defaults higher than
            :class:`~pyhomerun.mlb.MLBClient`'s.
        base_url: Override the endpoint (useful for testing).
    """

    def __init__(self, timeout: float = 30.0, base_url: str = _BASE_URL) -> None:
        self.timeout = timeout
        self.base_url = base_url

    def search(
        self,
        start_dt: str,
        end_dt: str,
        player_id: Optional[int] = None,
        player_type: str = "batter",
        season: Optional[int] = None,
        **extra_params: Union[str, int, None],
    ) -> List[Dict[str, Any]]:
        """Pitch-by-pitch Statcast rows for a date range.

        Args:
            start_dt: Start date, ``"YYYY-MM-DD"``.
            end_dt: End date, ``"YYYY-MM-DD"``, inclusive.
            player_id: Restrict to one player's MLBAM id (see
                :meth:`~pyhomerun.mlb.MLBClient.find_player`). Omit for
                every player.
            player_type: ``"batter"`` or ``"pitcher"`` -- which side
                ``player_id`` refers to.
            season: Restrict to one season (Savant's ``hfSea`` filter);
                omit to span ``start_dt``..``end_dt`` regardless of
                season boundaries.
            **extra_params: Additional raw Savant query parameters, for
                filters this method doesn't expose directly (e.g.
                ``hfZ="1|"`` for a strike-zone region). Passed through
                as-is -- see Baseball Savant's search UI for valid keys.
                A ``None`` value removes that key from the query instead
                of setting it.

        Returns:
            One dict per pitch, keyed by Savant's CSV column names
            (``launch_speed``, ``launch_angle``, ``release_spin_rate``,
            ...). Numeric-looking values are converted to ``float``;
            empty cells become ``None``; everything else stays a string.

        Raises:
            StatcastError: the request failed, or Savant returned
                something that isn't a Statcast CSV -- most likely
                because the undocumented export changed shape (see the
                module docstring).
        """
        if player_type not in ("batter", "pitcher"):
            raise ValueError('player_type must be "batter" or "pitcher"')

        params = dict(_DEFAULT_PARAMS)
        params["player_type"] = player_type
        params["game_date_gt"] = start_dt
        params["game_date_lt"] = end_dt
        params["hfSea"] = f"{season}|" if season else ""
        if player_id is not None:
            key = "batters_lookup[]" if player_type == "batter" else "pitchers_lookup[]"
            params[key] = str(player_id)
        for key, value in extra_params.items():
            if value is None:
                params.pop(key, None)
            else:
                params[key] = str(value)

        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        text = self._fetch(url)
        return self._parse(text)

    def _fetch(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise StatcastError(
                f"Baseball Savant returned HTTP {exc.code} for a Statcast query. "
                "This is an undocumented endpoint and can change without notice "
                "-- if this persists, please open a pyhomerun issue."
            ) from exc
        except urllib.error.URLError as exc:
            raise StatcastError(f"could not reach Baseball Savant: {exc.reason}") from exc

    def _parse(self, text: str) -> List[Dict[str, Any]]:
        stripped = text.strip()
        if not stripped:
            return []
        if stripped.lstrip().startswith("<"):
            raise StatcastError(
                "Baseball Savant returned HTML instead of CSV. This usually "
                "means the undocumented export endpoint changed shape or is "
                "temporarily down -- please open a pyhomerun issue if this "
                "persists."
            )
        try:
            rows = list(csv.DictReader(io.StringIO(stripped)))
        except csv.Error as exc:
            raise StatcastError(f"could not parse Statcast CSV: {exc}") from exc
        return [self._coerce(row) for row in rows]

    @staticmethod
    def _coerce(row: Dict[str, Optional[str]]) -> Dict[str, Any]:
        coerced: Dict[str, Any] = {}
        for key, value in row.items():
            if not value:
                coerced[key] = None
                continue
            try:
                coerced[key] = float(value)
            except ValueError:
                coerced[key] = value
        return coerced
