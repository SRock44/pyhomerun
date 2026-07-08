# Contributing to pyhomerun

Thanks for helping out! This project aims to stay small, correct, and dependency-free.

## Ground rules

1. **Zero dependencies.** Runtime code uses only the Python standard library, and the test suite runs with stock `unittest`. PRs that add a dependency will be asked to remove it.
2. **Document every public function.** Docstrings must state the formula and include a doctest example — the examples run in CI via `tests/test_doctests.py`, so they can't go stale.
3. **Test everything.** New stats need tests covering a typical value and the zero-denominator edge case. MLB client changes must be tested offline (mock `urllib` — see `tests/test_mlb.py`).
4. **Cite your formulas.** For sabermetric stats, link a reference (FanGraphs glossary, Baseball Reference, etc.) in the PR description.

## Development setup

```bash
git clone https://github.com/pyhomerun/pyhomerun
cd pyhomerun
pip install -e .
python -m unittest discover tests -v
```

That's it — no other tools required.

## Reporting bugs

Open an issue with the function called, the inputs, the output you got, and the output you expected (with a source for the expected value if it's a stat-correctness bug).
