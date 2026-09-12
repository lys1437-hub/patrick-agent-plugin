#!/usr/bin/env python3
"""Validate the exact files shipped by the root-source marketplace plugin."""

from __future__ import annotations

import json
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
    if not isinstance(value, dict):
        problems.append(f"{relative_path} must contain a JSON object")
        return None
    return value


def check_manifest_paths(root: Path, plugin: dict, marketplace: dict, problems: list[str]) -> None:
    for key in ("skills", "agents"):
        entries = plugin.get(key, [])
        if not isinstance(entries, list):
            problems.append(f"plugin.json {key} must be a list")
            continue
        for entry in entries:
            if not isinstance(entry, str) or not entry.startswith("./"):
                problems.append(f"plugin.json {key} has an invalid local path: {entry!r}")
                continue
            target = root / entry[2:]
            if not target.exists():
                problems.append(f"plugin.json declares a missing path: {entry[2:]}")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        problems.append("marketplace.json plugins must be a list")
        return
    for entry in plugins:
        if not isinstance(entry, dict):
            problems.append("marketplace.json plugins entries must be objects")
            continue
        source = entry.get("source")
        if not isinstance(source, str):
            continue  # External plugin sources are deliberately not local payload paths.
        if source != "./":
            problems.append(f"marketplace.json has an unsupported local source: {source!r}")
        elif not (root / ".claude-plugin" / "plugin.json").is_file():
            problems.append("marketplace.json root source is missing .claude-plugin/plugin.json")


def is_allowed(relative: Path) -> bool:
    text = relative.as_posix()
    if text in ALLOWED_EXACT_FILES:
        return True
    if not relative.parts or relative.parts[0] not in {"skills", "portfolio"}:
        return False
    return relative.suffix in ALLOWED_SUFFIXES or relative.name in {"LICENSE", "NOTICE"}


def check_payload(root: Path, problems: list[str]) -> None:
    total_size = 0
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts:
            continue
        relative = path.relative_to(root)
        if any(part in FORBIDDEN_DIRECTORIES for part in relative.parts):
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
    check_payload(root, problems)
    return problems


def main() -> int:
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
