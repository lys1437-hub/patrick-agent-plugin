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

    def test_plugin_manifest_requires_the_expected_local_paths(self) -> None:
        root = self.make_plugin()
        (root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "patrick-agent", "skills": [], "agents": []}), encoding="utf-8"
        )

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugin.json skills", result.stderr)

    def test_plugin_manifest_requires_the_expected_name(self) -> None:
        root = self.make_plugin()
        plugin_path = root / ".claude-plugin" / "plugin.json"
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
        plugin["name"] = "unrelated-plugin"
        plugin_path.write_text(json.dumps(plugin), encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugin.json name", result.stderr)

    def test_marketplace_manifest_requires_the_local_plugin_entry(self) -> None:
        root = self.make_plugin()
        (root / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"name": "patrick-agent-marketplace", "plugins": []}), encoding="utf-8"
        )

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("marketplace.json", result.stderr)

    def test_local_manifest_path_cannot_escape_the_payload_root(self) -> None:
        root = self.make_plugin()
        plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        plugin["skills"] = ["./../outside"]
        (root.parent / "outside").mkdir()
        (root / ".claude-plugin" / "plugin.json").write_text(json.dumps(plugin), encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes payload root", result.stderr)

    def test_symbolic_link_in_payload_fails(self) -> None:
        root = self.make_plugin()
        target = root.parent / "external-payload"
        target.mkdir()
        (target / "vectors.faiss").write_bytes(b"outside payload")
        (root / "portfolio").mkdir()
        (root / "portfolio" / "linked").symlink_to(target, target_is_directory=True)

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)

    def test_each_expected_skill_requires_its_skill_markdown(self) -> None:
        root = self.make_plugin()
        (root / "skills" / "one-page-report" / "SKILL.md").unlink()

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/one-page-report/SKILL.md", result.stderr)

    def test_nested_git_directory_is_not_ignored(self) -> None:
        root = self.make_plugin()
        nested_git = root / "portfolio" / "example" / ".git"
        nested_git.mkdir(parents=True)
        (nested_git / "index.faiss").write_bytes(b"forbidden")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested .git", result.stderr)

    def test_plugin_manifest_rejects_unsupported_components(self) -> None:
        root = self.make_plugin()
        plugin_path = root / ".claude-plugin" / "plugin.json"
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
        plugin["commands"] = ["./../outside"]
        plugin_path.write_text(json.dumps(plugin), encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported plugin.json field", result.stderr)

    def test_marketplace_rejects_invalid_external_source(self) -> None:
        root = self.make_plugin()
        marketplace_path = root / ".claude-plugin" / "marketplace.json"
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        marketplace["plugins"].append({"name": "broken", "source": None})
        marketplace_path.write_text(json.dumps(marketplace), encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("external source", result.stderr)


if __name__ == "__main__":
    unittest.main()
