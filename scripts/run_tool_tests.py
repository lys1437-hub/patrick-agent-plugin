#!/usr/bin/env python3
"""Run shipped tool tests with an explicit, portable final result line."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


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
            result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
            tests_run = result.testsRun
            skipped = len(result.skipped)
            passed = result.wasSuccessful() and tests_run > skipped
        except Exception as error:
            print(f"tool test discovery failed: {error}", file=sys.stderr)
    outcome = "PASS" if passed else "FAIL"
    print(f"TOOL_TESTS tools={len(tools)} tests={tests_run} skipped={skipped} result={outcome}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
