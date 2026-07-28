# Changelog

## 0.7.0 (2026-07-28)

Still zero dependencies. This release is entirely about performance and memory footprint — every number below is measured in `benchmarks/bench.py`, run it yourself with `python benchmarks/bench.py`.

- `BattingLine`/`PitchingLine` now use `dataclass(slots=True)` on Python 3.10+: no per-instance `__dict__`, meaningfully less memory per line and faster attribute access — matters when a dataset is thousands of lines built for ML feature extraction. A no-op fallback on 3.9, which keeps the old `__dict__`-based behavior.
- New `MLBClient.player_stats_bulk(player_ids, ...)`: fetches `player_stats()` for many players concurrently on a small thread pool (`concurrent.futures`, standard library). MLB Stats API calls are I/O-bound, not CPU-bound, so this is a ~7x wall-clock win pulling stats for a roster or league instead of looping one call at a time.
- `StatcastClient` CSV parsing is ~2.3x faster on typical pulls: column dtype (numeric vs. string) is now decided once per column from its first non-empty value instead of `try: float(v)`-ing every single cell, which used to raise and catch a `ValueError` for every string cell (`pitch_type`, `player_name`, `des`, ...). A per-cell fallback is kept as a safety net for a stray non-numeric value in an otherwise-numeric column. This also makes Statcast output columns consistently typed, matching the assumption `to_numpy()`/`to_dataframe()` already make.
- We also benchmarked an `operator.attrgetter()`-batched rewrite of `to_records()` and measured it ~10% *slower* than the existing per-field `getattr()` loop (attribute access on a slotted dataclass is already about as fast as pure Python gets) — reverted rather than shipped, and documented in `benchmarks/bench.py` so the reasoning isn't lost.

Measured on this machine (Python 3.13.3, see `benchmarks/bench.py` for the exact workload):

| Benchmark | Before | After | Result |
|---|---|---|---|
| `MLBClient.player_stats_bulk()`, 30 players, ~50ms latency each | 1.52s sequential | 0.21s (8 workers) | **7.35x faster** |
| `StatcastClient` CSV parsing, 20,000 pitch rows | 0.056s (357k rows/sec) | 0.024s (821k rows/sec) | **2.30x faster** |
| `BattingLine` memory, 50,000 instances | 193 bytes/line | 145 bytes/line | **1.33x less memory** |
| `to_records()`/`to_dict()` bulk export | ~500k lines/sec | unchanged | attrgetter rewrite tried, measured 10% slower, reverted |

## 0.6.0 (2026-07-25)

Still zero dependencies.

- New `pyhomerun.to_records()` / `to_dict(records=...)`: flatten `BattingLine`/`PitchingLine` collections (or already record-shaped data, like `StatcastClient.search()` output) into plain `list`/`dict` — no pyhomerun objects in the output. `to_dict()`'s default columnar shape is exactly what `pandas.DataFrame(...)` accepts.
- New `pyhomerun.to_numpy()` / `to_dataframe()`: convenience wrappers that build on the above with a lazy `import numpy` / `import pandas` inside the function body — pyhomerun itself never imports either and still installs nothing else. Raise a clear `ImportError` with an install hint if the optional package isn't there.
- `numpy` and `pandas` are now available as opt-in extras (`pip install pyhomerun[numpy]`, `pyhomerun[pandas]`) for convenience; installing plain `pyhomerun` still pulls in nothing beyond the standard library.
- `to_csv()` is now implemented on top of `to_records()` internally; its behavior and output are unchanged.

## 0.5.0 (2026-07-09)

Still zero dependencies.

- New `StatcastClient`: exit velocity, launch angle, and spin rate via Baseball Savant's CSV export, with defensive error handling (`StatcastError`) since it's an undocumented endpoint rather than a stable API
- `MLBClient.teams(sport_id=...)` and new `MLBClient.sports()`: minor-league team/level lookups, plus a `MINOR_LEAGUE_SPORT_IDS` convenience mapping (Triple-A through Rookie)
- Fixed a duplicate import in `pyhomerun/__init__.py`

## 0.4.0 (2026-07-08)

Still zero dependencies.

- New `situational` module: the published 24-base-out-state run-expectancy (RE24) matrix as data, plus `run_expectancy()` and `run_value()` for computing the run value of a play
- `to_csv()`: export `BattingLine`/`PitchingLine` collections to CSV via the stdlib `csv` module; new `pyhomerun export <hitting|pitching> <team>` CLI subcommand
- `MLBClient(retries=..., backoff_factor=...)`: bounded retry with exponential backoff for transient failures (5xx responses, network errors), off by default
- New `MLBClient` endpoints: `play_by_play()`, `venues()`, `awards()`, `award_recipients()`, `draft()`

## 0.3.0 (2026-07-07)

Still zero dependencies.

- `pyhomerun` CLI (also `python -m pyhomerun`): `standings`, `scores [date]`, `player <name>`, `teams`, `roster <team>`
- `MLBClient.find_player(name)`: typo-tolerant player lookup (recovers from a misspelling in one name part, using the API's own search plus `difflib` re-ranking)
- `MLBClient(cache_ttl=..., cache_dir=...)`: optional on-disk response caching, off by default
- Added `ROADMAP.md`

## 0.2.0 (2026-07-07)

Still zero dependencies.

- `BattingLine` / `PitchingLine` stat-line dataclasses: build from raw counts or directly from MLB Stats API splits (`from_mlb`), get every derived stat as a property/method, and combine lines with `+`
- New batting stats: wRC, wRC+ (with park factor), Runs Created
- New pitching stats: ERA+, ERA-, xFIP
- New `team` module: run differential, Pythagorean expectation, Pythagenpat exponent, expected wins, magic number
- `WobaWeights` gains `league_runs_per_pa` (used by wRC/wRC+)

## 0.1.0 (2026-07-07)

Initial release.

- Batting stats: AVG, OBP, SLG, OPS, OPS+, TB, ISO, BABIP, wOBA, wRAA, PA, BB%, K%, SB%
- Pitching stats: ERA, WHIP, FIP, K/9, BB/9, HR/9, H/9, K/BB, LOB%, Game Score, innings conversion helpers
- Fielding stats: FPCT, RF/G, RF/9, CS%
- `MLBClient`: zero-dependency client for the MLB Stats API (player search, player stats, teams, rosters, schedule, standings, boxscore, linescore, raw `get`)
- Fully typed (`py.typed`), stdlib-only test suite with doctests
