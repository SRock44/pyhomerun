# Roadmap

## Core mission

`pyhomerun` is a baseball statistics and MLB data library for Python that installs **zero third-party dependencies** — runtime code uses only the standard library, and the test suite runs with stock `unittest`. This is not a starting constraint we intend to relax as the library grows; it's the point of the library. Every item below is scoped to be buildable on `urllib`, `json`, `csv`, `sqlite3`, `difflib`, `statistics`, `argparse`, `dataclasses`, and friends. A proposal that needs `requests`, `pandas`, `numpy`, or similar belongs in a different project, or as a documented *optional* integration that the core never imports.

If a future feature turns out to genuinely require a third-party package, the answer is not "add it as a dependency" — it's "write an adapter the user opts into," "implement the 20% of the package we actually need," or "leave it out." See [CONTRIBUTING.md](CONTRIBUTING.md) for the same rule stated as a contribution guideline.

## Shipped

- **v0.1.0** — Batting/pitching/fielding sabermetrics (AVG through wOBA/FIP), `MLBClient` for the MLB Stats API, fully typed, doctested.
- **v0.2.0** — `BattingLine`/`PitchingLine` stat-line dataclasses with `from_mlb()` and `+`, wRC/wRC+/Runs Created, ERA+/ERA-/xFIP, team-level Pythagorean win expectation and magic number.
- **v0.3.0** — `pyhomerun` CLI (`standings`, `scores`, `player`, `teams`, `roster`), typo-tolerant `find_player()`, optional on-disk response caching (`cache_ttl`).
- **v0.4.0** — `situational` module with the RE24 run-expectancy matrix (`run_expectancy()`, `run_value()`); CSV export (`to_csv()`) and a `pyhomerun export` CLI subcommand; `MLBClient` retry with backoff (`retries`, `backoff_factor`); new `MLBClient` endpoints (`play_by_play`, `venues`, `awards`, `award_recipients`, `draft`).
- **v0.5.0** — `StatcastClient` for Baseball Savant's exit velocity/launch angle/spin rate CSV export, with defensive error handling (`StatcastError`) rather than a bare escape hatch; `MLBClient.teams(sport_id=...)` and `MLBClient.sports()` for minor-league team/level lookups, plus `MINOR_LEAGUE_SPORT_IDS`.
- **v0.6.0** — ML-friendly bulk export, pulled forward from the original v1.0.0 plan: `to_records()`/`to_dict(records=...)` return plain `list`/`dict` shapes (no pyhomerun objects) that `pandas.DataFrame(...)` accepts directly; `to_numpy()`/`to_dataframe()` build on those with a lazy, function-body-only `import numpy`/`import pandas` — pyhomerun still installs nothing else, and both work on Statcast rows as well as `BattingLine`/`PitchingLine` collections. `numpy`/`pandas` are available as opt-in extras (`pip install pyhomerun[numpy]`, `pyhomerun[pandas]`) purely for convenience.
- **v0.7.0** — Performance: `dataclass(slots=True)` for `BattingLine`/`PitchingLine` on Python 3.10+ (lower memory, faster attribute access); `MLBClient.player_stats_bulk()` for concurrent (thread-pooled) player-stat fetches; ~2.3x faster `StatcastClient` CSV parsing via column-wise dtype inference instead of per-cell `try/except`. All measured in `benchmarks/bench.py`, all stdlib-only.
- **v0.8.0** — Simulation and season tools: `pyhomerun.elo`'s `EloRatings` for self-updating team power ratings (`record_game()`, `win_probability()`, `regress_to_mean()` across seasons); `pyhomerun.simulate`'s `simulate_remaining_season()`/`simulation_odds()` for a `random`-only Monte Carlo playoff-odds engine, with `top_n_qualifies()`/`mlb_playoff_qualifiers()` covering division and wild-card races and `win_probability_from_win_pct()` (built on the new `team.log5_win_probability()`) as the no-Elo-required path in. `MLBClient.schedule()` gained `start_date`/`end_date` for pulling a full season in one call. New CLI commands `pyhomerun elo` and `pyhomerun playoff-odds` wire it all together against live data. Still stdlib-only — the simulator's `max_workers` option uses `concurrent.futures.ProcessPoolExecutor`, same as `player_stats_bulk()`'s thread pool.

## v1.0.0 — planned: the big one

The 1.0 release is where `pyhomerun` commits to being a serious base for ML/AI baseball work, not just a stats calculator. Big features, plus closing whatever gaps in stat/endpoint coverage remain from the 0.x releases before the public API locks in.

- **Full Statcast + play-by-play**: promote Statcast from v0.5.0's resilience-first integration to a first-class, fully-typed, fully-tested feature, paired with a stable play-by-play parser — the raw material for pitch-level and event-level models.
- **Standings/schedule helpers**: games-back computation, division/wild-card race summaries, "magic number for every team in a division" in one call — carried over from the original v0.8.0 plan.
- **Gap-filling pass**: audit every stat, endpoint, and CLI command shipped since v0.1.0 for missing edge cases, inconsistent conventions, or thin test coverage, and fix them here — 1.0 is the version where the public API stops changing shape.

## v1.1.0 and beyond — exploratory

These need more validation before committing to an API:

- **Plain-text visualizations**: ASCII win-probability graphs, spray charts as a coordinate grid — no charting library, just `str` and math. Nice-to-have, not core.

## How to influence this

Open an issue with the stat, endpoint, or workflow you want and, if it's a sabermetric addition, a link to its formula (FanGraphs glossary, Baseball Reference, a paper). PRs that follow [CONTRIBUTING.md](CONTRIBUTING.md) — zero dependencies, formula + doctest in every public docstring, tests for the happy path and the zero/edge case — are the fastest way to see something land ahead of this roadmap's own pace.
