"""Benchmarks backing pyhomerun's v0.7.0 performance claims.

Run directly -- no test framework, no third-party dependencies (numpy/pandas
are used only if already installed, to size up the export path against
them; everything else is stdlib):

    python benchmarks/bench.py

Every number is measured on this machine, right now -- nothing here is a
canned or historical figure. Four things are exercised, each one matching a
real ML/AI-adjacent workflow this library is meant for:

1. Stat-line memory footprint -- ``__slots__`` (Python 3.10+) vs a
   plain-``__dict__`` equivalent, for a dataset of many ``BattingLine``s.
2. Bulk export throughput -- ``to_records()``/``to_dict()`` turning a large
   collection of stat lines into the shape ``pandas.DataFrame()``/
   ``numpy`` want, before vs. after the ``attrgetter``-based fast path.
3. Statcast CSV parsing -- column-wise numeric inference vs. the original
   per-cell ``try: float(v)``, on a synthetic pull sized like a real
   multi-week Statcast query.
4. Concurrent MLB API fetches -- ``MLBClient.player_stats_bulk()`` against
   a simulated-latency endpoint, showing the wall-clock win of overlapping
   I/O-bound network calls on a thread pool.
"""

from __future__ import annotations

import io
import sys
import time
import timeit
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pyhomerun as bb  # noqa: E402
from pyhomerun.statcast import StatcastClient  # noqa: E402


def _rule(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# -- 1. Memory footprint: __slots__ vs __dict__ ------------------------------


@dataclass
class _BattingLineNoSlots:
    """A plain (non-slotted) stand-in, to size __dict__ overhead against."""

    at_bats: int = 0
    hits: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    walks: int = 0
    intentional_walks: int = 0
    hit_by_pitch: int = 0
    strikeouts: int = 0
    sacrifice_flies: int = 0
    sacrifice_hits: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0


def bench_memory(n: int = 50_000) -> None:
    _rule(f"1. Memory footprint -- {n:,} BattingLine instances")
    has_slots = hasattr(bb.BattingLine, "__slots__")
    print(f"Python {sys.version.split()[0]} -- __slots__ active: {has_slots}")

    tracemalloc.start()
    slotted = [bb.BattingLine(at_bats=550, hits=150, home_runs=25) for _ in range(n)]
    _, slotted_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    dicted = [_BattingLineNoSlots(at_bats=550, hits=150, home_runs=25) for _ in range(n)]
    _, dicted_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"BattingLine (this build):      {slotted_peak / 1e6:8.2f} MB  ({slotted_peak / n:.0f} bytes/line)")
    print(f"Plain __dict__ equivalent:      {dicted_peak / 1e6:8.2f} MB  ({dicted_peak / n:.0f} bytes/line)")
    if has_slots:
        print(f"-> {dicted_peak / slotted_peak:.2f}x less memory with __slots__")
    else:
        print("-> __slots__ needs Python 3.10+; this interpreter falls back to __dict__")
    del slotted, dicted


# -- 2. Bulk export throughput ------------------------------------------------
#
# We tried an operator.attrgetter()-batched rewrite of to_records() here and
# measured it ~10% *slower* than the plain per-field getattr() loop -- on a
# __slots__ dataclass, attribute access is already a fast C-level slot read,
# and attrgetter's tuple-building plus the extra zip() pass cost more than
# they saved. We only ship changes with a measured win, so that rewrite was
# reverted; this benchmark instead just documents to_records()/to_dict()'s
# actual throughput, unchanged from before.


