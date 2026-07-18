#!/usr/bin/env python3
"""Preview or remove safe, reproducible local build and cache artifacts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIRECTORIES = (".quarto", ".quarto-local", "_site")
PRUNED_DIRECTORIES = {".git", ".venv", "_freeze"}
CACHE_DIRECTORY_NAMES = {"__pycache__"}
CACHE_SUFFIXES = {".pyc", ".pyo"}


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


def cleanup_targets(repo_root: Path) -> list[Path]:
    targets: set[Path] = {
        repo_root / name
        for name in ROOT_DIRECTORIES
        if (repo_root / name).exists()
    }

    def walk(directory: Path) -> None:
        for child in directory.iterdir():
            if child.is_dir():
                if child.name in PRUNED_DIRECTORIES:
                    continue
                if child.name in CACHE_DIRECTORY_NAMES:
                    targets.add(child)
                else:
                    walk(child)
            elif child.suffix.lower() in CACHE_SUFFIXES:
                targets.add(child)

    walk(repo_root)
    return sorted(targets, key=lambda path: path.as_posix())


def remove_targets(targets: list[Path]) -> None:
    for target in targets:
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview safe local cleanup; pass --apply to remove listed paths."
    )
    parser.add_argument("--apply", action="store_true", help="Remove the listed artifacts.")
    args = parser.parse_args()

    try:
        repo_root = find_repo_root()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    targets = cleanup_targets(repo_root)
    action = "Removing" if args.apply else "Would remove"
    for target in targets:
        print(f"{action}: {target.relative_to(repo_root)}")

    if args.apply:
        remove_targets(targets)
        print(f"Removed {len(targets)} local artifact(s).")
    else:
        print(f"Found {len(targets)} local artifact(s). Run with --apply to remove them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
