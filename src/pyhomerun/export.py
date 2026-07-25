"""CSV/dict/array export for stat lines, via the standard library.

A zero-dependency escape hatch into Excel, Google Sheets, pandas, numpy, or
anything else that reads CSV or plain Python data — pyhomerun does the
sabermetrics, the rest of your pipeline does the rest.

* :func:`to_csv` — CSV text, via the stdlib ``csv`` module.
* :func:`to_records` / :func:`to_dict` — plain ``list``/``dict`` shapes,
  no pyhomerun objects left in the output. ``to_dict()``'s default
  columnar shape is exactly what ``pandas.DataFrame(...)`` wants; a
  record from ``to_records()`` is one row of that frame.
* :func:`to_numpy` / :func:`to_dataframe` — thin convenience wrappers
  around the two above that lazily ``import numpy``/``import pandas``
  *inside the function body*, only when you call them. pyhomerun itself
  never imports either and does not declare them as dependencies —
  installing pyhomerun installs nothing else; install numpy/pandas
  yourself if you use these two.

All five accept the same inputs: a ``{label: line}`` mapping or plain
iterable of :class:`~pyhomerun.BattingLine`/:class:`~pyhomerun.PitchingLine`,
or already record-shaped data such as
:meth:`~pyhomerun.StatcastClient.search` results.

Example::

    from pyhomerun import BattingLine, to_csv, to_dataframe

    lines = {"Aaron Judge": BattingLine(at_bats=550, hits=180, home_runs=53)}
    print(to_csv(lines))
    df = to_dataframe(lines)  # requires pandas: pip install pandas
"""

from __future__ import annotations

import csv
import dataclasses
import io
from typing import IO, Any, Dict, Iterable, List, Mapping, Optional, Union

from .lines import BattingLine, PitchingLine

__all__ = ["to_csv", "to_records", "to_dict", "to_numpy", "to_dataframe"]

#: Derived stats (zero-arg properties or methods) included as extra columns.
_BATTING_DERIVED = ("avg", "obp", "slg", "ops", "iso", "babip")
_PITCHING_DERIVED = ("era", "whip", "k_per_9", "bb_per_9", "fip")

Line = Union[BattingLine, PitchingLine]
#: A collection of stat lines, or already record-shaped rows (e.g. Statcast).
Data = Union[Mapping[str, Any], Iterable[Any]]


def _derived_fields(line: Line) -> Iterable[str]:
    if isinstance(line, BattingLine):
        return _BATTING_DERIVED
    if isinstance(line, PitchingLine):
        return _PITCHING_DERIVED
    raise TypeError(
        f"pyhomerun export functions support BattingLine/PitchingLine or "
        f"dict-like rows, not {type(line).__name__}"
    )


def to_records(data: Data) -> List[Dict[str, Any]]:
    """Flatten stat lines (or already record-shaped rows) into plain dicts.

    Args:
        data: A mapping of label (e.g. player name) to line — adds a
            leading ``name`` key to each record — or a plain iterable.
            Elements can be :class:`~pyhomerun.BattingLine`/
            :class:`~pyhomerun.PitchingLine` (every field plus every
            derived stat becomes a key; all elements must be the same
            line type), or plain ``dict``-like rows that are passed
            through as-is — e.g. the output of
            :meth:`~pyhomerun.StatcastClient.search`.

    Returns:
        One plain ``dict`` per input row, with only ``int``/``float``/
        ``str``/``None`` values and no pyhomerun objects — the shape
        ``pandas.DataFrame.from_records(...)`` and ``pandas.DataFrame(...)``
        both accept directly.

    >>> from pyhomerun import BattingLine
    >>> lines = {"Aaron Judge": BattingLine(at_bats=550, hits=180, home_runs=53, walks=110)}
    >>> records = to_records(lines)
    >>> records[0]["name"], records[0]["home_runs"]
    ('Aaron Judge', 53)
    >>> round(records[0]["avg"], 3)
    0.327
    >>> to_records([{"launch_speed": 105.1, "launch_angle": 22.0}])
    [{'launch_speed': 105.1, 'launch_angle': 22.0}]
    """
    labeled = isinstance(data, Mapping)
    items = list(data.items()) if labeled else [(None, item) for item in data]
    if not items:
        return []

    first = items[0][1]
    if isinstance(first, (BattingLine, PitchingLine)):
        line_type = type(first)
        fields = [f.name for f in dataclasses.fields(first)]
        derived = list(_derived_fields(first))
        records = []
        for label, line in items:
            if type(line) is not line_type:
                raise TypeError(
                    f"pyhomerun export functions require every line to be the "
                    f"same type, got {line_type.__name__} and {type(line).__name__}"
                )
            row: Dict[str, Any] = {"name": label} if labeled else {}
            for name in fields:
                row[name] = getattr(line, name)
            for name in derived:
                value = getattr(line, name)
                row[name] = value() if callable(value) else value
            records.append(row)
        return records

    records = []
    for label, item in items:
        if not isinstance(item, Mapping):
            raise TypeError(
                f"pyhomerun export functions support BattingLine/PitchingLine "
                f"or dict-like rows, not {type(item).__name__}"
            )
        row = {"name": label, **item} if labeled else dict(item)
        records.append(row)
    return records


