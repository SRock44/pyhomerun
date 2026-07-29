"""Baseball in your terminal — the ``pyhomerun`` command.

Installed as a console command by pip, and also runnable as
``python -m pyhomerun``::

    pyhomerun standings
    pyhomerun scores 2025-10-01
    pyhomerun player "Arron Judge"       # fuzzy: finds Aaron Judge
    pyhomerun teams
    pyhomerun roster "yankees"
    pyhomerun export hitting "yankees" --out yankees.csv
    pyhomerun elo
    pyhomerun playoff-odds --season 2025

Data comes from the free MLB Stats API; responses are cached for five
minutes so repeated commands are fast and polite.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from . import __version__
from .elo import EloRatings
from .export import to_csv
from .lines import BattingLine, PitchingLine
from .mlb import MLBAPIError, MLBClient
from .simulate import mlb_playoff_qualifiers, simulate_remaining_season, simulation_odds

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


def _division_names(mlb: MLBClient) -> Dict[int, str]:
    return {d["id"]: d["name"] for d in mlb.get("/divisions", sportId=1).get("divisions", [])}


def _season_games(mlb: MLBClient, season: int) -> List[Dict[str, Any]]:
    """Regular-season MLB games for a season, in chronological order.

    Excludes spring training and exhibition games (``gameType`` ``"S"``/
    ``"E"``) and the All-Star Game (``"A"``) -- the schedule endpoint
    includes all of these under the same MLB ``sportId``, but none of
    them are meaningful signal for team strength or a playoff race.
    """
    games = mlb.schedule(start_date=f"{season}-01-01", end_date=f"{season}-12-31")
    regular_season = [g for g in games if g.get("gameType") == "R"]
    return sorted(regular_season, key=lambda g: g.get("gameDate", ""))


def _elo_from_games(games: List[Dict[str, Any]]) -> EloRatings:
    """Build Elo ratings from every game with a decisive final score.

    Deliberately keyed off score presence rather than ``status.detailedState``:
    the schedule endpoint marks some games with real final scores as
    ``"Completed Early"`` (rain-shortened) rather than ``"Final"``, and marks
    some rained-out games with no makeup as ``"Postponed"`` while still
    reporting them as closed (``abstractGameState`` ``"Final"``) with no
    score at all. A present, unequal score is what actually means "this game
    happened and here's the result" -- everything else is noise.
    """
    elo = EloRatings()
    for game in games:
        away, home = game["teams"]["away"], game["teams"]["home"]
        home_score, away_score = home.get("score"), away.get("score")
        if home_score is None or away_score is None or home_score == away_score:
            continue
        elo.record_game(home["team"]["name"], away["team"]["name"], home_score, away_score)
    return elo


def _cmd_elo(mlb: MLBClient, args: argparse.Namespace) -> int:
    season = args.season or date.today().year
    elo = _elo_from_games(_season_games(mlb, season))
    rows = [(i + 1, team, f"{rating:.1f}") for i, (team, rating) in enumerate(elo.ranked())]
    print(_table(("#", "Team", "Elo"), rows))
    return 0


def _mlb_playoff_qualifies(
    by_league: Dict[Any, Dict[str, List[str]]]
) -> Callable[[Dict[str, int]], Set[str]]:
    """Combines per-league :func:`mlb_playoff_qualifiers` (AL and NL each
    have their own 3 wild-card spots, not a single MLB-wide pool)."""
    per_league = [mlb_playoff_qualifiers(divisions, wildcard_spots=3) for divisions in by_league.values()]

    def qualifies(final_wins: Dict[str, int]) -> Set[str]:
        result: Set[str] = set()
        for one_league in per_league:
            result |= set(one_league(final_wins))
        return result

    return qualifies


def _cmd_playoff_odds(mlb: MLBClient, args: argparse.Namespace) -> int:
    season = args.season or date.today().year
    games = _season_games(mlb, season)
    elo = _elo_from_games(games)

    # A game is still to be played if the API hasn't closed its record yet
    # (abstractGameState "Preview"/"Live") -- unlike detailedState, this
    # isn't fooled by "Postponed"/"Completed Early" placeholders for games
    # that already happened one way or another (see _elo_from_games).
    remaining: List[Tuple[str, str]] = [
        (game["teams"]["home"]["team"]["name"], game["teams"]["away"]["team"]["name"])
        for game in games
        if game.get("status", {}).get("abstractGameState") != "Final"
    ]

    # standings() teamRecords only carry each team's short name ("Blue Jays"),
    # while schedule() (and therefore `elo` and `remaining` above) uses the
    # full name ("Toronto Blue Jays") -- normalize through team id via
    # teams() so Elo ratings, current win totals, and division groupings
    # all agree on one name per team.
    full_names = {team["id"]: team["name"] for team in mlb.teams(season=season)}

    division_names = _division_names(mlb)
    by_league: Dict[Any, Dict[str, List[str]]] = {}
    current_wins: Dict[str, int] = {}
    for record in mlb.standings(season=season):
        league_id = record.get("league", {}).get("id")
        division_id = record.get("division", {}).get("id")
        name = division_names.get(division_id, str(division_id))
        team_names = []
        for team in record.get("teamRecords", []):
            team_id = team["team"]["id"]
            team_name = full_names.get(team_id, team["team"]["name"])
            team_names.append(team_name)
            current_wins[team_name] = team.get("wins", 0)
        by_league.setdefault(league_id, {})[name] = team_names

    sims = simulate_remaining_season(
        current_wins, remaining, elo.win_probability, n_simulations=args.simulations
    )
    odds = simulation_odds(sims, _mlb_playoff_qualifies(by_league))
    rows = sorted(odds.items(), key=lambda item: item[1], reverse=True)
    print(_table(("Team", "Playoff odds"), [(team, f"{pct:.1%}") for team, pct in rows]))
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

    elo = sub.add_parser("elo", help="team power ratings from this season's completed games")
    elo.add_argument("--season", type=int, default=None)
    elo.set_defaults(func=_cmd_elo)

    playoff_odds = sub.add_parser(
        "playoff-odds", help="Monte Carlo playoff odds from Elo ratings and the remaining schedule"
    )
    playoff_odds.add_argument("--season", type=int, default=None)
    playoff_odds.add_argument(
        "--simulations", type=int, default=2000, help="number of simulated seasons (default: 2000)"
    )
    playoff_odds.set_defaults(func=_cmd_playoff_odds)

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
