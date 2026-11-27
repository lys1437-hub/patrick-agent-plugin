#!/usr/bin/env python3
"""Run shipped tool tests with an explicit, portable final result line."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


class ExecutionCountingResult(unittest.TextTestResult):
    """Count tests that really ran, keeping test, fixture and subtest skips apart.

    ``testsRun`` counts started tests, while ``skipped`` also holds class or
    module fixture skips (never started) and subtest skips (inside a started
    test), so the two numbers cannot be subtracted.  A started test counts as
    executed unless the test itself was skipped, or it used subtests and every
    one of them was skipped.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.executed = 0
        self._current: unittest.TestCase | None = None
        self._current_skipped = False
        self._subtests_seen = 0
        self._subtests_skipped = 0

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._current = test
        self._current_skipped = False
        self._subtests_seen = 0
        self._subtests_skipped = 0

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        if self._current is None:
            return
        if test is self._current:
            self._current_skipped = True
        elif getattr(test, "test_case", None) is self._current:
            self._subtests_seen += 1
            self._subtests_skipped += 1

    def addSubTest(self, test: unittest.TestCase, subtest: unittest.TestCase, err: object) -> None:
        super().addSubTest(test, subtest, err)
        if test is self._current:
            self._subtests_seen += 1

    def stopTest(self, test: unittest.TestCase) -> None:
        super().stopTest(test)
        if test is self._current:
            all_subtests_skipped = self._subtests_seen > 0 and self._subtests_skipped == self._subtests_seen
            if not self._current_skipped and not all_subtests_skipped:
                self.executed += 1
        self._current = None


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
            runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=ExecutionCountingResult)
            result = runner.run(suite)
            tests_run = result.testsRun
            skipped = len(result.skipped)
            passed = result.wasSuccessful() and result.executed > 0
        except BaseException as error:  # any early exit, including SystemExit(0), must fail
            tests_run = skipped = 0
            passed = False
            print(f"tool test run aborted: {type(error).__name__}: {error}", file=sys.stderr)
    outcome = "PASS" if passed else "FAIL"
    print(f"TOOL_TESTS tools={len(tools)} tests={tests_run} skipped={skipped} result={outcome}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
