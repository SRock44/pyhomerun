# ⚾ pyhomerun

**Baseball statistics and MLB data for Python — with zero dependencies.**

[![PyPI](https://img.shields.io/pypi/v/pyhomerun.svg)](https://pypi.org/project/pyhomerun/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

`pyhomerun` does two things:

1. **Sabermetrics** — pure functions for batting, pitching, and fielding statistics (AVG, OBP, SLG, OPS, wOBA, wRAA, ERA, FIP, WHIP, Game Score, ...). Plain numbers in, plain numbers out.
2. **MLB data** — `MLBClient`, a tiny client for the free, key-less [MLB Stats API](https://statsapi.mlb.com) (players, season stats, teams, rosters, schedules, standings, boxscores).

It is built **entirely on the Python standard library** — installing it installs nothing else, and the test suite runs with stock Python.

## Installation

Available on PyPI: https://pypi.org/project/pyhomerun/

```bash
pip install pyhomerun
```

Or straight from source:

```bash
git clone https://github.com/SRock44/pyhomerun
cd pyhomerun
pip install .
```

Requires Python 3.9+.

## Quick start

### Calculate statistics

```python
import pyhomerun as bb

# Classic rate stats
avg = bb.batting_average(hits=200, at_bats=600)                     # 0.333
obp = bb.on_base_percentage(hits=200, walks=70, hit_by_pitch=5,
                            at_bats=600, sacrifice_flies=5)         # 0.404
tb  = bb.total_bases(hits=200, doubles=40, triples=5, home_runs=35) # 355
slg = bb.slugging_percentage(tb, at_bats=600)                       # 0.592
print(f"{avg:.3f}/{obp:.3f}/{slg:.3f}  OPS {bb.ops(obp, slg):.3f}")

# Advanced stats
bb.woba(walks=70, hit_by_pitch=5, singles=120, doubles=40, triples=5,
        home_runs=35, at_bats=600, sacrifice_flies=5)               # ~0.416
bb.fip(home_runs=18, walks=45, hit_by_pitch=5, strikeouts=190,
       innings_pitched=180)                                         # ~3.19
bb.era(earned_runs=3, innings_pitched=bb.innings(6.2))              # 4.05
```

### Fetch MLB data

```python
from pyhomerun import MLBClient

mlb = MLBClient()

# Find a player and pull their season batting line
judge = mlb.search_players("Aaron Judge")[0]
splits = mlb.player_stats(judge["id"], group="hitting", season=2025)
line = splits[0]["stat"]
print(judge["fullName"], line["avg"], line["homeRuns"], line["ops"])

# Today's games
for game in mlb.schedule():
    away, home = game["teams"]["away"], game["teams"]["home"]
    print(f'{away["team"]["name"]} at {home["team"]["name"]} — {game["status"]["detailedState"]}')

# Standings
for division in mlb.standings(season=2025):
    for record in division["teamRecords"]:
        print(record["team"]["name"], record["wins"], record["losses"])
```

### Put them together

```python
import pyhomerun as bb

mlb = bb.MLBClient()
player = mlb.search_players("Juan Soto")[0]
s = mlb.player_stats(player["id"], group="hitting", season=2025)[0]["stat"]

singles = s["hits"] - s["doubles"] - s["triples"] - s["homeRuns"]
w = bb.woba(walks=s["baseOnBalls"], hit_by_pitch=s["hitByPitch"],
            singles=singles, doubles=s["doubles"], triples=s["triples"],
            home_runs=s["homeRuns"], at_bats=s["atBats"],
            intentional_walks=s["intentionalWalks"], sacrifice_flies=s["sacFlies"])
print(f'{player["fullName"]} wOBA: {w:.3f}')
```

## API reference

Every function has a full docstring with its formula and a worked example (`help(bb.woba)`).

### Batting

| Function | Statistic |
|---|---|
| `batting_average(h, ab)` | AVG |
| `on_base_percentage(h, bb, hbp, ab, sf)` | OBP |
| `total_bases(h, 2b, 3b, hr)` | TB |
| `slugging_percentage(tb, ab)` | SLG |
| `ops(obp, slg)` | OPS |
| `ops_plus(obp, slg, lg_obp, lg_slg)` | OPS+ (100 = league average) |
| `isolated_power(slg, avg)` | ISO |
| `babip(h, hr, ab, k, sf)` | BABIP |
| `woba(...)` | wOBA (customizable linear weights) |
| `wraa(woba, pa)` | wRAA (runs above average) |
| `plate_appearances(...)` | PA |
| `walk_rate(bb, pa)` / `strikeout_rate(k, pa)` | BB% / K% |
| `stolen_base_percentage(sb, cs)` | SB% |

### Pitching

| Function | Statistic |
|---|---|
| `innings(6.2)` / `innings_from_outs(20)` | Box-score notation → true innings |
| `era(er, ip)` | ERA |
| `whip(bb, h, ip)` | WHIP |
| `fip(hr, bb, hbp, k, ip)` | FIP (customizable constant) |
| `k_per_9` / `bb_per_9` / `hr_per_9` / `h_per_9` | Per-9 rates |
| `k_bb_ratio(k, bb)` | K/BB |
| `left_on_base_percentage(...)` | LOB% |
| `game_score(...)` | Bill James Game Score |

### Fielding

| Function | Statistic |
|---|---|
| `fielding_percentage(po, a, e)` | FPCT |
| `range_factor_per_game(po, a, g)` / `range_factor_per_9(po, a, inn)` | RF/G, RF/9 |
| `caught_stealing_percentage(cs, sb)` | CS% |

### MLB Stats API client

| Method | Returns |
|---|---|
| `MLBClient(timeout=10.0)` | — |
| `.search_players(name)` | Player matches (with MLBAM `id`) |
| `.player(player_id)` | Bio for one player |
| `.player_stats(id, group, stat_type, season)` | Stat splits (`"hitting"`/`"pitching"`/`"fielding"`; `"season"`/`"career"`/`"yearByYear"`/`"gameLog"`) |
| `.teams(season)` / `.roster(team_id)` | Teams / active roster |
| `.schedule(date, team_id)` | Games for a date (default today) |
| `.standings(season)` | Division standings |
| `.boxscore(game_pk)` / `.linescore(game_pk)` | Game details |
| `.get(path, **params)` | Any other endpoint, as parsed JSON |

All methods return plain dicts/lists parsed from the API's JSON — nothing is hidden, and `.get()` is an escape hatch to the API's [many other endpoints](https://statsapi.mlb.com/docs/). Errors raise `pyhomerun.MLBAPIError`.

## Conventions

- **Division by zero** never raises: rate stats return `0.0` (or `math.inf` for ERA-style stats when runs scored without an out recorded). See each module's docstring.
- **Innings** must be *true* innings (6⅔, not the box-score `6.2`) — convert with `innings()`.
- **League constants**: `woba` and `fip` ship with representative modern-era defaults. For season-exact work, pass your own `WobaWeights` / FIP constant using values from the free [FanGraphs Guts!](https://www.fangraphs.com/guts.aspx) page.
- **Typed**: the package ships a `py.typed` marker; all functions are annotated.

## Running the tests

No test framework needed:

```bash
python -m unittest discover tests -v
```

(The suite also works under `pytest` if you prefer it.) The MLB client tests are fully offline — they never touch the network — and every docstring example runs as a doctest.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: keep it dependency-free, add a docstring with formula + example to every public function, and include tests.

## License and data

Code is [MIT licensed](LICENSE). Data from the MLB Stats API is subject to the [MLB copyright notice](http://gdx.mlb.com/components/copyright.txt); this project is not affiliated with or endorsed by MLB.
