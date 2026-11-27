#!/usr/bin/env python3
"""Run shipped tool tests with an explicit, portable final result line."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


class NonSkippedResult(unittest.TextTestResult):
    """Note whether at least one started test was not skipped as a whole.

    A start/stop interval qualifies unless ``addSkip`` names that same test
    object, which covers method or class decorators, setUp, the test body,
    tearDown and cleanups.  Class or module fixture skips and subtest skips
    never disqualify an interval, so a run whose subtests are all skipped can
    still pass.  This is a floor for the whole suite, not a count of executed
    assertions or subtests, nor per-tool or per-OS coverage.  ``testsRun`` and
    the skip records use different units and are never subtracted.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.has_non_skipped_test = False
        self._active: unittest.TestCase | None = None
        self._test_skipped = False

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._active = test
        self._test_skipped = False

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        if test is self._active:
            self._test_skipped = True

    def stopTest(self, test: unittest.TestCase) -> None:
        if test is self._active:
            self.has_non_skipped_test |= not self._test_skipped
            self._active = None
        super().stopTest(test)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tools_path = root / "tools"
    tools = sorted(path for path in tools_path.glob("*.py") if path.is_file())
    if not tools:
        print("TOOL_TESTS tools=0 tests=0 skipped=0 result=PASS")
        return 0
    tests_path = tools_path / "tests"
    tests_run = skipped = 0
    passed = False
    if tests_path.is_dir():
        sys.path.insert(0, str(root))
        try:
            suite = unittest.defaultTestLoader.discover(str(tests_path), pattern="test_*.py")
            runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=NonSkippedResult)
            result = runner.run(suite)
            tests_run = result.testsRun
            skipped = len(result.skipped)
            passed = result.wasSuccessful() and result.testsRun > 0 and result.has_non_skipped_test
        except BaseException as error:  # any early exit, including SystemExit(0), must fail
            tests_run = skipped = 0
            passed = False
            print(f"tool test run aborted: {type(error).__name__}: {error}", file=sys.stderr)
    outcome = "PASS" if passed else "FAIL"
    print(f"TOOL_TESTS tools={len(tools)} tests={tests_run} skipped={skipped} result={outcome}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
