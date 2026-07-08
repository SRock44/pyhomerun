"""Run every docstring example as a test, so the docs can never go stale."""

import doctest
import unittest

from pyhomerun import batting, constants, export, fielding, lines, pitching, situational, team


def load_tests(loader, tests, ignore):
    for module in (batting, pitching, fielding, constants, lines, team, situational, export):
        tests.addTests(doctest.DocTestSuite(module))
    return tests


if __name__ == "__main__":
    unittest.main()
