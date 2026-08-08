#!/usr/bin/env python3
"""Post-render SEO hygiene for the Quarto website output.

Quarto emits sitemap locs with ``/index.html`` (and sometimes root ``index.html``).
Canonical tags (via ``format.html.canonical-url: true``) already prefer clean URLs
like ``https://gilboa.blog/posts/slug/``. This script rewrites ``sitemap.xml`` so
sitemap suggestions match those canonicals.

Run automatically via ``project.post-render`` in ``_quarto.yml``.
Safe to run standalone: ``python tools/seo_post_render.py``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "_site"
SITEMAP = SITE_DIR / "sitemap.xml"

# Match <loc>...</loc> bodies; only rewrite absolute gilboa.blog URLs we own.
LOC_RE = re.compile(
    r"(<loc>)(https://gilboa\.blog[^<]*)(</loc>)",
    re.IGNORECASE,
)


def clean_url(url: str) -> str:
    """Map filesystem-style URLs to clean public URLs."""
    url = url.strip()
    # Root index
    if url in {"https://gilboa.blog/index.html", "https://gilboa.blog/index.htm"}:
        return "https://gilboa.blog/"
    # Directory indexes: .../slug/index.html -> .../slug/
    if url.endswith("/index.html"):
        return url[: -len("index.html")]
    if url.endswith("/index.htm"):
        return url[: -len("index.htm")]
    return url


def rewrite_sitemap(path: Path) -> int:
    if not path.is_file():
        print(f"seo_post_render: no sitemap at {path}, skipping", file=sys.stderr)
        return 0

    original = path.read_text(encoding="utf-8")
    changes = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal changes
        before = match.group(2)
        after = clean_url(before)
        if after != before:
            changes += 1
        return f"{match.group(1)}{after}{match.group(3)}"

    rewritten = LOC_RE.sub(repl, original)
    if changes:
        path.write_text(rewritten, encoding="utf-8", newline="\n")
    print(f"seo_post_render: rewrote {changes} sitemap URL(s) in {path}")
    return changes


def main() -> int:
    rewrite_sitemap(SITEMAP)
    robots = SITE_DIR / "robots.txt"
    if robots.is_file():
        text = robots.read_text(encoding="utf-8")
        if "/posts/drafts/" not in text:
            print(
                "seo_post_render: WARNING robots.txt missing Disallow for /posts/drafts/",
                file=sys.stderr,
            )
    else:
        print("seo_post_render: WARNING no robots.txt in _site/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
