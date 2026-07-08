# ⚾ pyhomerun

**Baseball statistics and MLB data for Python — with zero dependencies.**

[![PyPI](https://img.shields.io/pypi/v/pyhomerun.svg)](https://pypi.org/project/pyhomerun/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

`pyhomerun` does three things:

1. **Sabermetrics** — pure functions and stat-line dataclasses for batting, pitching, fielding, and team statistics (AVG, OBP, SLG, OPS, wOBA, wRC+, ERA, FIP, xFIP, Pythagorean win expectation, ...). Plain numbers in, plain numbers out.
2. **MLB data** — `MLBClient`, a tiny client for the free, key-less [MLB Stats API](https://statsapi.mlb.com) (players, season stats, teams, rosters, schedules, standings, boxscores), with optional disk caching and typo-tolerant player lookup.
3. **A terminal command** — `pyhomerun standings`, `pyhomerun scores`, `pyhomerun player "..."` for a quick look without writing any Python.

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

### Put them together: stat lines

`BattingLine` and `PitchingLine` bundle counting stats and expose every derived stat — and they build straight from API responses, so there's no field-mapping glue:

```python
import pyhomerun as bb

mlb = bb.MLBClient()
player = mlb.search_players("Juan Soto")[0]
split = mlb.player_stats(player["id"], group="hitting", season=2025)[0]

line = bb.BattingLine.from_mlb(split)
print(player["fullName"], line.slash())      # 0.266/0.396/0.525
print(f"wOBA {line.woba():.3f}  wRC+ {line.wrc_plus():.0f}  BABIP {line.babip:.3f}")
```

Lines add together, so combining splits or seasons is just `+`:

```python
career = bb.BattingLine()
for split in mlb.player_stats(player["id"], group="hitting", stat_type="yearByYear"):
    career += bb.BattingLine.from_mlb(split)
print(career.slash(), career.home_runs)
```

You can also build lines by hand — every field defaults to 0:

```python
line = bb.BattingLine(at_bats=550, hits=150, doubles=30, triples=5, home_runs=25,
                      walks=70, hit_by_pitch=5, strikeouts=120, sacrifice_flies=5)
line.ops                       # 0.839...
line.wraa()                    # runs above average

arm = bb.PitchingLine(outs=540, hits=160, earned_runs=65, walks=50,
                      strikeouts=190, home_runs=18, hit_by_pitch=5)
arm.era, arm.whip, arm.fip()   # (3.25, 1.16..., 3.27...)
```

### Team math

```python
bb.pythagorean_expectation(800, 700)      # 0.566 expected win pct
bb.expected_wins(800, 700, games=162)     # 91.2 (Pythagenpat exponent)
bb.magic_number(leader_wins=90, second_place_losses=60)   # 13
```

### From the terminal

Installing the package also installs a `pyhomerun` command:

```bash
pyhomerun standings
pyhomerun scores 2025-10-01
pyhomerun player "Arron Judge"      # fuzzy: finds Aaron Judge despite the typo
pyhomerun teams
pyhomerun roster yankees
```

Responses are cached on disk for 5 minutes so re-running commands is instant and doesn't hammer the API. Same thing works as `python -m pyhomerun ...` if you'd rather not rely on the installed script being on `PATH`.

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
| `wrc(woba, pa)` / `wrc_plus(woba, park_factor)` | wRC / wRC+ (100 = league average) |
| `runs_created(h, bb, tb, ab)` | Runs Created (Bill James) |
| `plate_appearances(...)` | PA |
| `walk_rate(bb, pa)` / `strikeout_rate(k, pa)` | BB% / K% |
| `stolen_base_percentage(sb, cs)` | SB% |

### Pitching

| Function | Statistic |
|---|---|
| `innings(6.2)` / `innings_from_outs(20)` | Box-score notation → true innings |
| `era(er, ip)` | ERA |
| `era_plus(era, lg_era)` / `era_minus(era, lg_era)` | ERA+ / ERA- (100 = league average) |
| `whip(bb, h, ip)` | WHIP |
| `fip(hr, bb, hbp, k, ip)` | FIP (customizable constant) |
| `xfip(fb, bb, hbp, k, ip)` | xFIP (league HR/FB rate) |
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

### Team

| Function | Statistic |
|---|---|
| `run_differential(rs, ra)` | Run differential |
| `pythagorean_expectation(rs, ra, exponent=2)` | Pythagorean win % |
| `pythagenpat_exponent(rs, ra, g)` | Environment-aware exponent |
| `expected_wins(rs, ra, g)` | Expected win total (Pythagenpat) |
| `magic_number(leader_wins, second_losses)` | Clinch magic number |

### Stat lines

| Class | What it does |
|---|---|
| `BattingLine` | Counting stats in; `avg`, `obp`, `slg`, `ops`, `iso`, `babip`, `walk_rate`, ... as properties, plus `woba()`, `wraa()`, `wrc()`, `wrc_plus()`, `runs_created()`, `slash()` |
| `PitchingLine` | Stores innings as `outs` for exact addition; `era`, `whip`, `k_per_9`, `lob%`, ... as properties, plus `fip()`, `era_plus()`, `era_minus()` |
| `*.from_mlb(split)` | Build either line directly from an `MLBClient.player_stats()` split |
| `line + line` | Combine splits/seasons field-by-field |

### MLB Stats API client

| Method | Returns |
|---|---|
| `MLBClient(timeout=10.0, cache_ttl=None, cache_dir=None)` | — pass `cache_ttl` (seconds) to cache responses on disk |
| `.search_players(name)` | Player matches (with MLBAM `id`) |
| `.find_player(name)` | Best-match player, tolerant of a typo in one name part (see docstring for what it can/can't fix) |
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

## Roadmap

See [ROADMAP.md](ROADMAP.md) for what's planned — situational stats (RE24), CSV export, a season/playoff-odds simulator, and more, all still zero third-party dependencies. That constraint is the project's core mission, not a starting default.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: keep it dependency-free, add a docstring with formula + example to every public function, and include tests.

## License and data

Code is [MIT licensed](LICENSE). Data from the MLB Stats API is subject to the [MLB copyright notice](http://gdx.mlb.com/components/copyright.txt); this project is not affiliated with or endorsed by MLB.
