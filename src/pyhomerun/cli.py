"""Baseball in your terminal — the ``pyhomerun`` command.

Installed as a console command by pip, and also runnable as
``python -m pyhomerun``::

    pyhomerun standings
    pyhomerun scores 2025-10-01
    pyhomerun player "Arron Judge"       # fuzzy: finds Aaron Judge
    pyhomerun teams
    pyhomerun roster "yankees"
    pyhomerun export hitting "yankees" --out yankees.csv

Data comes from the free MLB Stats API; responses are cached for five
minutes so repeated commands are fast and polite.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from typing import Any, Dict, List, Optional, Sequence

from . import __version__
from .export import to_csv
from .lines import BattingLine, PitchingLine
from .mlb import MLBAPIError, MLBClient

#: How long CLI responses are cached, in seconds.
CACHE_TTL = 300.0


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Render an aligned plain-text table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    def line(cells: Sequence[Any]) -> str:
        return "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells)).rstrip()
    return "\n".join([line(headers), line("-" * w for w in widths)] + [line(r) for r in rows])


def _cmd_standings(mlb: MLBClient, args: argparse.Namespace) -> int:
    divisions = {
        d["id"]: d["name"] for d in mlb.get("/divisions", sportId=1).get("divisions", [])
    }
    for record in mlb.standings(season=args.season):
        division_id = record.get("division", {}).get("id")
        print(divisions.get(division_id, "Division"))
        rows = [
            (
                team["team"]["name"],
                team.get("wins", 0),
                team.get("losses", 0),
                team.get("winningPercentage", ""),
                team.get("gamesBack", "-"),
            )
            for team in record.get("teamRecords", [])
        ]
        print(_table(("Team", "W", "L", "PCT", "GB"), rows))
        print()
    return 0


def _cmd_scores(mlb: MLBClient, args: argparse.Namespace) -> int:
    games = mlb.schedule(date=args.date)
    if not games:
        print("No games scheduled.")
        return 0
    rows = []
    for game in games:
        away, home = game["teams"]["away"], game["teams"]["home"]
        rows.append(
            (
                away["team"]["name"],
                away.get("score", ""),
                home["team"]["name"],
                home.get("score", ""),
                game.get("status", {}).get("detailedState", ""),
            )
        )
    print(_table(("Away", "R", "Home", "R", "Status"), rows))
    return 0


def _cmd_player(mlb: MLBClient, args: argparse.Namespace) -> int:
    name = " ".join(args.name)
    person = mlb.find_player(name)
    position = person.get("primaryPosition", {}).get("name", "?")
    team = person.get("currentTeam", {}).get("name", "")
    print(f'{person["fullName"]} — {position}' + (f" — {team}" if team else ""))

    hitting = mlb.player_stats(person["id"], group="hitting", season=args.season)
    if hitting:
        line = BattingLine.from_mlb(hitting[0])
        if line.plate_appearances:
            print(
                f"Batting:  {line.slash()}  HR {line.home_runs}  SB {line.stolen_bases}"
                f"  wOBA {line.woba():.3f}  wRC+ {line.wrc_plus():.0f}"
            )
    pitching = mlb.player_stats(person["id"], group="pitching", season=args.season)
    if pitching:
        line = PitchingLine.from_mlb(pitching[0])
        if line.outs:
            print(
                f"Pitching: {line.innings_pitched:.1f} IP  ERA {line.era:.2f}"
                f"  WHIP {line.whip:.2f}  K {line.strikeouts}  FIP {line.fip():.2f}"
            )
    return 0


def _cmd_teams(mlb: MLBClient, args: argparse.Namespace) -> int:
    rows = [
        (team["id"], team.get("abbreviation", ""), team["name"])
        for team in sorted(mlb.teams(season=args.season), key=lambda t: str(t["name"]))
    ]
    print(_table(("ID", "Abbr", "Team"), rows))
    return 0


def _find_team(mlb: MLBClient, query: str) -> Dict[str, Any]:
    teams = mlb.teams()
    if query.isdigit():
        for team in teams:
            if team["id"] == int(query):
                return team
    lowered = query.lower()
    scored = max(
        teams,
        key=lambda t: max(
            difflib.SequenceMatcher(None, lowered, str(t.get(key, "")).lower()).ratio()
            for key in ("name", "teamName", "abbreviation")
        ),
    )
    return scored


def _cmd_roster(mlb: MLBClient, args: argparse.Namespace) -> int:
    team = _find_team(mlb, " ".join(args.team))
    print(team["name"])
    rows = [
        (
            entry.get("jerseyNumber", ""),
            entry["person"]["fullName"],
            entry.get("position", {}).get("abbreviation", ""),
        )
        for entry in mlb.roster(team["id"])
    ]
    print(_table(("#", "Player", "Pos"), rows))
    return 0


def _cmd_export(mlb: MLBClient, args: argparse.Namespace) -> int:
    team = _find_team(mlb, " ".join(args.team))
    line_cls = BattingLine if args.group == "hitting" else PitchingLine
    lines: Dict[str, Any] = {}
    for entry in mlb.roster(team["id"], season=args.season):
        player_id = entry["person"]["id"]
        splits = mlb.player_stats(player_id, group=args.group, season=args.season)
        if splits:
            lines[entry["person"]["fullName"]] = line_cls.from_mlb(splits[0])
    text = to_csv(lines)
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            handle.write(text or "")
    else:
        sys.stdout.write(text or "")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyhomerun",
        description="Baseball in your terminal (data: MLB Stats API).",
    )
    parser.add_argument("--version", action="version", version=f"pyhomerun {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    standings = sub.add_parser("standings", help="division standings")
    standings.add_argument("--season", type=int, default=None)
    standings.set_defaults(func=_cmd_standings)

    scores = sub.add_parser("scores", help="scores for a date (default today)")
    scores.add_argument("date", nargs="?", default=None, help="YYYY-MM-DD")
    scores.set_defaults(func=_cmd_scores)

    player = sub.add_parser("player", help="look up a player (fuzzy match)")
    player.add_argument("name", nargs="+")
    player.add_argument("--season", type=int, default=None)
    player.set_defaults(func=_cmd_player)

    teams = sub.add_parser("teams", help="list MLB teams")
    teams.add_argument("--season", type=int, default=None)
    teams.set_defaults(func=_cmd_teams)

    roster = sub.add_parser("roster", help="a team's active roster")
    roster.add_argument("team", nargs="+", help="team name, abbreviation, or id")
    roster.set_defaults(func=_cmd_roster)

    export = sub.add_parser("export", help="export a team's stat lines to CSV")
    export.add_argument("group", choices=("hitting", "pitching"))
    export.add_argument("team", nargs="+", help="team name, abbreviation, or id")
    export.add_argument("--season", type=int, default=None)
    export.add_argument("--out", default=None, help="write to a file instead of stdout")
    export.set_defaults(func=_cmd_export)

    return parser


def main(argv: Optional[List[str]] = None, client: Optional[MLBClient] = None) -> int:
    """CLI entry point. Returns a process exit code."""
    args = _build_parser().parse_args(argv)
    mlb = client if client is not None else MLBClient(cache_ttl=CACHE_TTL)
    try:
        return int(args.func(mlb, args))
    except MLBAPIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
