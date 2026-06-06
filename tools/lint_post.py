#!/usr/bin/env python3
"""
lint_post.py - deterministic guardrails for gilboa.blog posts.

Mechanical checks that enforce the form rules in CLAUDE.md so they do not
depend on anyone remembering them. This is the engine behind the pre-commit
hook (.githooks/pre-commit) and the CI gate (.github/workflows/publish.yml).

It enforces FORM, not TRUTH: it can catch a stray `subtitle:` field or an
em dash, but it cannot tell you whether a chart's labels overlap (use
/blog-chart-review for that) or whether a consensus figure is the correct
number (only a source check can be enforced, not the value).

Severities:
  ERROR  -> non-zero exit; blocks the commit / fails the deploy.
  WARN   -> printed, does not block.

Usage (from repo root):
  python tools/lint_post.py --all                 # every published post
  python tools/lint_post.py --staged              # staged published index.qmd
  python tools/lint_post.py posts/SLUG/index.qmd  # explicit path(s)

Exit code 0 = no errors (warnings allowed), 1 = one or more errors.
Standard library only - no third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ERROR = "ERROR"
WARN = "WARN"


class Finding:
    def __init__(self, severity: str, code: str, message: str):
        self.severity = severity
        self.code = code
        self.message = message


# ----------------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------------

def split_frontmatter(text: str):
    """Return (frontmatter_lines, body_text). Frontmatter is the block between
    the first two `---` delimiters at the top of the file."""
    if not text.startswith("---"):
        return [], text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return [], text
    fm = lines[1:end]
    body = "\n".join(lines[end + 1:])
    return fm, body


def frontmatter_keys(fm_lines):
    """Map top-level scalar keys to their raw string value (best-effort, no
    YAML dependency). Only top-level `key: value` lines are captured."""
    keys = {}
    for line in fm_lines:
        if line[:1] in (" ", "\t", "#") or not line.strip():
            continue
        m = re.match(r"^([A-Za-z0-9_\-\"]+)\s*:\s*(.*)$", line)
        if m:
            key = m.group(1).strip().strip('"')
            keys[key] = m.group(2).strip()
    return keys


def prose_lines(body: str):
    """Yield (lineno, text) for prose lines only - outside ``` code fences."""
    in_fence = False
    for n, line in enumerate(body.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield n, line


# ----------------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------------

def check_frontmatter(keys, post_dir: Path, findings, strict: bool):
    # `subtitle:`, a missing description, and a missing image are "listing/SEO"
    # rules. They are ERRORs for a post you are actively editing (strict), but
    # only WARNs in a full-repo scan so latent issues in legacy posts do not
    # block every deploy. `strict` is True for staged/explicitly-named posts
    # and False for `--all`.
    listing_sev = ERROR if strict else WARN

    # The bug that shipped this session: a `subtitle:` renders as the listing
    # card's description line and doubles up with `description:` / the excerpt.
    if "subtitle" in keys:
        findings.append(Finding(
            listing_sev, "subtitle",
            "frontmatter has `subtitle:` - it renders as the homepage listing "
            "description and doubles up with `description:` / the excerpt. Use "
            "`description:` only (or `description-meta:` for SEO text that "
            "should differ from the listing card)."))

    if "description" not in keys or not keys.get("description"):
        findings.append(Finding(
            listing_sev, "no-description",
            "frontmatter is missing a non-empty `description:` (used by the "
            "listing card, search engines, and social previews)."))

    img = keys.get("image", "").strip().strip('"')
    if not img:
        findings.append(Finding(
            listing_sev, "no-image",
            "frontmatter is missing an `image:` for the social preview."))
    else:
        if not (post_dir / img).exists():
            findings.append(Finding(
                listing_sev, "image-missing",
                f"`image: {img}` does not exist at {post_dir.name}/{img}. "
                "Render the post so the figure is saved, or fix the path."))

    # Categories: CLAUDE.md wants lowercase, space-separated (no hyphens).
    cats_raw = keys.get("categories", "")
    cats = re.findall(r"[A-Za-z][A-Za-z \-]*", cats_raw)
    for c in cats:
        c = c.strip()
        if not c:
            continue
        if "-" in c:
            findings.append(Finding(
                WARN, "category-hyphen",
                f"category '{c}' uses a hyphen; CLAUDE.md wants lowercase, "
                "space-separated labels (e.g. 'labor market')."))
        if c != c.lower():
            findings.append(Finding(
                WARN, "category-case",
                f"category '{c}' is not lowercase."))


def check_prose(body: str, findings):
    for n, line in prose_lines(body):
        # Standalone horizontal rules (`---`, `***`) are legitimate markdown.
        if line.strip() in ("---", "***", "___"):
            continue
        if "—" in line or "–" in line:  # em dash / en dash
            findings.append(Finding(
                ERROR, "unicode-dash",
                f"line {n}: contains an em/en dash (— or –). "
                "CLAUDE.md forbids these - use spaced hyphens, commas, or "
                "restructured sentences."))
        if re.search(r"\w ?-- ?\w", line) or re.search(r"\w--\w", line):
            findings.append(Finding(
                WARN, "ascii-dash",
                f"line {n}: inline '--' renders as an en/em dash in Quarto. "
                "Use ' - ' or restructure."))
        if re.search(r"\bclick here\b", line, re.IGNORECASE):
            findings.append(Finding(
                ERROR, "click-here",
                f"line {n}: 'click here' link text is banned - use a full, "
                "descriptive link or URL."))
        if "<style" in line.lower():
            findings.append(Finding(
                ERROR, "inline-style",
                f"line {n}: inline <style> block - shared styles belong in "
                "styles.css at the repo root."))

    # Wildcard imports anywhere in the file (code chunks included).
    for m in re.finditer(r"^\s*from\s+[\w.]+\s+import\s+\*", body, re.MULTILINE):
        findings.append(Finding(
            ERROR, "wildcard-import",
            "wildcard import (`from ... import *`) is banned."))

    # Soft flags for unfinished work.
    for token in ("TODO", "FIXME", "XXX", "placeholder", "PLACEHOLDER"):
        if token in body:
            findings.append(Finding(
                WARN, "unfinished",
                f"body contains '{token}' - confirm it is intentional before "
                "publishing."))
            break


def check_stats(qmd_text: str, post_dir: Path, findings):
    stats_path = post_dir / "stats" / "summary_stats.json"
    references_stats = "summary_stats.json" in qmd_text
    if stats_path.exists():
        try:
            json.loads(stats_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            findings.append(Finding(
                ERROR, "stats-invalid",
                f"stats/summary_stats.json is not valid JSON: {exc}"))
    elif references_stats:
        findings.append(Finding(
            ERROR, "stats-missing",
            "post references summary_stats.json but stats/summary_stats.json "
            "does not exist - run scripts/04_compute_stats.py."))


def check_manual_values(post_dir: Path, findings):
    """Every `# MANUAL:` value (a number that cannot be fetched, e.g. a
    consensus estimate) must declare a source. This raises the floor - it
    forces a citation, though it cannot verify the value is correct."""
    scripts = post_dir / "scripts"
    if not scripts.exists():
        return
    for py in scripts.glob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"#\s*MANUAL:(.*)", text):
            comment = m.group(1)
            window_start = m.start()
            window = text[window_start:window_start + 400]
            has_source = (
                re.search(r"source", comment, re.IGNORECASE)
                or "http" in window.lower()
                or re.search(r"_source", window)
            )
            if not has_source:
                findings.append(Finding(
                    WARN, "manual-no-source",
                    f"{py.name}: a '# MANUAL:' value has no nearby source "
                    "citation. Every non-fetchable value must name its "
                    "primary source."))


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

def lint_post(qmd_path: Path, strict: bool = True):
    findings: list[Finding] = []
    post_dir = qmd_path.parent
    text = qmd_path.read_text(encoding="utf-8", errors="ignore")
    fm_lines, body = split_frontmatter(text)
    keys = frontmatter_keys(fm_lines)

    check_frontmatter(keys, post_dir, findings, strict)
    check_prose(body, findings)
    check_stats(text, post_dir, findings)
    check_manual_values(post_dir, findings)
    return findings


def discover_published():
    """All published posts: posts/<slug>/index.qmd, excluding drafts/."""
    out = []
    posts = REPO_ROOT / "posts"
    for d in sorted(posts.iterdir()):
        if not d.is_dir() or d.name == "drafts":
            continue
        qmd = d / "index.qmd"
        if qmd.exists():
            out.append(qmd)
    return out


def discover_staged():
    res = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    out = []
    for line in res.stdout.splitlines():
        if re.match(r"^posts/[^/]+/index\.qmd$", line):
            out.append(REPO_ROOT / line)
    return out


def main():
    ap = argparse.ArgumentParser(description="Lint gilboa.blog posts.")
    ap.add_argument("paths", nargs="*", help="post index.qmd paths or dirs")
    ap.add_argument("--all", action="store_true", help="lint all published posts")
    ap.add_argument("--staged", action="store_true", help="lint staged posts")
    args = ap.parse_args()

    # Full-repo scans are lenient on listing/SEO rules so latent issues in
    # legacy posts do not block the deploy; active authoring (staged or named)
    # is strict.
    strict = not args.all
    targets: list[Path] = []
    if args.all:
        targets = discover_published()
    elif args.staged:
        targets = discover_staged()
    else:
        for p in args.paths:
            path = Path(p)
            if not path.is_absolute():
                path = REPO_ROOT / p
            if path.is_dir():
                path = path / "index.qmd"
            targets.append(path)

    if not targets:
        print("lint_post: nothing to lint.")
        return 0

    total_errors = 0
    total_warns = 0
    for qmd in targets:
        if not qmd.exists():
            print(f"  SKIP (not found): {qmd}")
            continue
        findings = lint_post(qmd, strict=strict)
        rel = qmd.relative_to(REPO_ROOT)
        errs = [f for f in findings if f.severity == ERROR]
        warns = [f for f in findings if f.severity == WARN]
        total_errors += len(errs)
        total_warns += len(warns)
        if not findings:
            print(f"PASS  {rel}")
        else:
            status = "FAIL" if errs else "WARN"
            print(f"{status}  {rel}")
            for f in findings:
                print(f"    [{f.severity}] {f.code}: {f.message}")

    print(f"\nSummary: {total_errors} error(s), {total_warns} warning(s) "
          f"across {len(targets)} post(s).")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
