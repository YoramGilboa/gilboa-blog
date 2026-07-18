#!/usr/bin/env python3
"""Audit repository structure that is not covered by per-post linting."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


VALID_POST_SLUG = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
LEGACY_POST_PATHS = {"posts/20260501 April FOMC decision"}
FORBIDDEN_TRACKED_PARTS = {
    ".claude",
    ".idea",
    ".local-archive",
    ".quarto",
    ".quarto-local",
    ".venv",
    ".vscode",
    "__pycache__",
    "_site",
}
FORBIDDEN_TRACKED_SUFFIXES = {".log", ".pyc", ".pyo", ".quarto_ipynb"}
FIGURE_REFERENCE = re.compile(r"figure-html/([^\"'\s)]+\.png)")


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str


def git_tracked_paths(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Unable to list tracked files with git.")
    return {
        value.decode("utf-8").replace("\\", "/")
        for value in result.stdout.split(b"\0")
        if value
    }


def source_post_dirs(repo_root: Path) -> set[str]:
    result: set[str] = set()
    posts_root = repo_root / "posts"
    for index_file in posts_root.glob("*/index.qmd"):
        result.add(index_file.parent.relative_to(repo_root).as_posix())
    drafts_root = posts_root / "drafts"
    for index_file in drafts_root.glob("*/index.qmd"):
        if index_file.parent.name != "_template":
            result.add(index_file.parent.relative_to(repo_root).as_posix())
    return result


def freeze_post_dirs(repo_root: Path) -> set[str]:
    result: set[str] = set()
    freeze_root = repo_root / "_freeze"
    for metadata in freeze_root.glob("posts/**/index/execute-results/html.json"):
        freeze_post = metadata.parents[2]
        result.add(freeze_post.relative_to(freeze_root).as_posix())
    return result


def referenced_figures(metadata_path: Path) -> set[str]:
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    strings: list[str] = []

    def collect(value: object) -> None:
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(payload)
    return {
        match.group(1)
        for value in strings
        for match in FIGURE_REFERENCE.finditer(value)
    }


def nested_git_paths(repo_root: Path) -> list[str]:
    excluded = {".git", ".venv", "_site", ".quarto", ".quarto-local"}
    found: list[str] = []
    for current, dirs, files in os.walk(repo_root):
        relative = Path(current).relative_to(repo_root)
        if relative.parts and relative.parts[0] in excluded:
            dirs[:] = []
            continue
        if ".git" in dirs:
            nested = Path(current) / ".git"
            if nested != repo_root / ".git":
                found.append(nested.relative_to(repo_root).as_posix())
            dirs.remove(".git")
        if ".git" in files:
            nested = Path(current) / ".git"
            found.append(nested.relative_to(repo_root).as_posix())
    return sorted(set(found))


def audit_repository(
    repo_root: Path,
    tracked_paths: set[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    tracked = tracked_paths if tracked_paths is not None else git_tracked_paths(repo_root)
    sources = source_post_dirs(repo_root)
    freezes = freeze_post_dirs(repo_root)

    for source in sorted(sources - freezes):
        if source.startswith("posts/drafts/"):
            continue
        findings.append(
            Finding("missing-freeze", source, "Post source has no matching freeze metadata.")
        )
    for freeze in sorted(freezes - sources):
        findings.append(
            Finding("orphan-freeze", freeze, "Freeze metadata has no matching post source.")
        )

    for source in sorted(sources):
        if source in LEGACY_POST_PATHS or source.startswith("posts/drafts/"):
            continue
        slug = Path(source).name
        if not VALID_POST_SLUG.fullmatch(slug):
            findings.append(
                Finding(
                    "invalid-post-slug",
                    source,
                    "Published post folders must use YYYY-MM-DD-kebab-case.",
                )
            )

    for path in sorted(tracked):
        if not (repo_root / path).exists():
            continue
        parts = set(Path(path).parts)
        suffix = Path(path).suffix.lower()
        if parts & FORBIDDEN_TRACKED_PARTS or suffix in FORBIDDEN_TRACKED_SUFFIXES:
            findings.append(
                Finding("tracked-generated", path, "Generated or local-only file is tracked.")
            )

    freeze_root = repo_root / "_freeze"
    for freeze in sorted(freezes):
        metadata = freeze_root / freeze / "index" / "execute-results" / "html.json"
        figure_dir = freeze_root / freeze / "index" / "figure-html"
        try:
            referenced = referenced_figures(metadata)
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(
                Finding("invalid-freeze-metadata", metadata.relative_to(repo_root).as_posix(), str(exc))
            )
            continue

        actual = {path.name for path in figure_dir.glob("*.png")} if figure_dir.exists() else set()
        for name in sorted(actual - referenced):
            path = (figure_dir / name).relative_to(repo_root).as_posix()
            findings.append(
                Finding("stale-freeze-figure", path, "Figure is not referenced by freeze metadata.")
            )
        for name in sorted(referenced - actual):
            path = (figure_dir / name).relative_to(repo_root).as_posix()
            findings.append(
                Finding("missing-freeze-figure", path, "Freeze metadata references a missing figure.")
            )

    for path in nested_git_paths(repo_root):
        findings.append(Finding("nested-git", path, "Nested Git metadata is not allowed."))

    return sorted(findings, key=lambda item: (item.code, item.path))


def find_repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Run this tool inside the blog repository.")
    return Path(result.stdout.strip()).resolve()


def main() -> int:
    try:
        repo_root = find_repo_root()
        findings = audit_repository(repo_root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if findings:
        for finding in findings:
            print(f"ERROR [{finding.code}] {finding.path}: {finding.message}")
        print(f"\nRepository audit failed with {len(findings)} issue(s).")
        return 1

    print("Repository audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
