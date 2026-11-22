#!/usr/bin/env python3
"""
validate_expressions.py - pre-render inline expression validator for gilboa.blog.

Deterministic gate that runs BEFORE `quarto render`:

  1. Every literal `stats[...]` key referenced in index.qmd must exist in the
     post's stats JSON (stats/*.json, excluding final_review_status.json).
  2. Every inline `{python}` expression must be fully backticked
     (`` `{python} ...` ``) so it executes instead of shipping as raw text.

It enforces FORM, not TRUTH: a key can exist and still hold the wrong number.

Usage (from repo root):
  python tools/validate_expressions.py posts/SLUG
  python tools/validate_expressions.py posts/SLUG/index.qmd [more paths...]

Exit code 0 = no errors, 1 = one or more errors.
Standard library only - no third-party dependencies.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

STATS_KEY_RE = re.compile(r"stats\[\s*['\"]([^'\"]+)['\"]\s*\]")
INLINE_PY_RE = re.compile(r"`\{python\}[^`]*`")
FENCE_OPEN_RE = re.compile(r"^```+\{python\}")
FENCE_CLOSE_RE = re.compile(r"^```+\s*$")
# a # preceded by whitespace/line start is a comment; "#1f4e79" color strings are not
CODE_COMMENT_RE = re.compile(r"(^|\s)#\s.*$")
STATS_DICT_OPEN_RE = re.compile(r"^\s*stats\s*=\s*\{")
DICT_KEY_RE = re.compile(r"['\"]([^'\"]+)['\"]\s*:")
EXCLUDED_STATS_FILES = {"final_review_status.json"}


def resolve_qmd(path: Path) -> Path | None:
    if path.is_dir():
        path = path / "index.qmd"
    if path.name != "index.qmd" or not path.is_file():
        return None
    return path


def load_stats_keys(post_dir: Path):
    """Merge top-level keys from every stats JSON except review artifacts.
    Returns (keys, errors)."""
    keys: set[str] = set()
    errors: list[str] = []
    stats_dir = post_dir / "stats"
    if not stats_dir.is_dir():
        return keys, [f"missing stats directory: {stats_dir}"]
    files = [p for p in sorted(stats_dir.glob("*.json"))
             if p.name not in EXCLUDED_STATS_FILES]
    if not files:
        return keys, [f"no stats JSON files found in {stats_dir}"]
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot parse {path.name}: {exc}")
            continue
        if isinstance(data, dict):
            keys.update(data.keys())
        else:
            errors.append(f"{path.name}: top level is not a JSON object")
    return keys, errors


def check_post(qmd_path: Path) -> list[str]:
    errors: list[str] = []
    key_refs: list[tuple[int, str]] = []
    defined_keys: set[str] = set()

    lines = qmd_path.read_text(encoding="utf-8").splitlines()
    in_fence = False
    dict_depth = 0
    for lineno, line in enumerate(lines, start=1):
        if in_fence:
            if FENCE_CLOSE_RE.match(line):
                in_fence = False
                dict_depth = 0
                continue
            line = CODE_COMMENT_RE.sub("", line)
            if dict_depth > 0:
                defined_keys.update(DICT_KEY_RE.findall(line))
                dict_depth += line.count("{") - line.count("}")
                continue
            if STATS_DICT_OPEN_RE.match(line):
                # older posts define stats inline instead of loading JSON
                defined_keys.update(DICT_KEY_RE.findall(line))
                dict_depth = line.count("{") - line.count("}")
                continue
        elif FENCE_OPEN_RE.match(line):
            in_fence = True
            continue
        else:
            # prose line: every {python} must be inside a backticked span
            raw_count = line.count("{python}")
            if raw_count and raw_count != len(INLINE_PY_RE.findall(line)):
                errors.append(
                    f"line {lineno}: inline {{python}} expression is not fully "
                    f"backticked: {line.strip()[:120]}"
                )
        for match in STATS_KEY_RE.finditer(line):
            rest = line[match.end():].lstrip()
            if in_fence and rest.startswith("=") and not rest.startswith("=="):
                defined_keys.add(match.group(1))
            else:
                key_refs.append((lineno, match.group(1)))

    if key_refs:
        keys = set(defined_keys)
        json_keys, stats_errors = load_stats_keys(qmd_path.parent)
        keys.update(json_keys)
        if not defined_keys:
            # JSON is the only key source, so its problems are errors
            errors.extend(stats_errors)
        for lineno, key in key_refs:
            if key not in keys:
                errors.append(
                    f"line {lineno}: stats key '{key}' not found in stats JSON "
                    "or inline stats definition"
                )
    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: python tools/validate_expressions.py <post-dir | index.qmd> ...")
        return 1
    exit_code = 0
    for arg in argv:
        qmd = resolve_qmd(Path(arg))
        if qmd is None:
            print(f"ERROR  {arg}: not a post directory or index.qmd")
            exit_code = 1
            continue
        errors = check_post(qmd)
        rel = qmd.as_posix()
        if errors:
            exit_code = 1
            print(f"FAIL   {rel}")
            for err in errors:
                print(f"  ERROR  {err}")
        else:
            print(f"OK     {rel}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
