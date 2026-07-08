"""A minimal client for the free MLB Stats API (statsapi.mlb.com).

Built entirely on the standard library — no third-party dependencies.
Every method returns the API's JSON parsed into plain dicts/lists, so the
full response is always available; nothing is hidden behind wrapper objects.

Example::

    from pyhomerun import MLBClient

    mlb = MLBClient()
    players = mlb.search_players("Shohei Ohtani")
    ohtani_id = players[0]["id"]
    stats = mlb.player_stats(ohtani_id, group="hitting", season=2025)

The MLB Stats API is free and requires no API key. Data is subject to the
MLB copyright notice: http://gdx.mlb.com/components/copyright.txt
"""

from __future__ import annotations

import difflib
import hashlib
import json
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

__all__ = ["MLBClient", "MLBAPIError"]

_BASE_URL = "https://statsapi.mlb.com/api/v1"
_USER_AGENT = "pyhomerun (https://github.com/SRock44/pyhomerun)"

#: sportId for Major League Baseball (the API also serves minor leagues).
MLB_SPORT_ID = 1

JSONDict = Dict[str, Any]


class MLBAPIError(Exception):
    """Raised when the MLB Stats API request fails or returns bad data."""


class MLBClient:
    """HTTP client for the MLB Stats API.

    Args:
        timeout: Per-request timeout in seconds.
        base_url: Override the API root (useful for testing/proxies).
        cache_ttl: If set, successful responses are cached on disk and
            reused for this many seconds. Great for notebooks and scripts
            that re-run, and polite to MLB's servers.
        cache_dir: Where cached responses live. Defaults to a
            ``pyhomerun-cache`` directory under the system temp dir.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        base_url: str = _BASE_URL,
        cache_ttl: Optional[float] = None,
        cache_dir: Union[str, Path, None] = None,
    ) -> None:
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self.cache_ttl = cache_ttl
        self.cache_dir = (
            Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "pyhomerun-cache"
        )

    # -- plumbing ----------------------------------------------------------

    def get(self, path: str, **params: Union[str, int, None]) -> JSONDict:
        """Perform a GET against any API path and return the parsed JSON.

        This is the escape hatch for endpoints without a dedicated method:
        ``client.get("/awards")``, ``client.get("/venues", season=2025)``.
        ``None``-valued params are omitted.
        """
        query = {k: str(v) for k, v in params.items() if v is not None}
        url = f"{self.base_url}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        if self.cache_ttl:
            cached = self._cache_read(url)
            if cached is not None:
                return cached
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data: JSONDict = json.load(response)
        except urllib.error.HTTPError as exc:
            raise MLBAPIError(f"MLB Stats API returned HTTP {exc.code} for {url}") from exc
        except urllib.error.URLError as exc:
            raise MLBAPIError(f"could not reach the MLB Stats API: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise MLBAPIError(f"MLB Stats API returned invalid JSON for {url}") from exc
        if self.cache_ttl:
            self._cache_write(url, data)
        return data

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")

    def _cache_read(self, url: str) -> Optional[JSONDict]:
        try:
            entry = json.loads(self._cache_path(url).read_text("utf-8"))
            if time.time() - entry["time"] <= (self.cache_ttl or 0):
                return entry["data"]  # type: ignore[no-any-return]
        except (OSError, ValueError, KeyError):
            pass  # missing, corrupt, or stale cache entries are simply misses
        return None

    def _cache_write(self, url: str, data: JSONDict) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_path(url).write_text(
                json.dumps({"time": time.time(), "data": data}), "utf-8"
            )
        except OSError:
            pass  # caching is best-effort; never fail the request over it

    # -- players -----------------------------------------------------------

    def search_players(self, name: str) -> List[JSONDict]:
        """Search players by (partial) name. Returns a list of person dicts.

        Each result includes ``id``, ``fullName``, ``primaryPosition``,
        ``currentTeam`` (when active), and more.
        """
        return self.get("/people/search", names=name).get("people", [])

    def find_player(self, name: str) -> JSONDict:
        """Best-match player lookup, tolerant of misspellings.

        Tries the API's own search first; if that finds nothing, searches
        on each name part separately and ranks every candidate against
        the full query with ``difflib``, returning the closest match.
        This recovers from a typo in *one* name part as long as the other
        part still prefix-matches (e.g. "Arron Judge" or "Aaron Jugde"
        both resolve to Aaron Judge). It can't recover a typo that breaks
        the leading letters of every part (e.g. "aron jugde"), since the
        MLB API's own search is prefix-based and there's no local name
        index to fall back on. Raises :class:`MLBAPIError` when nothing
        plausible is found.
        """
        people = self.search_players(name)
        if not people:
            candidates: Dict[int, JSONDict] = {}
            for token in name.split():
                if len(token) < 3:
                    continue
                for person in self.search_players(token):
                    candidates[person["id"]] = person
            people = list(candidates.values())
        if not people:
            raise MLBAPIError(f"no player found matching {name!r}")
        return max(
            people,
            key=lambda p: difflib.SequenceMatcher(
                None, name.lower(), str(p.get("fullName", "")).lower()
            ).ratio(),
        )

    def player(self, player_id: int) -> JSONDict:
        """Biographical info for one player (bats/throws, birth date, ...)."""
        people = self.get(f"/people/{player_id}").get("people", [])
        if not people:
            raise MLBAPIError(f"no player found with id {player_id}")
        return people[0]

    def player_stats(
        self,
        player_id: int,
        group: str = "hitting",
        stat_type: str = "season",
        season: Optional[int] = None,
    ) -> List[JSONDict]:
        """Stat lines for one player.

        Args:
            player_id: MLBAM player id (see :meth:`search_players`).
            group: ``"hitting"``, ``"pitching"``, or ``"fielding"``.
            stat_type: ``"season"``, ``"career"``, ``"yearByYear"``,
                ``"gameLog"``, and others supported by the API.
            season: Year, for season-scoped stat types.

        Returns:
            A list of split dicts; each has a ``stat`` dict with the
            counting stats (``hits``, ``atBats``, ``homeRuns``, ...).
        """
        data = self.get(
            f"/people/{player_id}/stats",
            stats=stat_type,
            group=group,
            season=season,
        )
        splits: List[JSONDict] = []
        for stat_block in data.get("stats", []):
            splits.extend(stat_block.get("splits", []))
        return splits

    # -- teams ---------------------------------------------------------------

    def teams(self, season: Optional[int] = None) -> List[JSONDict]:
        """All MLB teams (optionally for a specific season)."""
        return self.get("/teams", sportId=MLB_SPORT_ID, season=season).get("teams", [])

    def roster(self, team_id: int, season: Optional[int] = None) -> List[JSONDict]:
        """Active roster for a team. Each entry has ``person`` and ``position``."""
        return self.get(f"/teams/{team_id}/roster", season=season).get("roster", [])

    # -- games and standings -------------------------------------------------

    def schedule(
        self,
        date: Optional[str] = None,
        team_id: Optional[int] = None,
    ) -> List[JSONDict]:
        """Games for a date (``"YYYY-MM-DD"``, default today), flattened.

        Each game dict includes ``gamePk``, ``status``, ``teams`` (with
        scores), and ``venue``.
        """
        data = self.get("/schedule", sportId=MLB_SPORT_ID, date=date, teamId=team_id)
        games: List[JSONDict] = []
        for day in data.get("dates", []):
            games.extend(day.get("games", []))
        return games

    def standings(
        self,
        season: Optional[int] = None,
        league_ids: Iterable[int] = (103, 104),
    ) -> List[JSONDict]:
        """Division standings. 103 = American League, 104 = National League.

        Returns a list of division records, each with ``teamRecords``.
        """
        data = self.get(
            "/standings",
            leagueId=",".join(str(i) for i in league_ids),
            season=season,
        )
        return data.get("records", [])

    def boxscore(self, game_pk: int) -> JSONDict:
        """Full boxscore for a game (``gamePk`` from :meth:`schedule`)."""
        return self.get(f"/game/{game_pk}/boxscore")

    def linescore(self, game_pk: int) -> JSONDict:
        """Inning-by-inning line score for a game."""
        return self.get(f"/game/{game_pk}/linescore")
