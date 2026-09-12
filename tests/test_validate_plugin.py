"""Contract tests for the distributable plugin payload."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.validate_plugin import validate as validate_in_process


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
        for directory_name in ("cache", "Cache", "DATA"):
            with self.subTest(directory_name=directory_name):
                root = self.make_plugin()
                forbidden = root / "portfolio" / "retrieval" / directory_name
                forbidden.mkdir(parents=True)
                (forbidden / "rows.csv").write_text("not a dataset", encoding="utf-8")

                result = self.validate(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("forbidden payload directory", result.stderr)

    def test_validator_ignores_python_bytecode_cache(self) -> None:
        root = self.make_plugin()
        cache = root / "tests" / "__pycache__"
        cache.mkdir()
        (cache / "test_validate_plugin.cpython-313.pyc").write_bytes(b"bytecode")

        result = self.validate(root)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_validator_rejects_non_bytecode_inside_python_cache(self) -> None:
        root = self.make_plugin()
        cache = root / "skills" / "skill-doctor" / "__pycache__"
        cache.mkdir()
        (cache / "model.bin").write_bytes(b"not bytecode")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden payload directory", result.stderr)

    def test_in_process_validation_resolves_root_before_containment_checks(self) -> None:
        root = self.make_plugin()
        alias = root.parent / "plugin-alias"
        try:
            alias.symlink_to(root, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlink creation is unavailable: {error}")

        problems = validate_in_process(alias)

        self.assertEqual(problems, [])

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
        try:
            (root / "portfolio" / "linked").symlink_to(target, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlink creation is unavailable: {error}")

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

    def test_marketplace_requires_owner_and_repo_for_external_source(self) -> None:
        for invalid_repo in ("", "   ", "owner"):
            with self.subTest(repo=invalid_repo):
                root = self.make_plugin()
                marketplace_path = root / ".claude-plugin" / "marketplace.json"
                marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
                marketplace["plugins"][1]["source"]["repo"] = invalid_repo
                marketplace_path.write_text(json.dumps(marketplace), encoding="utf-8")

                result = self.validate(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("owner/repo", result.stderr)

    def test_marketplace_requires_a_pinned_lowercase_sha(self) -> None:
        for invalid_sha in ("abc", "A" * 40, None):
            with self.subTest(sha=invalid_sha):
                root = self.make_plugin()
                marketplace_path = root / ".claude-plugin" / "marketplace.json"
                marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
                marketplace["plugins"][1]["source"]["sha"] = invalid_sha
                marketplace_path.write_text(json.dumps(marketplace), encoding="utf-8")

                result = self.validate(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("40-character SHA", result.stderr)

    def test_unknown_top_level_payload_file_fails(self) -> None:
        root = self.make_plugin()
        (root / ".env").write_text("not allowed", encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown payload path", result.stderr)

    def test_forbidden_suffix_inside_skill_fails(self) -> None:
        root = self.make_plugin()
        (root / "skills" / "skill-doctor" / "model.bin").write_bytes(b"not allowed")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden payload file type", result.stderr)

    def test_disallowed_suffix_inside_skill_fails(self) -> None:
        root = self.make_plugin()
        (root / "skills" / "skill-doctor" / "settings.ini").write_text("not allowed", encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown payload path", result.stderr)

    def test_non_utf8_manifest_reports_validation_error(self) -> None:
        root = self.make_plugin()
        (root / ".claude-plugin" / "plugin.json").write_bytes(b"\xff")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valid JSON", result.stderr)

    def test_external_source_rejects_extra_fields_and_dot_segments(self) -> None:
        for patch in ({"ref": "main"}, {"repo": "../.."}):
            with self.subTest(patch=patch):
                root = self.make_plugin()
                path = root / ".claude-plugin" / "marketplace.json"
                marketplace = json.loads(path.read_text(encoding="utf-8"))
                marketplace["plugins"][1]["source"].update(patch)
                path.write_text(json.dumps(marketplace), encoding="utf-8")
                result = self.validate(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("external source", result.stderr)

    def test_validator_rejects_extra_cli_arguments(self) -> None:
        root = self.make_plugin()
        result = subprocess.run(
            ["python3", str(VALIDATOR), str(root), "--strict"],
            check=False, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage", result.stderr)

    def test_manifest_must_be_a_json_object(self) -> None:
        root = self.make_plugin()
        (root / ".claude-plugin" / "plugin.json").write_text("[]", encoding="utf-8")
        result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JSON object", result.stderr)

    def test_marketplace_plugin_entries_must_be_named_objects(self) -> None:
        for entry in ([], {"name": "", "source": "./"}):
            with self.subTest(entry=entry):
                root = self.make_plugin()
                path = root / ".claude-plugin" / "marketplace.json"
                marketplace = json.loads(path.read_text(encoding="utf-8"))
                marketplace["plugins"].append(entry)
                path.write_text(json.dumps(marketplace), encoding="utf-8")
                result = self.validate(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("marketplace.json", result.stderr)

    def test_marketplace_plugins_must_be_a_list(self) -> None:
        root = self.make_plugin()
        path = root / ".claude-plugin" / "marketplace.json"
        marketplace = json.loads(path.read_text(encoding="utf-8"))
        marketplace["plugins"] = {}
        path.write_text(json.dumps(marketplace), encoding="utf-8")
        result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugins must be a list", result.stderr)

    def test_marketplace_requires_name_and_named_owner(self) -> None:
        for patch in ({"name": None}, {"owner": {}}, {"owner": "LipiD"}):
            with self.subTest(patch=patch):
                root = self.make_plugin()
                path = root / ".claude-plugin" / "marketplace.json"
                marketplace = json.loads(path.read_text(encoding="utf-8"))
                marketplace.update(patch)
                path.write_text(json.dumps(marketplace), encoding="utf-8")
                result = self.validate(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("marketplace.json", result.stderr)

    def test_marketplace_rejects_unknown_top_level_and_entry_fields(self) -> None:
        for target, patch in (
            ("top", {"mcpServers": {"unexpected": {"command": "echo"}}}),
            ("entry", {"mcpServers": {"unexpected": {"command": "echo"}}}),
        ):
            with self.subTest(target=target):
                root = self.make_plugin()
                path = root / ".claude-plugin" / "marketplace.json"
                marketplace = json.loads(path.read_text(encoding="utf-8"))
                if target == "top":
                    marketplace.update(patch)
                else:
                    marketplace["plugins"][0].update(patch)
                path.write_text(json.dumps(marketplace), encoding="utf-8")
                result = self.validate(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unsupported", result.stderr)

    def test_marketplace_plugin_names_must_be_unique(self) -> None:
        for entry_index, duplicate_name in ((1, "patrick-agent"), (0, "superpowers")):
            with self.subTest(entry_index=entry_index, duplicate_name=duplicate_name):
                root = self.make_plugin()
                path = root / ".claude-plugin" / "marketplace.json"
                marketplace = json.loads(path.read_text(encoding="utf-8"))
                marketplace["plugins"][entry_index]["name"] = duplicate_name
                path.write_text(json.dumps(marketplace), encoding="utf-8")
                result = self.validate(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unique", result.stderr)

    def test_missing_declared_agent_path_is_reported_by_manifest_check(self) -> None:
        root = self.make_plugin()
        (root / "agents" / "skill-auditor.md").unlink()
        result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("declares a missing path", result.stderr)

    def test_skill_set_mismatch_has_its_own_error(self) -> None:
        root = self.make_plugin()
        (root / "skills" / "one-page-report").rename(root / "skills" / "renamed-skill")
        result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Skill set mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
