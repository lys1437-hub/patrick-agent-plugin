"""Contract tests for the distributable plugin payload."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_plugin import validate as validate_in_process
from scripts import validate_plugin as validator_module

VALIDATOR = REPO_ROOT / "scripts" / "validate_plugin.py"


class PluginValidationTests(unittest.TestCase):
    def make_plugin(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "plugin"
        tracked = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8").split("\0")
        for item in filter(None, tracked):
            source = REPO_ROOT / item
            destination = root / item
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        return root

    def validate(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(root)],
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

    def test_required_file_must_be_in_the_git_release_inventory(self) -> None:
        root = self.make_plugin()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "rm", "--cached", "LICENSE"], check=True, capture_output=True)

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required file: LICENSE", result.stderr)

    def test_skill_entry_must_be_in_the_git_release_inventory(self) -> None:
        root = self.make_plugin()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "rm", "--cached", "skills/skill-doctor/SKILL.md"], check=True, capture_output=True)

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required Skill entry: skills/skill-doctor/SKILL.md", result.stderr)

    def test_skill_license_and_notice_must_be_present_and_tracked(self) -> None:
        root = self.make_plugin()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        for relative in (
            "skills/report-and-verification/LICENSE",
            "skills/report-and-verification/NOTICE",
            "skills/skill-workflow-builder/LICENSE",
            "skills/skill-workflow-builder/NOTICE",
        ):
            (root / relative).unlink()

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/report-and-verification/LICENSE", result.stderr)
        self.assertIn("skills/skill-workflow-builder/NOTICE", result.stderr)

    def test_validator_rejects_tracked_file_missing_from_working_tree(self) -> None:
        root = self.make_plugin()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        (root / "skills" / "one-page-report" / "scripts" / "check_page.py").unlink()

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tracked payload file is missing", result.stderr)

    def test_validator_rejects_missing_expected_support_file_from_inventory(self) -> None:
        root = self.make_plugin()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "rm", "--cached", "skills/one-page-report/references/skeleton.html"], check=True, capture_output=True)

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing expected release path: skills/one-page-report/references/skeleton.html", result.stderr)

    def test_exported_payload_rejects_missing_expected_support_file(self) -> None:
        root = self.make_plugin()
        (root / "skills" / "one-page-report" / "references" / "skeleton.html").unlink()

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing expected release path: skills/one-page-report/references/skeleton.html", result.stderr)

    def test_exported_payload_rejects_unexpected_release_file(self) -> None:
        root = self.make_plugin()
        (root / "skills" / "skill-doctor" / "private-notes.md").write_text("not for release\n", encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected release path: skills/skill-doctor/private-notes.md", result.stderr)

    def test_validator_rejects_gitlink_in_release_inventory(self) -> None:
        root = self.make_plugin()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(root), "update-index", "--add", "--cacheinfo", "160000," + "1" * 40 + ",unexpected-module"],
            check=True,
        )
        (root / "unexpected-module").mkdir()

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported Git entry mode 160000", result.stderr)

    def test_validator_rejects_unmerged_git_index_stage(self) -> None:
        root = self.make_plugin()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "validation@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Validation Fixture"], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial fixture"], check=True)
        base_branch = subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(["git", "-C", str(root), "checkout", "-qb", "incoming"], check=True)
        (root / "README.md").write_text("incoming change\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "incoming change"], check=True)
        subprocess.run(["git", "-C", str(root), "checkout", "-q", base_branch], check=True)
        (root / "README.md").write_text("current change\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "current change"], check=True)
        merge = subprocess.run(["git", "-C", str(root), "merge", "incoming"], check=False, capture_output=True, text=True)
        self.assertNotEqual(merge.returncode, 0, merge.stdout + merge.stderr)

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported Git entry mode unmerged-stage-1", result.stderr)

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

    def test_validator_rejects_tracked_python_bytecode(self) -> None:
        root = self.make_plugin()
        cache = root / "tests" / "__pycache__"
        cache.mkdir()
        bytecode = cache / "test_validate_plugin.cpython-313.pyc"
        bytecode.write_bytes(b"bytecode")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "-f", "."], check=True)

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden payload directory", result.stderr)

    def test_skill_doctor_describes_the_shipped_agent(self) -> None:
        contents = (self.make_plugin() / "skills" / "skill-doctor" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("skill-auditor", contents)

    def test_validator_falls_back_when_plugin_is_nested_in_a_git_repository(self) -> None:
        root = self.make_plugin()
        subprocess.run(["git", "init", "-q", str(root.parent)], check=True)
        (root / ".env").write_text("must be scanned", encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown payload path", result.stderr)

    def test_plugin_manifest_rejects_invalid_release_metadata(self) -> None:
        root = self.make_plugin()
        path = root / ".claude-plugin" / "plugin.json"
        plugin = json.loads(path.read_text(encoding="utf-8"))
        plugin["version"] = {"not": "a string"}
        plugin["license"] = False
        path.write_text(json.dumps(plugin), encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugin.json version", result.stderr)
        self.assertIn("plugin.json license", result.stderr)

    def test_plugin_manifest_rejects_non_string_author_email(self) -> None:
        root = self.make_plugin()
        path = root / ".claude-plugin" / "plugin.json"
        plugin = json.loads(path.read_text(encoding="utf-8"))
        plugin["author"]["email"] = 123
        path.write_text(json.dumps(plugin), encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("author.email", result.stderr)

    def test_validator_rejects_invalid_manifest_metadata_types(self) -> None:
        cases = (
            ("marketplace_description", lambda plugin, marketplace: marketplace.__setitem__("description", {})),
            ("owner_email", lambda plugin, marketplace: marketplace["owner"].__setitem__("email", 123)),
            ("entry_description", lambda plugin, marketplace: marketplace["plugins"][0].__setitem__("description", [])),
            ("author_url", lambda plugin, marketplace: plugin["author"].__setitem__("url", False)),
        )
        for name, mutate in cases:
            with self.subTest(name=name):
                root = self.make_plugin()
                plugin_path = root / ".claude-plugin" / "plugin.json"
                marketplace_path = root / ".claude-plugin" / "marketplace.json"
                plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
                marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
                mutate(plugin, marketplace)
                plugin_path.write_text(json.dumps(plugin), encoding="utf-8")
                marketplace_path.write_text(json.dumps(marketplace), encoding="utf-8")

                result = self.validate(root)

                self.assertNotEqual(result.returncode, 0)

    def test_agent_contract_rejects_write_capabilities(self) -> None:
        root = self.make_plugin()
        path = root / "agents" / "skill-auditor.md"
        path.write_text(path.read_text(encoding="utf-8").replace("  - Glob", "  - Glob\n  - Bash"), encoding="utf-8")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frontmatter must match", result.stderr)

    def test_agent_contract_does_not_read_lists_from_another_field_as_tools(self) -> None:
        root = self.make_plugin()
        path = root / "agents" / "skill-auditor.md"
        path.write_text(
            "---\nname: skill-auditor\ndescription: test\ntools:\n  - Bash\nskills:\n  - Read\n  - Grep\n  - Glob\n---\n",
            encoding="utf-8",
        )

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frontmatter must match", result.stderr)

    def test_agent_contract_rejects_non_utf8_agent_file(self) -> None:
        root = self.make_plugin()
        (root / "agents" / "skill-auditor.md").write_bytes(b"\xff")

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("readable UTF-8", result.stderr)

    def test_agent_contract_rejects_ambiguous_or_non_string_descriptions(self) -> None:
        for description in ("[", '\"\"', "null", "test: broken"):
            with self.subTest(description=description):
                root = self.make_plugin()
                path = root / "agents" / "skill-auditor.md"
                contents = path.read_text(encoding="utf-8").replace(
                    "description: 掃使用者的 skill 目錄下所有 skill 的斷引用、硬編絕對路徑、description 截斷與 provenance 缺漏，回報結構化清單。**唯讀，不改檔。** 需要一次讀很多檔案時派給它，避免塞爆主對話。",
                    f"description: {description}",
                )
                path.write_text(contents, encoding="utf-8")

                result = self.validate(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("frontmatter must match", result.stderr)

    def test_agent_contract_rejects_comment_number_and_missing_mapping_separator(self) -> None:
        for description in ("# comment only", "123", "test"):
            with self.subTest(description=description):
                root = self.make_plugin()
                path = root / "agents" / "skill-auditor.md"
                contents = path.read_text(encoding="utf-8").replace(
                    "description: 掃使用者的 skill 目錄下所有 skill 的斷引用、硬編絕對路徑、description 截斷與 provenance 缺漏，回報結構化清單。**唯讀，不改檔。** 需要一次讀很多檔案時派給它，避免塞爆主對話。",
                    f"description:{description}" if description == "test" else f"description: {description}",
                )
                path.write_text(contents, encoding="utf-8")

                result = self.validate(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("frontmatter must match", result.stderr)

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
        oversized.parent.mkdir(parents=True, exist_ok=True)
        oversized.write_bytes(b"x" * (512 * 1024))

        result = self.validate(root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("total size", result.stderr)

    def test_payload_over_single_file_limit_fails(self) -> None:
        root = self.make_plugin()
        oversized = root / "portfolio" / "example.md"
        oversized.parent.mkdir(parents=True, exist_ok=True)
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
        (root / "portfolio").mkdir(exist_ok=True)
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
            [sys.executable, str(VALIDATOR), str(root), "--strict"],
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


    def add_release_files(self, root: Path, files: dict[str, str]) -> None:
        for relative, contents in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")

    def validate_with_inventory(self, root: Path, extra: set[str]) -> list[str]:
        with mock.patch.object(validator_module, "EXPECTED_TRACKED_PATHS", validator_module.EXPECTED_TRACKED_PATHS | extra):
            return validate_in_process(root)

    def tool_files(self) -> dict[str, str]:
        return {
            "tools/example.py": "# SPDX-License-Identifier: Apache-2.0\nraise RuntimeError('must never execute')\n",
            "tools/tests/test_example.py": "raise RuntimeError('must never import')\n",
        }

    def hook_files(self, command: str = '"${CLAUDE_PLUGIN_ROOT}/hooks/example.sh"', **fields: object) -> dict[str, str]:
        handler = {"type": "command", "command": command, **fields}
        return {
            "hooks/hooks.json": json.dumps({"hooks": {"SessionStart": [{"matcher": "startup", "hooks": [handler]}]}}),
            "hooks/example.sh": "#!/bin/sh\nexit 0\n",
        }

    def test_synthetic_tool_and_default_hooks_pass_without_execution(self) -> None:
        root = self.make_plugin()
        files = {**self.tool_files(), **self.hook_files()}
        self.add_release_files(root, files)
        self.assertEqual(self.validate_with_inventory(root, set(files)), [])

    def test_tool_requires_matching_test(self) -> None:
        root = self.make_plugin()
        files = self.tool_files()
        files.pop("tools/tests/test_example.py")
        self.add_release_files(root, files)
        self.assertIn("tool requires matching test: tools/example.py", self.validate_with_inventory(root, set(files)))

    def test_tool_test_requires_matching_tool(self) -> None:
        root = self.make_plugin()
        files = self.tool_files()
        files.pop("tools/example.py")
        self.add_release_files(root, files)
        self.assertIn("tool test requires matching tool: tools/tests/test_example.py", self.validate_with_inventory(root, set(files)))

    def test_tool_requires_exact_license_in_first_five_lines(self) -> None:
        for contents in ("pass\n", "# SPDX-License-Identifier: MIT\n", "\n" * 5 + "# SPDX-License-Identifier: Apache-2.0\n", " # SPDX-License-Identifier: Apache-2.0\n"):
            with self.subTest(contents=contents):
                root = self.make_plugin()
                files = self.tool_files()
                files["tools/example.py"] = contents
                self.add_release_files(root, files)
                self.assertIn("tool requires Apache-2.0 SPDX line in first five lines: tools/example.py", self.validate_with_inventory(root, set(files)))

    def test_tool_license_on_fifth_line_passes(self) -> None:
        root = self.make_plugin()
        files = self.tool_files()
        files["tools/example.py"] = "\n" * 4 + "# SPDX-License-Identifier: Apache-2.0\n"
        self.add_release_files(root, files)
        self.assertEqual(self.validate_with_inventory(root, set(files)), [])

    def test_new_paths_keep_exact_release_inventory(self) -> None:
        root = self.make_plugin()
        files = {**self.tool_files(), **self.hook_files()}
        self.add_release_files(root, files)
        problems = validate_in_process(root)
        for relative in files:
            self.assertIn(f"unexpected release path: {relative}", problems)

    def test_new_path_allowlist_is_shallow_and_suffix_specific(self) -> None:
        for relative in ("tools/example.py", "tools/tests/test_example.py", "hooks/example.py", "hooks/example.sh", "hooks/hooks.json"):
            with self.subTest(allowed=relative):
                self.assertTrue(validator_module.is_allowed(Path(relative)))
        for relative in ("tools/example.sh", "tools/example.json", "tools/nested/example.py", "tools/tests/example.py", "tools/tests/deep/test_example.py", "tools/__init__.py", "tools/tests/test___init__.py", "hooks/nested/example.sh", "hooks/example.txt", "hooks/example.bin", "portfolio/example.sh", "unknown/example.py"):
            with self.subTest(rejected=relative):
                self.assertFalse(validator_module.is_allowed(Path(relative)))

    def test_new_paths_reject_disallowed_file_types_in_payload(self) -> None:
        for relative in ("tools/example.sh", "hooks/example.txt", "hooks/example.bin"):
            with self.subTest(relative=relative):
                root = self.make_plugin()
                self.add_release_files(root, {relative: "synthetic fixture\n"})
                problems = self.validate_with_inventory(root, {relative})
                expected = "forbidden payload file type" if relative.endswith(".bin") else "unknown payload path or file type"
                self.assertIn(f"{expected}: {relative}", problems)

    def test_manifest_hooks_field_always_uses_default_only_error(self) -> None:
        for value in ("./hooks/hooks.json", "./other.json", ["./hooks/hooks.json"], {"SessionStart": []}, None):
            with self.subTest(value=value):
                root = self.make_plugin()
                path = root / ".claude-plugin/plugin.json"
                plugin = json.loads(path.read_text(encoding="utf-8"))
                plugin["hooks"] = value
                path.write_text(json.dumps(plugin), encoding="utf-8")
                result = self.validate(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("plugin.json must not declare hooks; this plugin only allows the default hooks/hooks.json", result.stderr)

    def test_default_hooks_reject_invalid_json_and_utf8(self) -> None:
        for contents in (b"{", b"\xff"):
            with self.subTest(contents=contents):
                root = self.make_plugin()
                self.add_release_files(root, {"hooks/hooks.json": "{}"})
                (root / "hooks/hooks.json").write_bytes(contents)
                problems = self.validate_with_inventory(root, {"hooks/hooks.json"})
                self.assertTrue(any("hooks/hooks.json must be valid JSON" in problem for problem in problems), problems)

    def test_default_hooks_reject_unsupported_structures(self) -> None:
        values = ([], {}, {"SessionStart": []}, {"hooks": []}, {"hooks": {}, "modules": []}, {"hooks": {"SessionStart": {}}}, {"hooks": {"SessionStart": ["other.json"]}}, {"hooks": {"SessionStart": [{"hooks": {}}]}}, {"hooks": {"SessionStart": [{"hooks": [{"type": "http", "url": "https://example.invalid"}]}]}}, {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo", "args": "wrong"}]}]}})
        for value in values:
            with self.subTest(value=value):
                root = self.make_plugin()
                self.add_release_files(root, {"hooks/hooks.json": json.dumps(value)})
                problems = self.validate_with_inventory(root, {"hooks/hooks.json"})
                self.assertTrue(any("hooks/hooks.json" in problem for problem in problems), problems)

    def test_hook_paths_accept_both_shell_quotes_and_exec_args(self) -> None:
        handlers = (
            {'command': '"${CLAUDE_PLUGIN_ROOT}"/hooks/example.sh'},
            {'command': '"${CLAUDE_PLUGIN_ROOT}/hooks/example.sh"'},
            {'command': 'sh', 'args': ['${CLAUDE_PLUGIN_ROOT}/hooks/example.sh']},
            {'command': '${CLAUDE_PLUGIN_ROOT}/hooks/example.sh', 'args': []},
        )
        for fields in handlers:
            with self.subTest(fields=fields):
                root = self.make_plugin()
                files = self.hook_files(**fields)
                self.add_release_files(root, files)
                self.assertEqual(self.validate_with_inventory(root, set(files)), [])

    def test_hook_paths_reject_missing_outside_and_traversal_targets(self) -> None:
        for target in ("hooks/missing.sh", "scripts/validate_plugin.py", "hooks/../scripts/validate_plugin.py", "hooks/nested/example.sh", "hooks/example.sh/extra"):
            for use_args in (False, True):
                with self.subTest(target=target, use_args=use_args):
                    root = self.make_plugin()
                    reference = "${CLAUDE_PLUGIN_ROOT}/" + target
                    files = self.hook_files("sh", args=[reference]) if use_args else self.hook_files('"' + reference + '"')
                    self.add_release_files(root, files)
                    problems = self.validate_with_inventory(root, set(files))
                    self.assertTrue(any("invalid hook target" in problem for problem in problems), problems)

    def test_hook_paths_check_every_reference_and_expected_inventory(self) -> None:
        root = self.make_plugin()
        files = self.hook_files('"${CLAUDE_PLUGIN_ROOT}/hooks/example.sh"; "${CLAUDE_PLUGIN_ROOT}/hooks/missing.sh"')
        self.add_release_files(root, files)
        problems = self.validate_with_inventory(root, set(files))
        self.assertTrue(any("invalid hook target" in problem and "missing.sh" in problem for problem in problems), problems)
        files = self.hook_files()
        self.add_release_files(root, files)
        problems = self.validate_with_inventory(root, {"hooks/hooks.json"})
        self.assertTrue(any("invalid hook target" in problem and "example.sh" in problem for problem in problems), problems)

    def test_hook_paths_reject_malformed_shell_quoting(self) -> None:
        root = self.make_plugin()
        files = self.hook_files('"${CLAUDE_PLUGIN_ROOT}/hooks/example.sh')
        self.add_release_files(root, files)
        problems = self.validate_with_inventory(root, set(files))
        self.assertTrue(any("invalid command quoting" in problem for problem in problems), problems)

    def run_synthetic_tools(self, tool: str | None = None, tests: str | None = None) -> subprocess.CompletedProcess[str]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        runner = root / "scripts/run_tool_tests.py"
        runner.parent.mkdir()
        shutil.copy2(REPO_ROOT / "scripts/run_tool_tests.py", runner)
        if tool is not None:
            self.add_release_files(root, {"tools/example.py": tool})
        if tests is not None:
            self.add_release_files(root, {"tools/tests/test_example.py": tests})
        return subprocess.run([sys.executable, "-B", str(runner)], cwd=root.parent, capture_output=True, text=True, check=False)

    def test_tool_runner_empty_tools_passes(self) -> None:
        result = self.run_synthetic_tools()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=0 tests=0 skipped=0 result=PASS")

    def test_tool_runner_synthetic_pair_passes(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "import unittest\nfrom tools.example import VALUE\nclass Example(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(VALUE, 42)\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=1 skipped=0 result=PASS")

    def test_tool_runner_synthetic_pair_fails(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "import unittest\nclass Example(unittest.TestCase):\n    def test_value(self):\n        self.fail('synthetic failure')\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=1 skipped=0 result=FAIL")

    def test_tool_runner_zero_tests_fails(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "# no test cases\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=0 skipped=0 result=FAIL")

    def test_tool_runner_all_skipped_fails(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "import unittest\nclass Example(unittest.TestCase):\n    @unittest.skip('synthetic skip')\n    def test_value(self):\n        pass\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=1 skipped=1 result=FAIL")

    def test_tool_runner_missing_tests_fails(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=0 skipped=0 result=FAIL")

    def test_tool_runner_load_tests_system_exit_fails(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "def load_tests(loader, tests, pattern):\n    raise SystemExit(0)\n")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=0 skipped=0 result=FAIL")

    def test_tool_runner_fixture_base_exception_fails(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "import unittest\nclass Abort(BaseException):\n    pass\nclass Example(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        raise Abort('synthetic early exit')\n    def test_value(self):\n        pass\n")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=0 skipped=0 result=FAIL")

    def test_tool_runner_class_fixture_skip_with_passing_test_passes(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "import unittest\nfrom tools.example import VALUE\nclass Runs(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(VALUE, 42)\nclass Skipped(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        raise unittest.SkipTest('synthetic fixture skip')\n    def test_value(self):\n        pass\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=1 skipped=1 result=PASS")

    def test_tool_runner_partial_subtest_skip_passes(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "import unittest\nfrom tools.example import VALUE\nclass Example(unittest.TestCase):\n    def test_value(self):\n        for case in ('run', 'skip'):\n            with self.subTest(case=case):\n                if case == 'skip':\n                    self.skipTest('synthetic subtest skip')\n                self.assertEqual(VALUE, 42)\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=1 skipped=1 result=PASS")

    def test_tool_runner_module_fixture_skip_fails(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "import unittest\ndef setUpModule():\n    raise unittest.SkipTest('synthetic module skip')\nclass Example(unittest.TestCase):\n    def test_value(self):\n        pass\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=0 skipped=1 result=FAIL")

    def test_tool_runner_all_subtests_skipped_fails(self) -> None:
        result = self.run_synthetic_tools("VALUE = 42\n", "import unittest\nclass Example(unittest.TestCase):\n    def test_value(self):\n        for case in ('a', 'b'):\n            with self.subTest(case=case):\n                self.skipTest('synthetic subtest skip')\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines()[-1], "TOOL_TESTS tools=1 tests=1 skipped=2 result=FAIL")


if __name__ == "__main__":
    unittest.main()
