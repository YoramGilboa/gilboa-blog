#!/usr/bin/env python3
"""
validate_rendered_output.py - post-render HTML validator for gilboa.blog.

Deterministic gate that runs AFTER `quarto render`, before chart review.
Scans the rendered post's visible text for values that mean an inline
expression or stats pipeline failed:

  - raw `{python}` left in the page (inline expression did not execute)
  - NaN
  - undefined
  - `None%` (a formatted value came back as None)

A bare `None` in prose is reported as WARN only, since sentences like
"None of them dissented" are legitimate.

Script, style, and pre blocks (code-fold source listings) are stripped first
so legitimate Python source does not trigger false positives. Inline <code>
spans are kept because a failed inline expression renders as one.

Usage (from repo root):
  python tools/validate_rendered_output.py _site/posts/SLUG/index.html
  python tools/validate_rendered_output.py posts/SLUG          # resolved to _site
  python tools/validate_rendered_output.py posts/SLUG/index.qmd [more paths...]

Exit code 0 = no errors, 1 = one or more errors.
Standard library only - no third-party dependencies.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STRIP_BLOCKS_RE = re.compile(
    r"<(script|style|pre)\b.*?</\1>", re.DOTALL | re.IGNORECASE
)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")

ERROR_PATTERNS = [
    ("raw {python} expression", re.compile(r"\{python\}")),
    ("NaN", re.compile(r"\bNaN\b")),
    ("undefined", re.compile(r"\bundefined\b")),
    ("None%", re.compile(r"\bNone\s*%")),
]
# bare None is usually legitimate prose ("None of them dissented") -> WARN only
WARN_PATTERNS = [
    ("bare None (verify it is prose, not a failed value)",
     re.compile(r"\bNone\b(?!\s*%)")),
]


def resolve_html(path: Path) -> Path | None:
    """Accept a rendered HTML file, a post source dir, or its index.qmd."""
    if path.suffix == ".html" and path.is_file():
        return path
    if path.name == "index.qmd":
        path = path.parent
    if path.is_dir():
        try:
            rel = path.resolve().relative_to(REPO_ROOT)
        except ValueError:
            return None
        candidate = REPO_ROOT / "_site" / rel / "index.html"
        if candidate.is_file():
            return candidate
    return None


def visible_text(html: str) -> list[str]:
    html = COMMENT_RE.sub(" ", html)
    html = STRIP_BLOCKS_RE.sub(" ", html)
    html = TAG_RE.sub(" ", html)
    return html.splitlines()


def check_html(html_path: Path):
    errors: list[str] = []
    warnings: list[str] = []
    lines = visible_text(html_path.read_text(encoding="utf-8", errors="replace"))
    for lineno, line in enumerate(lines, start=1):
        for sink, patterns in ((errors, ERROR_PATTERNS), (warnings, WARN_PATTERNS)):
            for label, pattern in patterns:
                for match in pattern.finditer(line):
                    start = max(match.start() - 60, 0)
                    context = " ".join(line[start:match.end() + 60].split())
                    sink.append(f"line {lineno}: {label}: ...{context}...")
    return errors, warnings


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: python tools/validate_rendered_output.py "
              "<rendered.html | post-dir | index.qmd> ...")
        return 1
    exit_code = 0
    for arg in argv:
        html = resolve_html(Path(arg))
        if html is None:
            print(f"ERROR  {arg}: no rendered HTML found (render the post first)")
            exit_code = 1
            continue
        errors, warns = check_html(html)
        rel = html.as_posix()
        if errors:
            exit_code = 1
            print(f"FAIL   {rel}")
            for err in errors:
                print(f"  ERROR  {err}")
        else:
            print(f"OK     {rel}")
        for warn in warns:
            print(f"  WARN   {warn}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
