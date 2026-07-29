# ⚾ pyhomerun

**Baseball statistics and MLB data for Python — with zero dependencies.**

[![PyPI](https://img.shields.io/pypi/v/pyhomerun.svg)](https://pypi.org/project/pyhomerun/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

`pyhomerun` does five things:

1. **Sabermetrics** — pure functions and stat-line dataclasses for batting, pitching, fielding, and team statistics (AVG, OBP, SLG, OPS, wOBA, wRC+, ERA, FIP, xFIP, Pythagorean win expectation, log5, ...), plus situational run-expectancy (RE24). Plain numbers in, plain numbers out.
2. **MLB data** — `MLBClient`, a tiny client for the free, key-less [MLB Stats API](https://statsapi.mlb.com) (players, season stats, teams, rosters, schedules, standings, boxscores, play-by-play), with optional disk caching, retry with backoff, typo-tolerant player lookup, and concurrent bulk fetching for many players at once.
3. **CSV/dict/array export** — `to_csv()`, `to_records()`/`to_dict()`, and `to_numpy()`/`to_dataframe()` turn a collection of stat lines (or Statcast rows) into CSV, plain Python data, or a numpy array/pandas DataFrame — no third-party library required unless you reach for the last two.
4. **Power ratings and season simulation** — `EloRatings` for self-updating team Elo, and `simulate_remaining_season()`/`simulation_odds()` for Monte Carlo division and wild-card odds off those ratings (or plain win percentages) and the remaining schedule.
5. **A terminal command** — `pyhomerun standings`, `pyhomerun scores`, `pyhomerun player "..."`, `pyhomerun elo`, `pyhomerun playoff-odds`, `pyhomerun export ...` for a quick look without writing any Python.

It is built **entirely on the Python standard library** — installing it installs nothing else, and the test suite runs with stock Python. `to_numpy()`/`to_dataframe()` are the one exception, and even those only `import numpy`/`import pandas` lazily, inside the function body, when you actually call them. Where stdlib-only concurrency helps at scale, it's used: `MLBClient.player_stats_bulk()` and `simulate_remaining_season(max_workers=...)` both build on `concurrent.futures`. As of v0.7.0 the library's also been tuned for speed and memory where it matters for ML/AI workflows — see [Performance](#performance).

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

Requires Python 3.9+. If you want `to_numpy()`/`to_dataframe()`, install the matching extra (or already have numpy/pandas around — pyhomerun doesn't care how they got there):

```bash
pip install pyhomerun[numpy]
pip install pyhomerun[pandas]
```

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

### Team power ratings and playoff odds

```python
from pyhomerun import EloRatings, simulate_remaining_season, simulation_odds, top_n_qualifies

elo = EloRatings()
elo.record_game("Yankees", "Red Sox", home_score=5, away_score=3)
elo.record_game("Red Sox", "Yankees", home_score=6, away_score=2)
elo.ranked()                              # [("Red Sox", ~1500.0), ("Yankees", ~1500.0)] -- split series, near even

current_wins = {"Yankees": 85, "Red Sox": 85}
remaining = [("Yankees", "Red Sox"), ("Red Sox", "Yankees")]
sims = simulate_remaining_season(current_wins, remaining, elo.win_probability)
odds = simulation_odds(sims, top_n_qualifies(current_wins, n=1))
odds["Yankees"]                           # ~0.75 -- fraction of simulated seasons the Yankees finished on top
```

No Elo history yet? `win_probability_from_win_pct()` builds the same `win_probability` callable straight from plain winning percentages (via `log5_win_probability()`), and `mlb_playoff_qualifiers(divisions, wildcard_spots=3)` models MLB's real division-winner-plus-wild-card format instead of a flat top-N. `pyhomerun elo` and `pyhomerun playoff-odds` run this whole pipeline against live MLB data from the terminal — see [From the terminal](#from-the-terminal).

### Situational stats: run expectancy

```python
from pyhomerun import BaseOutState, run_expectancy, run_value

# Runner on second, one out: how many runs does a team expect to score?
run_expectancy(BaseOutState(on_second=True, outs=1))       # 0.644

# A walk with the bases empty and nobody out — its run value:
before = BaseOutState()
after = BaseOutState(on_first=True)
run_value(before, after, runs_scored=0)                    # 0.37
```

### CSV export

```python
from pyhomerun import to_csv

roster_lines = {"Aaron Judge": line, "Juan Soto": other_line}  # name -> BattingLine
to_csv(roster_lines)                        # CSV text
with open("roster.csv", "w", newline="") as f:
    to_csv(roster_lines, file=f)
```

### Bulk export: dicts, numpy, pandas

`to_records()`/`to_dict()` flatten stat lines (or already record-shaped data, like `StatcastClient.search()` output) into plain Python — no pyhomerun objects left in the result:

```python
from pyhomerun import BattingLine, to_records, to_dict

roster_lines = {"Aaron Judge": line, "Juan Soto": other_line}  # name -> BattingLine

to_records(roster_lines)                  # [{'name': 'Aaron Judge', 'at_bats': 550, ..., 'avg': 0.327}, ...]
to_dict(roster_lines)                     # {'name': [...], 'at_bats': [...], ..., 'avg': [...]} - columnar
to_dict(roster_lines, records=True)       # same shape as to_records()
```

`to_dict()`'s columnar shape is exactly what `pandas.DataFrame(...)` accepts, so `to_numpy()`/`to_dataframe()` are thin convenience wrappers around it — they `import numpy`/`import pandas` lazily, only inside the function body when called, so pyhomerun itself never depends on either:

```python
from pyhomerun import to_numpy, to_dataframe

arr = to_numpy(roster_lines)              # numpy structured array; arr["home_runs"]
df = to_dataframe(roster_lines)           # pandas DataFrame, one row per line

# Works on Statcast rows too - no BattingLine/PitchingLine required
from pyhomerun import StatcastClient
savant = StatcastClient()
pitches = savant.search("2024-06-01", "2024-06-30", player_id=660271)
to_dataframe(pitches)                     # one row per pitch
```

Calling `to_numpy()`/`to_dataframe()` without numpy/pandas installed raises a plain `ImportError` telling you which package to `pip install`.

### From the terminal

Installing the package also installs a `pyhomerun` command:

```bash
pyhomerun standings
pyhomerun scores 2025-10-01
pyhomerun player "Arron Judge"      # fuzzy: finds Aaron Judge despite the typo
pyhomerun teams
pyhomerun roster yankees
pyhomerun export hitting yankees --out yankees.csv
pyhomerun elo                        # power ratings from this season's completed games
pyhomerun playoff-odds --season 2025 # Monte Carlo division/wild-card odds
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
| `log5_win_probability(win_pct_a, win_pct_b)` | Bill James's log5 head-to-head probability |

### Elo power ratings

| Class / function | What it does |
|---|---|
| `EloRatings(initial=None, k=4.0, home_field_advantage=24.0)` | A live, self-updating set of team ratings |
| `.record_game(home, away, home_score, away_score)` | Update both teams' ratings from a final score |
| `.win_probability(home, away)` | P(home wins), including home-field advantage |
| `.regress_to_mean(factor=1/3, mean=1500.0)` | Pull ratings partway back to average between seasons |
| `.ranked()` / `.ratings()` | Every team, strongest first / a plain `{team: rating}` snapshot |
| `expected_score(rating_a, rating_b)` / `update_elo(rating_a, rating_b, score_a, k=4.0)` | The underlying Elo logistic curve and update, without home-field or state |

### Monte Carlo season simulation

| Function | What it does |
|---|---|
| `simulate_remaining_season(current_wins, remaining_games, win_probability, n_simulations=10000, rng=None, max_workers=None)` | Replays the rest of a season `n_simulations` times; `{team: [final_win_total, ...]}` |
| `simulation_odds(simulated_wins, qualifies)` | Fraction of simulations in which each team qualifies, given a `qualifies` rule |
| `top_n_qualifies(teams, n)` | `qualifies` factory: the `n` teams with the most wins |
| `mlb_playoff_qualifiers(divisions, wildcard_spots=3)` | `qualifies` factory shaped like MLB's real format: division winners plus pooled wild cards |
| `win_probability_from_win_pct(win_pct)` | `win_probability` adapter built on `log5_win_probability()` — no `EloRatings` required |

### Situational

| Function | Statistic |
|---|---|
| `run_expectancy(BaseOutState(...))` | RE24: expected rest-of-inning runs for a base-out state |
| `run_value(before, after, runs_scored)` | Run value of a play (change in expectancy + runs scored) |
| `RE24_TABLE` | The underlying `{BaseOutState: float}` matrix — swap in your own for exact per-season values |

### Stat lines

| Class | What it does |
|---|---|
| `BattingLine` | Counting stats in; `avg`, `obp`, `slg`, `ops`, `iso`, `babip`, `walk_rate`, ... as properties, plus `woba()`, `wraa()`, `wrc()`, `wrc_plus()`, `runs_created()`, `slash()` |
| `PitchingLine` | Stores innings as `outs` for exact addition; `era`, `whip`, `k_per_9`, `lob%`, ... as properties, plus `fip()`, `era_plus()`, `era_minus()` |
| `*.from_mlb(split)` | Build either line directly from an `MLBClient.player_stats()` split |
| `line + line` | Combine splits/seasons field-by-field |
| `to_csv(lines, file=None)` | Export a mapping or iterable of lines to CSV (returns text, or writes to `file`) |
| `to_records(lines)` | Flatten lines (or dict-like rows, e.g. Statcast) into a `list` of plain `dict` |
| `to_dict(lines, records=False)` | Columnar `{column: [values]}` by default (ready for `pandas.DataFrame(...)`), or `records=True` for the `to_records()` shape |
| `to_numpy(lines, dtype=None)` | Numpy structured array — requires numpy (`pip install pyhomerun[numpy]`), imported lazily |
| `to_dataframe(lines)` | Pandas `DataFrame` — requires pandas (`pip install pyhomerun[pandas]`), imported lazily |

### MLB Stats API client

| Method | Returns |
|---|---|
| `MLBClient(timeout=10.0, cache_ttl=None, cache_dir=None, retries=0, backoff_factor=0.5)` | — pass `cache_ttl` (seconds) to cache responses on disk, `retries` for transient-failure retry with backoff |
| `.search_players(name)` | Player matches (with MLBAM `id`) |
| `.find_player(name)` | Best-match player, tolerant of a typo in one name part (see docstring for what it can/can't fix) |
| `.player(player_id)` | Bio for one player |
| `.player_stats(id, group, stat_type, season)` | Stat splits (`"hitting"`/`"pitching"`/`"fielding"`; `"season"`/`"career"`/`"yearByYear"`/`"gameLog"`) |
| `.player_stats_bulk(player_ids, group, stat_type, season, max_workers=8)` | `{player_id: splits}` for many players at once, fetched concurrently — see [Performance](#performance) |
| `.teams(season)` / `.roster(team_id)` | Teams / active roster |
| `.schedule(date, team_id, start_date, end_date)` | Games for a date (default today), or a `start_date`/`end_date` range (e.g. a full season) |
| `.standings(season)` | Division standings |
| `.boxscore(game_pk)` / `.linescore(game_pk)` | Game details |
| `.play_by_play(game_pk)` | Every play of a game, in order |
| `.venues()` | All MLB ballparks |
| `.awards()` / `.award_recipients(award_id, season)` | Awards / winners of one award |
| `.draft(year)` | Every pick of the amateur draft for a year |
| `.get(path, **params)` | Any other endpoint, as parsed JSON |

All methods return plain dicts/lists parsed from the API's JSON — nothing is hidden, and `.get()` is an escape hatch to the API's [many other endpoints](https://statsapi.mlb.com/docs/). Errors raise `pyhomerun.MLBAPIError`.

## Conventions

- **Division by zero** never raises: rate stats return `0.0` (or `math.inf` for ERA-style stats when runs scored without an out recorded). See each module's docstring.
- **Innings** must be *true* innings (6⅔, not the box-score `6.2`) — convert with `innings()`.
- **League constants**: `woba` and `fip` ship with representative modern-era defaults. For season-exact work, pass your own `WobaWeights` / FIP constant using values from the free [FanGraphs Guts!](https://www.fangraphs.com/guts.aspx) page.
- **Typed**: the package ships a `py.typed` marker; all functions are annotated.

## Performance

`pyhomerun` targets ML/AI-scale baseball workflows — building feature sets from thousands of player-seasons, or pulling a season of Statcast pitches — and v0.7.0 is a dedicated performance pass for exactly that. Every number below comes from [`benchmarks/bench.py`](benchmarks/bench.py); run it yourself:

```bash
python benchmarks/bench.py
```

- **Lower memory per stat line.** On Python 3.10+, `BattingLine`/`PitchingLine` use `dataclass(slots=True)` — no per-instance `__dict__` — so building a dataset of thousands of lines for feature extraction costs less memory. (3.9 falls back to the old `__dict__`-based behavior automatically; nothing to configure.)
- **~7x faster bulk player-stat fetches.** `MLBClient.player_stats_bulk(player_ids, ...)` fetches many players' stats concurrently on a small thread pool (`concurrent.futures`, standard library — no new dependency). MLB Stats API calls are network-latency-bound, not CPU-bound, so overlapping them is the single biggest real-world speedup available for building a training set across a roster or league:

  ```python
  mlb = bb.MLBClient()
  ids = [p["id"] for p in mlb.roster(147)]  # every Yankee, e.g.
  stats = mlb.player_stats_bulk(ids, group="hitting", season=2025, max_workers=8)
  # {player_id: [splits...]}
  ```

- **~2.3x faster Statcast CSV parsing.** `StatcastClient` now infers each column's dtype once (numeric vs. string) from its first non-empty value, instead of `try: float(v)`-ing every cell — a real cost when most of a Statcast pull's ~90 columns are categorical (`pitch_type`, `player_name`, `des`, ...) and only a handful are numeric.
- **Honest about what didn't help.** We also benchmarked an `operator.attrgetter()`-batched rewrite of `to_records()`/`to_dict()` and measured it ~10% *slower* than the existing per-field loop — attribute access on a `__slots__` dataclass is already about as fast as pure Python gets, so batching it added overhead instead of removing it. That rewrite was reverted rather than shipped; see the comment in `benchmarks/bench.py` for the numbers. `to_records()` already runs at roughly half a million lines/sec on a typical machine.

All of this is still **zero third-party dependencies** — the "lightest" half of the claim was already true (no `pandas`/`numpy`/`requests` pulled in just to import `pyhomerun`), and this release is what makes "fastest" backed by actual measurements rather than assertion.

## Running the tests

No test framework needed:

```bash
python -m unittest discover tests -v
```

(The suite also works under `pytest` if you prefer it.) The MLB client tests are fully offline — they never touch the network — and every docstring example runs as a doctest.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for what's planned — a 1.0.0 that promotes Statcast/play-by-play to first-class, adds standings/schedule helpers, and closes out remaining coverage gaps before the public API locks in. All still zero required third-party dependencies (`to_numpy()`/`to_dataframe()` are opt-in extras, never a hard install). That constraint is the project's core mission, not a starting default — see [Performance](#performance) for how v0.7.0 made it faster without loosening it.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: keep it dependency-free, add a docstring with formula + example to every public function, and include tests.

## License and data

Code is [MIT licensed](LICENSE). Data from the MLB Stats API is subject to the [MLB copyright notice](http://gdx.mlb.com/components/copyright.txt); this project is not affiliated with or endorsed by MLB.
