# Changelog

## 0.1.0 (2026-07-07)

Initial release.

- Batting stats: AVG, OBP, SLG, OPS, OPS+, TB, ISO, BABIP, wOBA, wRAA, PA, BB%, K%, SB%
- Pitching stats: ERA, WHIP, FIP, K/9, BB/9, HR/9, H/9, K/BB, LOB%, Game Score, innings conversion helpers
- Fielding stats: FPCT, RF/G, RF/9, CS%
- `MLBClient`: zero-dependency client for the MLB Stats API (player search, player stats, teams, rosters, schedule, standings, boxscore, linescore, raw `get`)
- Fully typed (`py.typed`), stdlib-only test suite with doctests
