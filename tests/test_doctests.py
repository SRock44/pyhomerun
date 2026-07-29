"""Run every docstring example as a test, so the docs can never go stale."""

import doctest
import unittest

from pyhomerun import (
    batting,
    constants,
    elo,
    export,
    fielding,
    lines,
    pitching,
    simulate,
    situational,
    team,
)


def load_tests(loader, tests, ignore):
    for module in (
        batting,
        pitching,
        fielding,
        constants,
        lines,
        team,
        situational,
        export,
        elo,
        simulate,
    ):
        tests.addTests(doctest.DocTestSuite(module))
    return tests


if __name__ == "__main__":
    unittest.main()