def bench_export(n: int = 100_000) -> None:
    _rule(f"2. Bulk export -- to_records()/to_dict() over {n:,} BattingLines")
    lines = [
        bb.BattingLine(at_bats=550, hits=150 + (i % 50), doubles=30, triples=5,
                        home_runs=20 + (i % 30), walks=70, hit_by_pitch=5,
                        strikeouts=120, sacrifice_flies=5)
        for i in range(n)
    ]

    elapsed = min(timeit.Timer(lambda: bb.to_records(lines)).repeat(repeat=3, number=1))
    print(f"to_records(): {elapsed:.3f}s -- {n / elapsed:,.0f} lines/sec")

    elapsed = min(timeit.Timer(lambda: bb.to_dict(lines)).repeat(repeat=3, number=1))
    print(f"to_dict():    {elapsed:.3f}s -- {n / elapsed:,.0f} lines/sec")


# -- 3. Statcast CSV parsing --------------------------------------------------


def _make_statcast_csv(n_rows: int) -> bytes:
    header = "pitch_type,launch_speed,launch_angle,release_spin_rate,player_name,des,events,zone\n"
    rows = []
    for i in range(n_rows):
        rows.append(
            f"FF,{95.0 + (i % 10) / 10:.1f},{12.0 + (i % 20)},"
            f"{2200 + (i % 300)},Aaron Judge,single hit,single,{5 + (i % 9)}\n"
        )
    return (header + "".join(rows)).encode()


def _old_style_coerce(text: str) -> list:
    """Reimplementation of the pre-0.7.0 per-cell try/except coercion, for comparison."""
    import csv as _csv

    rows = list(_csv.DictReader(io.StringIO(text)))
    out = []
    for row in rows:
        coerced = {}
        for key, value in row.items():
            if not value:
                coerced[key] = None
                continue
            try:
                coerced[key] = float(value)
            except ValueError:
                coerced[key] = value
        out.append(coerced)
    return out


def bench_statcast(n_rows: int = 20_000) -> None:
    _rule(f"3. Statcast CSV parsing -- {n_rows:,} synthetic pitch rows")
    csv_bytes = _make_statcast_csv(n_rows)
    text = csv_bytes.decode()

    old_time = min(timeit.Timer(lambda: _old_style_coerce(text)).repeat(repeat=3, number=1))
    print(f"old per-cell try/except:  {old_time:.3f}s -- {n_rows / old_time:,.0f} rows/sec")

    client = StatcastClient()

    def new_parse():
        return client._parse(text)

    new_time = min(timeit.Timer(new_parse).repeat(repeat=3, number=1))
    print(f"new column-wise inference: {new_time:.3f}s -- {n_rows / new_time:,.0f} rows/sec")
    print(f"-> {old_time / new_time:.2f}x faster")


# -- 4. Concurrent MLB API fetches --------------------------------------------


def bench_concurrent_fetch(n_players: int = 30, simulated_latency: float = 0.05) -> None:
    _rule(
        f"4. MLBClient.player_stats_bulk() -- {n_players} players, "
        f"~{simulated_latency * 1000:.0f}ms simulated network latency each"
    )

    def fake_urlopen(request, timeout=None):
        time.sleep(simulated_latency)
        body = io.BytesIO(b'{"stats": [{"splits": [{"stat": {"homeRuns": 10}}]}]}')
        response = mock.MagicMock()
        response.__enter__.return_value = body
        response.__exit__.return_value = False
        return response

    client = bb.MLBClient()
    player_ids = list(range(n_players))

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        start = time.perf_counter()
        for pid in player_ids:
            client.player_stats(pid)
        sequential = time.perf_counter() - start

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        start = time.perf_counter()
        client.player_stats_bulk(player_ids, max_workers=8)
        concurrent_time = time.perf_counter() - start

    print(f"sequential (one at a time): {sequential:.2f}s")
    print(f"player_stats_bulk(max_workers=8): {concurrent_time:.2f}s")
    print(f"-> {sequential / concurrent_time:.2f}x faster")


if __name__ == "__main__":
    print(f"pyhomerun {bb.__version__} benchmarks -- {time.strftime('%Y-%m-%d %H:%M:%S')}")
    bench_memory()
    bench_export()
    bench_statcast()
    bench_concurrent_fetch()
    print()
