# Changelog

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
