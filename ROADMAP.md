# Roadmap

## Core mission

`pyhomerun` is a baseball statistics and MLB data library for Python that installs **zero third-party dependencies** — runtime code uses only the standard library, and the test suite runs with stock `unittest`. This is not a starting constraint we intend to relax as the library grows; it's the point of the library. Every item below is scoped to be buildable on `urllib`, `json`, `csv`, `sqlite3`, `difflib`, `statistics`, `argparse`, `dataclasses`, and friends. A proposal that needs `requests`, `pandas`, `numpy`, or similar belongs in a different project, or as a documented *optional* integration that the core never imports.

If a future feature turns out to genuinely require a third-party package, the answer is not "add it as a dependency" — it's "write an adapter the user opts into," "implement the 20% of the package we actually need," or "leave it out." See [CONTRIBUTING.md](CONTRIBUTING.md) for the same rule stated as a contribution guideline.

## Shipped

- **v0.1.0** — Batting/pitching/fielding sabermetrics (AVG through wOBA/FIP), `MLBClient` for the MLB Stats API, fully typed, doctested.
- **v0.2.0** — `BattingLine`/`PitchingLine` stat-line dataclasses with `from_mlb()` and `+`, wRC/wRC+/Runs Created, ERA+/ERA-/xFIP, team-level Pythagorean win expectation and magic number.
- **v0.3.0** — `pyhomerun` CLI (`standings`, `scores`, `player`, `teams`, `roster`), typo-tolerant `find_player()`, optional on-disk response caching (`cache_ttl`).
- **v0.4.0** *(this PR)* — `situational` module with the RE24 run-expectancy matrix (`run_expectancy()`, `run_value()`); CSV export (`to_csv()`) and a `pyhomerun export` CLI subcommand; `MLBClient` retry with backoff (`retries`, `backoff_factor`); new `MLBClient` endpoints (`play_by_play`, `venues`, `awards`, `award_recipients`, `draft`).

## v0.5.0 — Simulation and season tools

- **Monte Carlo season/playoff simulator**: `random`-only simulator that takes team strength (from Pythagorean record or user input) and a remaining schedule, and estimates playoff odds via repeated simulation. No dependency needed — `random.random()` and a loop is the whole engine.
- **Standings/schedule helpers**: games-back computation, division/wild-card race summaries, "magic number for every team in a division" in one call.
- **`sqlite3`-backed local cache** as an alternative to the current file-per-URL disk cache, for people who want to build a season's worth of local data (e.g. `pyhomerun sync 2025` populates a local db; stats can then run entirely offline).

## v0.6.0 and beyond — exploratory

These need more validation before committing to an API:

- **Statcast data** (exit velocity, launch angle, spin rate) via Baseball Savant's CSV export endpoints — feasible with `urllib` + `csv`, but Savant's download URLs aren't a documented stable API, so this needs a resilience plan (graceful failure, clear error messages) before it ships as a first-class feature rather than a `.get()`-style escape hatch.
- **Historical/minor-league data**: the MLB Stats API's `sportId` parameter already exposes minor league data; a thin set of convenience wrappers (`mlb.teams(sport_id=...)`) could make this more discoverable without new endpoints.
- **Plain-text visualizations**: ASCII win-probability graphs, spray charts as a coordinate grid — no charting library, just `str` and math. Nice-to-have, not core.

## How to influence this

Open an issue with the stat, endpoint, or workflow you want and, if it's a sabermetric addition, a link to its formula (FanGraphs glossary, Baseball Reference, a paper). PRs that follow [CONTRIBUTING.md](CONTRIBUTING.md) — zero dependencies, formula + doctest in every public docstring, tests for the happy path and the zero/edge case — are the fastest way to see something land ahead of this roadmap's own pace.
