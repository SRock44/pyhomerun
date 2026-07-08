"""CSV export for stat lines, via the standard library ``csv`` module.

A zero-dependency escape hatch into Excel, Google Sheets, pandas, or
anything else that reads CSV — pyhomerun does the sabermetrics, the
spreadsheet does the rest.

Example::

    from pyhomerun import BattingLine, to_csv

    lines = {"Aaron Judge": BattingLine(at_bats=550, hits=180, home_runs=53)}
    print(to_csv(lines))
"""

from __future__ import annotations

import csv
import dataclasses
import io
from typing import IO, Iterable, Mapping, Optional, Union

from .lines import BattingLine, PitchingLine

__all__ = ["to_csv"]

#: Derived stats (zero-arg properties or methods) included as extra columns.
_BATTING_DERIVED = ("avg", "obp", "slg", "ops", "iso", "babip")
_PITCHING_DERIVED = ("era", "whip", "k_per_9", "bb_per_9", "fip")

Line = Union[BattingLine, PitchingLine]


def _derived_fields(line: Line) -> Iterable[str]:
    if isinstance(line, BattingLine):
        return _BATTING_DERIVED
    if isinstance(line, PitchingLine):
        return _PITCHING_DERIVED
    raise TypeError(f"to_csv() supports BattingLine/PitchingLine, not {type(line).__name__}")


def to_csv(
    lines: Union[Mapping[str, Line], Iterable[Line]],
    file: Optional[IO[str]] = None,
) -> Optional[str]:
    """Export a collection of stat lines to CSV.

    Args:
        lines: A mapping of label (e.g. player name) to line — adds a
            leading ``name`` column — or a plain iterable of lines.
            Every line must be the same type (all ``BattingLine`` or all
            ``PitchingLine``).
        file: A writable text file to write to. If omitted, the CSV text
            is returned instead of being written anywhere.

    Returns:
        The CSV text, or ``None`` if ``file`` was given.

    >>> from pyhomerun import BattingLine
    >>> lines = {"Aaron Judge": BattingLine(at_bats=550, hits=180, home_runs=53, walks=110)}
    >>> print(to_csv(lines).splitlines()[0])
    name,at_bats,hits,doubles,triples,home_runs,walks,intentional_walks,hit_by_pitch,strikeouts,sacrifice_flies,sacrifice_hits,stolen_bases,caught_stealing,avg,obp,slg,ops,iso,babip
    """
    labeled = isinstance(lines, Mapping)
    items = list(lines.items()) if labeled else [(None, line) for line in lines]

    buffer = io.StringIO()
    if items:
        first = items[0][1]
        line_type = type(first)
        fields = [f.name for f in dataclasses.fields(first)]
        derived = list(_derived_fields(first))
        columns = (["name"] if labeled else []) + fields + derived
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        for label, line in items:
            if type(line) is not line_type:
                raise TypeError(
                    f"to_csv() requires every line to be the same type, "
                    f"got {line_type.__name__} and {type(line).__name__}"
                )
            row = {f: getattr(line, f) for f in fields}
            for name in derived:
                value = getattr(line, name)
                row[name] = value() if callable(value) else value
            if labeled:
                row["name"] = label
            writer.writerow(row)

    text = buffer.getvalue()
    if file is None:
        return text
    file.write(text)
    return None
