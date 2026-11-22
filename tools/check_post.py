#!/usr/bin/env python3
"""Preflight checks and optional render for a single post.

This script is the Python source of truth for preflight behavior. The
PowerShell wrapper in scripts/check_post.ps1 forwards to this script.

Excluded drafts render in a temporary, post-local Quarto project using the
site's inspected configuration. Output and freeze go to the canonical root
locations without changing the production configuration or homepage.
Missing review HTML is an error, including with --skip-render.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_expressions
import validate_rendered_output


MAX_RENDERED_FIGURE_WIDTH = 850


def run_cmd(args: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def find_repo_root() -> Path:
    result = run_cmd(["git", "rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        raise RuntimeError("Run this script from inside the blog Git repository.")
    return Path(result.stdout.strip()).resolve()


def resolve_post_file(post_path_arg: str, repo_root: Path) -> tuple[Path, str]:
    candidate = Path(post_path_arg)
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if not candidate.exists():
        raise RuntimeError(f"Post path does not exist: {post_path_arg}")

    if candidate.name != "index.qmd":
        raise RuntimeError("Post path must point to an index.qmd file.")

    try:
        candidate.relative_to(repo_root)
    except ValueError as exc:
        raise RuntimeError(f"Post path must be inside the blog repository: {candidate}") from exc

    relative_post = candidate.relative_to(repo_root).as_posix()
    return candidate, relative_post


def discover_python(repo_root: Path) -> str:
    repo_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if repo_python.exists():
        return str(repo_python)
    return sys.executable


def add_preflight_checks(content: str, post_dir: Path, allow_draft: bool) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []

    if re.search(r"(?m)^draft:\s*true\s*$", content):
        if allow_draft:
            print("Draft mode allowed: frontmatter contains draft: true.")
        else:
            issues.append("Frontmatter still contains draft: true. Use -AllowDraft while checking drafts.")

    if re.search(r"(?m)^##\s+Introduction\s*$", content):
        issues.append("Remove the stale '## Introduction' heading and start with the opening paragraph.")

    if re.search(r"plt\.show\s*\(", content):
        issues.append("Remove plt.show(); Quarto displays figures automatically.")

    if re.search(r"(?m)^\s*from\s+\S+\s+import\s+\*", content):
        issues.append("Remove wildcard imports.")

    stats_path = post_dir / "stats" / "summary_stats.json"
    if "summary_stats.json" in content and not stats_path.exists():
        issues.append("The post loads stats\\summary_stats.json but the file is missing.")

    for error in validate_expressions.check_post(post_dir / "index.qmd"):
        issues.append(f"Inline expression check: {error}")

    final_review_path = post_dir / "stats" / "final_review_status.json"
    if not allow_draft:
        if not final_review_path.exists():
            issues.append(
                "Final review status file is missing: stats\\final_review_status.json. "
                "Run /blog-final-review and ensure status is PASS before publishing."
            )
        else:
            try:
                payload = json.loads(final_review_path.read_text(encoding="utf-8"))
                status = str(payload.get("status", "")).upper()
                if status != "PASS":
                    issues.append(
                        f"Final review status is '{status}' in stats\\final_review_status.json. "
                        "Status must be PASS before publishing."
                    )
            except Exception:
                issues.append(
                    "Unable to parse stats\\final_review_status.json as valid JSON. "
                    "Fix the file and ensure status is PASS before publishing."
                )

    return issues, warnings


def run_pipeline(post_dir: Path, repo_root: Path) -> int:
    scripts_dir = post_dir / "scripts"
    if not scripts_dir.exists():
        print("No post scripts directory found; skipping pipeline.")
        return 0

    py = discover_python(repo_root)
    for script in sorted(scripts_dir.glob("*.py")):
        if not re.match(r"^\d+_.*\.py$", script.name):
            continue
        print(f"Running pipeline script: {script.name}")
        result = subprocess.run([py, str(script)], cwd=str(post_dir), check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


def draft_project_config(repo_root: Path, relative_post: str, env: dict[str, str]) -> dict:
    inspected = run_cmd(["quarto", "inspect", str(repo_root)], cwd=repo_root, env=env)
    if inspected.returncode != 0:
        raise RuntimeError(f"Unable to inspect the site configuration:\n{inspected.stderr}")
    config = json.loads(inspected.stdout)["config"]
    config["project"] = {
        "type": "website",
        "output-dir": str(rendered_html_path(repo_root, relative_post).parent),
        "render": ["index.qmd"],
    }
    config["draft-mode"] = "unlinked"
    website = config["website"]
    website["draft-mode"] = "unlinked"
    site_url = website["site-url"].rstrip("/")
    website["site-url"] = site_url + "/" + Path(relative_post).parent.as_posix()

    def asset(value: str) -> str:
        path = repo_root / value
        if path.is_file():
            return os.path.relpath(path, (repo_root / relative_post).parent).replace("\\", "/")
        return value

    website["favicon"] = asset(website["favicon"])
    for section in (website.get("navbar", {}), website.get("page-footer", {})):
        for side in ("left", "right"):
            items = section.get(side, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and "href" in item:
                    href = item["href"]
                    if not href.startswith(("https://", "http://", "mailto:", "#")):
                        target = Path(href).with_suffix(".html") if href.endswith(".qmd") else Path(href)
                        item["href"] = site_url + ("/" if href == "index.qmd" else "/" + target.as_posix().lstrip("/"))
    html = config["format"]["html"]
    if isinstance(html.get("theme"), str):
        html["theme"] = asset(html["theme"])
    html["css"] = [asset(value) for value in html.get("css", [])]
    for value in html.get("include-in-header", []):
        if isinstance(value, dict) and "file" in value:
            value["file"] = asset(value["file"])
    return config


def run_render(repo_root: Path, relative_post: str) -> int:
    env = os.environ.copy()
    quarto_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if quarto_python.exists():
        env["QUARTO_PYTHON"] = str(quarto_python)

    quarto_local = repo_root / ".quarto-local"
    quarto_local_appdata = quarto_local / "localappdata"
    quarto_log_dir = quarto_local / "logs"
    quarto_local_appdata.mkdir(parents=True, exist_ok=True)
    quarto_log_dir.mkdir(parents=True, exist_ok=True)
    env["LOCALAPPDATA"] = str(quarto_local_appdata)
    env["DENO_DIR"] = str(quarto_local / "deno")
    env["IPYTHONDIR"] = str(quarto_local / "ipython")
    env["QUARTO_LOG"] = str(quarto_log_dir / "quarto.log")

    freeze_before = run_cmd(["git", "status", "--porcelain", "--", "_freeze"], cwd=repo_root, env=env).stdout

    print(f"Rendering {relative_post}")
    post_dir = (repo_root / relative_post).parent
    is_draft = Path(relative_post).parts[:2] == ("posts", "drafts")
    config_path = post_dir / "_quarto.yml"
    local_freeze = post_dir / "_freeze"
    local_output = post_dir / ".review-site"
    if is_draft:
        if config_path.exists() or local_freeze.exists() or local_output.exists():
            raise RuntimeError(f"Remove or resolve the existing draft-local project/freeze before review: {post_dir}")
        config = draft_project_config(repo_root, relative_post, env)
        config["project"]["output-dir"] = str(local_output)
        with config_path.open("x", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
    try:
        render = subprocess.run(["quarto", "render", str(repo_root / relative_post)], cwd=str(repo_root), env=env, check=False)
        if render.returncode != 0:
            return render.returncode
        if is_draft:
            if not (local_output / "index.html").is_file():
                raise RuntimeError(f"Quarto did not create the draft review page: {local_output}")
            shutil.copytree(local_output, rendered_html_path(repo_root, relative_post).parent, dirs_exist_ok=True)
            for value in [*config["format"]["html"].get("css", []), config["website"]["favicon"]]:
                source = (post_dir / value).resolve()
                if source.is_file():
                    target = repo_root / "_site" / source.relative_to(repo_root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            if (local_freeze / "index").is_dir():
                target = repo_root / "_freeze" / Path(relative_post).parent / "index"
                shutil.copytree(local_freeze / "index", target, dirs_exist_ok=True)
    finally:
        if is_draft:
            config_path.unlink()
            if local_freeze.exists():
                shutil.rmtree(local_freeze)
            if local_output.exists():
                shutil.rmtree(local_output)

    freeze_after = run_cmd(["git", "status", "--porcelain", "--", "_freeze"], cwd=repo_root, env=env).stdout
    if freeze_after != freeze_before:
        print("_freeze changed during render; review and commit the relevant updates.")
    else:
        print("_freeze did not change during render.")

    return 0


def rendered_html_path(repo_root: Path, relative_post: str) -> Path:
    return repo_root / "_site" / Path(relative_post).with_suffix(".html")


def add_rendered_output_checks(repo_root: Path, relative_post: str, post_file: Path) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []

    rendered_html = rendered_html_path(repo_root, relative_post)
    if not rendered_html.exists():
        issues.append(f"Rendered HTML not found for post-review checks: {rendered_html.relative_to(repo_root)}")
        return issues, warnings

    html = rendered_html.read_text(encoding="utf-8")

    html_errors, html_warnings = validate_rendered_output.check_html(rendered_html)
    issues.extend(f"Rendered output check: {error}" for error in html_errors)
    warnings.extend(f"Rendered output check: {warning}" for warning in html_warnings)

    caption_count = len(re.findall(r'<figcaption\b', html))
    source_count = len(re.findall(r'class="figure-source"', html))
    if caption_count and source_count < caption_count:
        issues.append(
            f"Rendered HTML has {caption_count} figure caption(s) but only {source_count} .figure-source line(s)."
        )

    widths = [int(match) for match in re.findall(r'<img[^>]+class="figure-img"[^>]+width="(\d+)"', html)]
    oversized = [width for width in widths if width > MAX_RENDERED_FIGURE_WIDTH]
    if oversized:
        warnings.append(
            "Rendered figure image(s) exceed the preferred review width of "
            f"{MAX_RENDERED_FIGURE_WIDTH}px: {', '.join(str(width) for width in oversized)}. "
            "The browser may shrink these images and make chart text look smaller than intended."
        )

    freeze_figure_dir = repo_root / "_freeze" / Path(relative_post).parent / "index" / "figure-html"
    if freeze_figure_dir.exists():
        duplicate_groups: list[str] = []
        for first_output in sorted(freeze_figure_dir.glob("*-output-1.png")):
            prefix = first_output.name[:-len("output-1.png")]
            alternates = sorted(freeze_figure_dir.glob(f"{prefix}output-*.png"))
            if len(alternates) > 1:
                duplicate_groups.append(first_output.name.replace("-output-1.png", ""))
        if duplicate_groups:
            warnings.append(
                "_freeze contains multiple output images for these figures: "
                f"{', '.join(duplicate_groups)}. Review for stale duplicate render artifacts."
            )

    content = post_file.read_text(encoding="utf-8")
    if "#| fig-cap:" in content and ("Interpretation:" in content or "fig.text(" in content):
        warnings.append(
            "Post source contains both Quarto figure captions and in-chart interpretation text markers. "
            "Review for duplicate caption systems."
        )

    return issues, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight checks and render for a post index.qmd")
    parser.add_argument("post_path", help="Path to post index.qmd (absolute or relative)")
    parser.add_argument("--run-pipeline", action="store_true", help="Run numbered scripts in post scripts/ before render")
    parser.add_argument("--allow-draft", action="store_true", help="Allow draft:true in frontmatter")
    parser.add_argument("--skip-render", action="store_true", help="Skip quarto render")
    args = parser.parse_args()

    try:
        repo_root = find_repo_root()
        post_file, relative_post = resolve_post_file(args.post_path, repo_root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    content = post_file.read_text(encoding="utf-8")
    post_dir = post_file.parent

    issues, warnings = add_preflight_checks(content, post_dir, args.allow_draft)

    freeze_tracked = run_cmd(["git", "ls-files", "_freeze"], cwd=repo_root)
    if freeze_tracked.returncode != 0 or not freeze_tracked.stdout.strip():
        issues.append("_freeze is not tracked by Git.")

    site_ignored = run_cmd(["git", "check-ignore", "-q", "_site"], cwd=repo_root)
    if site_ignored.returncode != 0:
        issues.append("_site is not ignored by Git.")

    if issues:
        print(f"Preflight failed for {relative_post}")
        for issue in issues:
            print(f" - {issue}")
        return 1

    if args.run_pipeline:
        rc = run_pipeline(post_dir, repo_root)
        if rc != 0:
            return rc

    if not args.skip_render:
        try:
            rc = run_render(repo_root, relative_post)
        except (RuntimeError, OSError, ValueError, KeyError) as exc:
            print(f"Render failed: {exc}", file=sys.stderr)
            return 1
        if rc != 0:
            return rc

    rendered_issues, rendered_warnings = add_rendered_output_checks(repo_root, relative_post, post_file)
    issues.extend(rendered_issues)
    warnings.extend(rendered_warnings)

    if issues:
        print(f"Preflight failed for {relative_post}")
        for issue in issues:
            print(f" - {issue}")
        return 1

    if warnings:
        print(f"Preflight warnings for {relative_post}")
        for warning in warnings:
            print(f" - {warning}")

    print(f"Preflight passed for {relative_post}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
