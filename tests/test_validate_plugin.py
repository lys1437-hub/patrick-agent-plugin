"""Contract tests for the distributable plugin payload."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate_plugin.py"


class PluginValidationTests(unittest.TestCase):
    def make_plugin(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "plugin"
        shutil.copytree(REPO_ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        return root

    def validate(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(VALIDATOR), str(root)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_current_plugin_payload_passes(self) -> None:
        result = self.validate(self.make_plugin())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_manifest_path_fails(self) -> None:
        root = self.make_plugin()
        (root / "agents" / "skill-auditor.md").unlink()

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("agents/skill-auditor.md", result.stderr)

    def test_missing_required_file_fails(self) -> None:
        root = self.make_plugin()
        (root / "LICENSE").unlink(missing_ok=True)

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LICENSE", result.stderr)

    def test_skill_set_mismatch_fails(self) -> None:
        root = self.make_plugin()
        (root / "skills" / "one-page-report").rename(root / "skills" / "renamed-skill")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Skill", result.stderr)

    def test_forbidden_payload_directory_fails(self) -> None:
        root = self.make_plugin()
        forbidden = root / "portfolio" / "retrieval" / "cache"
        forbidden.mkdir(parents=True)
        (forbidden / "vectors.faiss").write_bytes(b"not a real index")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden", result.stderr)

    def test_payload_over_total_limit_fails(self) -> None:
        root = self.make_plugin()
        oversized = root / "portfolio" / "example.md"
        oversized.parent.mkdir(parents=True)
        oversized.write_bytes(b"x" * (512 * 1024))

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("total size", result.stderr)

    def test_payload_over_single_file_limit_fails(self) -> None:
        root = self.make_plugin()
        oversized = root / "portfolio" / "example.md"
        oversized.parent.mkdir(parents=True)
        oversized.write_bytes(b"x" * (64 * 1024 + 1))

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("single-file", result.stderr)

    def test_manifests_must_be_valid_json(self) -> None:
        root = self.make_plugin()
        (root / ".claude-plugin" / "plugin.json").write_text("{", encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main()