def to_dict(data: Data, *, records: bool = False) -> Union[Dict[str, List[Any]], List[Dict[str, Any]]]:
    """Bulk-export stat lines (or Statcast-style rows) as plain dicts.

    Args:
        data: Same input :func:`to_records` accepts.
        records: If ``False`` (default), return the columnar shape
            ``{column: [value, ...]}`` — exactly what ``pandas.DataFrame(...)``
            wants, and each value list is ready for ``numpy.array(...)``.
            If ``True``, return a list of one dict per row instead (the
            same shape :func:`to_records` returns).

    >>> from pyhomerun import BattingLine
    >>> to_dict([BattingLine(at_bats=10, hits=3)])["hits"]
    [3]
    >>> to_dict([BattingLine(at_bats=10, hits=3)], records=True)[0]["hits"]
    3
    """
    rows = to_records(data)
    if records:
        return rows
    if not rows:
        return {}
    columns = list(rows[0].keys())
    return {column: [row.get(column) for row in rows] for column in columns}


def _infer_numpy_dtype(values: List[Any]) -> str:
    present = [v for v in values if v is not None]
    if not present:
        return "f8"
    if all(isinstance(v, bool) for v in present):
        return "bool"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
        return "f8"
    return "O"


def to_numpy(data: Data, dtype: Optional[List[Any]] = None) -> Any:
    """Bulk-export stat lines (or Statcast-style rows) as a numpy structured array.

    Requires numpy, which pyhomerun does not install by default (see the
    module docstring) — ``pip install numpy`` first.

    Args:
        data: Same input :func:`to_records` accepts.
        dtype: Override the inferred ``numpy`` structured dtype (a list of
            ``(name, dtype)`` pairs). By default, each column's dtype is
            inferred independently: all-numeric columns (missing values
            become ``nan``) get ``float64``; anything else gets ``object``.

    Returns:
        A one-dimensional ``numpy.ndarray`` with one named field per
        column — index a column with ``array["home_runs"]``.

    Example (requires numpy)::

        >>> from pyhomerun import BattingLine, to_numpy
        >>> arr = to_numpy([BattingLine(at_bats=550, hits=180, home_runs=53)])  # doctest: +SKIP
        >>> arr["home_runs"]  # doctest: +SKIP
        array([53.])
    """
    try:
        import numpy as np
    except ImportError as exc:
        raise ImportError(
            "to_numpy() requires numpy, which pyhomerun does not install by "
            "default (pyhomerun stays zero-dependency). Install it with "
            "`pip install numpy`."
        ) from exc

    rows = to_records(data)
    if not rows:
        return np.array([])

    columns = list(rows[0].keys())
    if dtype is None:
        dtype = [(column, _infer_numpy_dtype([row.get(column) for row in rows])) for column in columns]

    array = np.empty(len(rows), dtype=dtype)
    for name in array.dtype.names:
        values = [row.get(name) for row in rows]
        if np.issubdtype(array.dtype[name], np.floating):
            values = [float("nan") if v is None else v for v in values]
        array[name] = values
    return array


def to_dataframe(data: Data) -> Any:
    """Bulk-export stat lines (or Statcast-style rows) as a pandas DataFrame.

    Requires pandas, which pyhomerun does not install by default (see the
    module docstring) — ``pip install pandas`` first.

    Args:
        data: Same input :func:`to_records` accepts.

    Returns:
        A ``pandas.DataFrame``, one row per input line/record.

    Example (requires pandas)::

        >>> from pyhomerun import BattingLine, to_dataframe
        >>> df = to_dataframe({"Aaron Judge": BattingLine(at_bats=550, hits=180, home_runs=53)})  # doctest: +SKIP
        >>> df["home_runs"].iloc[0]  # doctest: +SKIP
        53
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "to_dataframe() requires pandas, which pyhomerun does not install "
            "by default (pyhomerun stays zero-dependency). Install it with "
            "`pip install pandas`."
        ) from exc

    return pd.DataFrame(to_records(data))


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
    rows = to_records(lines)

    buffer = io.StringIO()
    if rows:
        columns = list(rows[0].keys())
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    text = buffer.getvalue()
    if file is None:
        return text
    file.write(text)
    return None
