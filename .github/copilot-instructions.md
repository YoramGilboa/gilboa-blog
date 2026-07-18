# gilboa.blog - Copilot instructions

This is the canonical instruction file for working on this repository with VS Code Copilot.

## Quick operating model

- Use one repo-root `.venv` only.
- Commit `_freeze/`; never commit `_site/`.
- Keep post assets together: `index.qmd`, `images/`, `stats/`, optional `scripts/`, and matching `_freeze/`.
- Enforce quality with existing guardrails:
  - `python tools/lint_post.py <post-dir>`
  - pre-commit hook in `.githooks/pre-commit`
  - CI gate in `.github/workflows/publish.yml`

## Authoring workflow

1. Copy `posts/drafts/_template/` to `posts/drafts/YYYY-MM-DD-slug/`.
2. Draft with `draft: true`.
3. Run preflight while drafting:
   - `bash scripts/check_post.sh posts/drafts/YYYY-MM-DD-slug/index.qmd --allow-draft`
   - PowerShell: `.\scripts\check_post.ps1 posts\drafts\YYYY-MM-DD-slug\index.qmd -AllowDraft`
4. Move to `posts/YYYY-MM-DD-slug/` when ready.
5. Run local release gate before merge:
   - `bash scripts/local_release_gate.sh posts/YYYY-MM-DD-slug/index.qmd`
6. Merge locally into `main` only after gate success, then push.

## Data fetching patterns

Choose one pattern per post based on complexity.

### Pattern A - Inline fetch in `index.qmd` (default for simpler FRED-only posts)
- Fetch and transform in hidden code chunks (`#| echo: false`).
- Include FRED CSV fallback if client libraries are unavailable.
- Best when preprocessing is small and post-specific.

### Pattern B - Scripted pipeline (for complex/multi-source posts)
- Use `scripts/01_fetch_data.py`, `02_clean_data.py`, optional `03_visualizations.py`, `04_compute_stats.py`.
- Keep `.qmd` focused on narrative and charting.
- Best when transforms are heavier or reusable.

## Required post conventions

- Frontmatter includes `title`, `date`, `author`, `categories`, `description`, `image`, `draft`, TOC and code-fold fields.
- Do not use `subtitle:` in frontmatter.
- No wildcard imports.
- No em/en dashes in prose.
- No hard-coded key figures in prose; use inline `{python}` values from stats.

## Setup block conventions

- First code block is hidden setup (`#| echo: false`).
- Standard helpers:
  - `fmt(n)` and `fmt_chg(n)`
  - `annualized(series, months)` for momentum transforms
  - endpoint-label helper (for overlap-safe end labels)
- Use semantic color keys in `COLORS` and reuse consistently across charts.

## Metric cards and stats

- Use responsive card grid immediately after setup when surfacing 3-5 headline numbers.
- Pull card values from `stats/summary_stats.json`.
- Keep a baseline stats set for reuse:
  - `latest_month`
  - `latest_month_short`
  - `data_current_as_of`
  - plus post-specific metrics used by prose/charts

## Reproducibility callout

Use a "Reproducing this analysis" callout immediately after opening paragraph:
- Pattern A posts: describe inline fetch + transform approach and data sources.
- Pattern B posts: list numbered scripts and source systems.

## Review steps before publish

- Lint: `python tools/lint_post.py <post-dir>`
- Chart QA and final editorial QA via project Copilot skills.
- Verify `stats/final_review_status.json` is `PASS` before release.
- Confirm homepage card renders as expected (no duplicate description line).

## Copilot skills in this repo

Project skills are defined in `.claude/commands/` and can be invoked from Copilot chat:
- `blog-post-create`
- `blog-data-validate`
- `blog-chart-review`
- `blog-final-review`

## Related files

- Quick-start: `README.md`
- Template: `posts/drafts/_template/index.qmd`
- Legacy compatibility/reference guidance: `CLAUDE.md`
