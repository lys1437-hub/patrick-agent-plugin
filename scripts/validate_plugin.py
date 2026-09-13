#!/usr/bin/env python3
"""Validate the exact files shipped by the root-source marketplace plugin."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


MAX_TOTAL_BYTES = 512 * 1024
MAX_FILE_BYTES = 64 * 1024
EXPECTED_SKILLS = {
    "feature-proposal-planning",
    "report-and-verification",
    "team-delivery-review",
    "team-weekly-review",
    "skill-workflow-builder",
    "skill-doctor",
    "one-page-report",
}
REQUIRED_FILES = {
    "LICENSE",
    "README.md",
    "TEAM_RULES.md",
    "WHY-THESE-RULES.md",
    "ACCEPTANCE-LEVELS.md",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "agents/skill-auditor.md",
}
ALLOWED_EXACT_FILES = REQUIRED_FILES | {
    ".github/workflows/plugin-validation.yml",
    "scripts/validate_plugin.py",
    "tests/test_validate_plugin.py",
}
ALLOWED_SUFFIXES = {".md", ".json", ".py", ".html", ".toml", ".yaml", ".yml", ".txt", ".csv"}
FORBIDDEN_DIRECTORIES = {"data", "dataset", "corpus", "index", "indexes", "cache", ".cache", ".venv", "venv", "node_modules", "__pycache__"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".faiss", ".npy", ".npz", ".pkl", ".pickle", ".pt", ".onnx", ".bin"}
ALLOWED_PLUGIN_FIELDS = {"name", "version", "description", "author", "keywords", "skills", "agents"}
ALLOWED_MARKETPLACE_FIELDS = {"name", "description", "owner", "plugins"}
ALLOWED_MARKETPLACE_ENTRY_FIELDS = {"name", "source", "description"}
EXTERNAL_SOURCE_FIELDS = {"source", "repo", "sha"}
REPOSITORY_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def load_json(root: Path, relative_path: str, problems: list[str]) -> dict | None:
    path = root / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append(f"missing required file: {relative_path}")
        return None
    except json.JSONDecodeError as error:
        problems.append(f"{relative_path} must be valid JSON: {error.msg}")
        return None
    except (UnicodeDecodeError, OSError) as error:
        problems.append(f"{relative_path} must be valid JSON: {error}")
        return None
    if not isinstance(value, dict):
        problems.append(f"{relative_path} must contain a JSON object")
        return None
    return value


def check_manifest_paths(root: Path, plugin: dict, marketplace: dict, problems: list[str]) -> None:
    for key in sorted(set(plugin) - ALLOWED_PLUGIN_FIELDS):
        problems.append(f"unsupported plugin.json field: {key}")
    if plugin.get("name") != "patrick-agent":
        problems.append("plugin.json name must be 'patrick-agent'")
    expected_paths = {"skills": ["./skills"], "agents": ["./agents/skill-auditor.md"]}
    for key, expected in expected_paths.items():
        entries = plugin.get(key)
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, str) or not entry.startswith("./"):
                    problems.append(f"plugin.json {key} has an invalid local path: {entry!r}")
                    continue
                target = (root / entry[2:]).resolve()
                try:
                    target.relative_to(root)
                except ValueError:
                    problems.append(f"plugin.json {key} escapes payload root: {entry}")
        if entries != expected:
            problems.append(f"plugin.json {key} must equal {expected}")
            continue
        for entry in entries:
            target = (root / entry[2:]).resolve()
            if not target.exists():
                problems.append(f"plugin.json declares a missing path: {entry[2:]}")

    for key in sorted(set(marketplace) - ALLOWED_MARKETPLACE_FIELDS):
        problems.append(f"unsupported marketplace.json field: {key}")
    if not isinstance(marketplace.get("name"), str) or not marketplace["name"]:
        problems.append("marketplace.json name must be a non-empty string")
    owner = marketplace.get("owner")
    if not isinstance(owner, dict) or not isinstance(owner.get("name"), str) or not owner["name"]:
        problems.append("marketplace.json owner must contain a non-empty name")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        problems.append("marketplace.json plugins must be a list")
        return
    local_plugins = []
    plugin_names: set[str] = set()
    for entry in plugins:
        if not isinstance(entry, dict):
            problems.append("marketplace.json plugins entries must be objects")
            continue
        for key in sorted(set(entry) - ALLOWED_MARKETPLACE_ENTRY_FIELDS):
            problems.append(f"unsupported marketplace.json plugin entry field: {key}")
        name, source = entry.get("name"), entry.get("source")
        if not isinstance(name, str) or not name:
            problems.append("marketplace.json plugin entry must have a non-empty name")
            continue
        if name in plugin_names:
            problems.append(f"marketplace.json plugin names must be unique: {name!r}")
        plugin_names.add(name)
        if isinstance(source, str):
            local_plugins.append(entry)
            if source != "./":
                problems.append(f"marketplace.json has an unsupported local source: {source!r}")
            elif not (root / ".claude-plugin" / "plugin.json").is_file():
                problems.append("marketplace.json root source is missing .claude-plugin/plugin.json")
            continue
        if not isinstance(source, dict):
            problems.append("marketplace.json external source must be a GitHub source object")
            continue
        repo, sha = source.get("repo"), source.get("sha")
        repo_parts = repo.split("/") if isinstance(repo, str) else []
        valid_repo = len(repo_parts) == 2 and all(
            part not in {".", ".."} and REPOSITORY_COMPONENT.fullmatch(part)
            for part in repo_parts
        )
        if set(source) != EXTERNAL_SOURCE_FIELDS or source.get("source") != "github" or not valid_repo or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            problems.append("marketplace.json external source must have github, owner/repo, and a 40-character SHA")
    if len(local_plugins) != 1 or local_plugins[0].get("name") != "patrick-agent" or local_plugins[0].get("source") != "./":
        problems.append("marketplace.json must declare exactly one patrick-agent plugin with source './'")


def is_allowed(relative: Path) -> bool:
    text = relative.as_posix()
    if text in ALLOWED_EXACT_FILES:
        return True
    if not relative.parts or relative.parts[0] not in {"skills", "portfolio"}:
        return False
    return relative.suffix in ALLOWED_SUFFIXES or relative.name in {"LICENSE", "NOTICE"}


def is_tracked(root: Path, relative: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative.as_posix()],
        capture_output=True,
        check=False,
        text=True,
    )
    return result.returncode == 0


def check_payload(root: Path, problems: list[str]) -> None:
    total_size = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == ".git":
            continue
        if ".git" in relative.parts:
            problems.append(f"nested .git directory is not allowed in payload: {relative.as_posix()}")
            continue
        if path.is_symlink():
            problems.append(f"symbolic link is not allowed in payload: {relative.as_posix()}")
            continue
        if path.is_dir() and path.name == "__pycache__":
            continue
        if path.is_file() and "__pycache__" in relative.parts and path.suffix == ".pyc" and not is_tracked(root, relative):
            continue
        if any(part.lower() in FORBIDDEN_DIRECTORIES for part in relative.parts):
            problems.append(f"forbidden payload directory: {relative.as_posix()}")
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden payload file type: {relative.as_posix()}")
            continue
        if not is_allowed(relative):
            problems.append(f"unknown payload path or file type: {relative.as_posix()}")
            continue
        size = path.stat().st_size
        total_size += size
        if size > MAX_FILE_BYTES:
            problems.append(f"single-file size exceeds {MAX_FILE_BYTES} bytes: {relative.as_posix()} ({size})")
    if total_size > MAX_TOTAL_BYTES:
        problems.append(f"total size exceeds {MAX_TOTAL_BYTES} bytes: {total_size}")


def validate(root: Path) -> list[str]:
    root = root.resolve()
    problems: list[str] = []
    if not root.is_dir():
        return [f"plugin root does not exist: {root}"]
    for relative in sorted(REQUIRED_FILES):
        if not (root / relative).is_file():
            problems.append(f"missing required file: {relative}")
    plugin = load_json(root, ".claude-plugin/plugin.json", problems)
    marketplace = load_json(root, ".claude-plugin/marketplace.json", problems)
    if plugin is not None and marketplace is not None:
        check_manifest_paths(root, plugin, marketplace, problems)
    skills_path = root / "skills"
    actual_skills = {path.name for path in skills_path.iterdir() if path.is_dir()} if skills_path.is_dir() else set()
    if actual_skills != EXPECTED_SKILLS:
        problems.append(f"Skill set mismatch: expected {sorted(EXPECTED_SKILLS)}, got {sorted(actual_skills)}")
    for skill in sorted(EXPECTED_SKILLS):
        entry = skills_path / skill / "SKILL.md"
        if not entry.is_file():
            problems.append(f"missing required Skill entry: skills/{skill}/SKILL.md")
    check_payload(root, problems)
    return problems


def main() -> int:
    if len(sys.argv) > 2:
        print("usage: validate_plugin.py [plugin-root]", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path.cwd()
    problems = validate(root)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    print(f"plugin-validation passed: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
