# gilboa.blog repository instructions

This is the repository-wide operating model for GitHub Copilot. More specific
rules are loaded from:

- `.github/instructions/posts.instructions.md` for post prose and charts
- `.github/instructions/pipelines.instructions.md` for post data pipelines
- `.github/skills/` for reusable creation and review workflows

## Project

gilboa.blog is a Quarto data-visualization site published to GitHub Pages.
Posts combine QMD prose, Python, matplotlib or seaborn, and committed Quarto
freeze output.

Primary lane: US macro data (CPI, labor, Fed, PPI, BTOS) with reproducible
pipelines. Occasional high-signal one-offs (e.g. open-weight AI / sovereign AI)
are allowed when the human requests them; open with an explicit one-off frame
and keep a chartable data spine. House writing/chart rules live in
`.github/instructions/posts.instructions.md` (US dates in prose, sparse bold,
no single-item bullets, composite-metric caveats, frontier-chart hygiene).

## Repository rules

- Use one Git repository and one root `.venv`.
- Never create a repository or virtual environment inside a post.
- Commit `_freeze/`; never commit `_site/` or local Quarto caches.
- Commit each post's `index.qmd`, scripts, stats, images, required source or
  cleaned data, and matching `_freeze/` entry.
- Do not commit regenerable top-level FRED series caches under
  `posts/*/data/*.csv`.
- Do not modify unrelated published posts during new-post work.
- Preserve published folder names because they are public URLs.

## Authoring workflow

1. Create branch `post/YYYY-MM-DD-slug`.
2. Copy `posts/drafts/_template/` to `posts/drafts/YYYY-MM-DD-slug/`.
3. Propose the section and chart plan before writing chart code.
4. Draft with `draft: true`.
5. Validate data series before building or changing a pipeline.
6. Run preflight while drafting:
   - `bash scripts/check_post.sh posts/drafts/YYYY-MM-DD-slug/index.qmd --allow-draft`
   - PowerShell: `.\scripts\check_post.ps1 posts\drafts\YYYY-MM-DD-slug\index.qmd -AllowDraft`
7. Run `blog-chart-review`, then `blog-final-review`.
8. After human approval, remove `draft: true`, move the post and freeze cache
   to published paths, and rerender.
9. Run the local release gate:
   - `bash scripts/local_release_gate.sh posts/YYYY-MM-DD-slug/index.qmd`
10. Commit on the post branch, merge locally into `main`, and push only after
    the release gate succeeds.

## Path and artifact contract

- While drafting, create and update post files only under
  `posts/drafts/YYYY-MM-DD-slug/`.
- For published posts, source files live under `posts/YYYY-MM-DD-slug/`.
- Rendered review HTML is read from `_site/posts/.../index.html`.
- Do not treat source-folder `index.html` files as canonical review artifacts.

## Guardrails

- `python tools/lint_post.py <post-dir>` checks one post.
- `python tools/lint_post.py --staged` is the pre-commit check.
- `python tools/lint_post.py --all` is the CI lint gate.
- `python tools/audit_repository.py` checks repository hygiene.
- `scripts/check_post.*` runs per-post preflight and rendering.
- `scripts/local_release_gate.sh` blocks publishing without a passing final
  review artifact.

These tools check form and repository state. Visual quality and analytical
truth still require the chart and final-review skills.

## Interaction contracts

- If the user asks for raw generated QMD output only, return content without
  writing files unless they explicitly ask to save it.
- When files are created or moved, always report final absolute paths.
- In `[[PLAN]]` mode, use read-only analysis only. Do not run mutating file or
  shell actions until approval is granted.
- If a required tool is unavailable, return one concise blocked status and wait
  for new user direction instead of repeating completion messages.

## Review scoring convention

- When both presentation quality and release-readiness are discussed, report
  them as separate scores or clearly separated assessments.
- If these assessments diverge, include a one-line explanation of the gap.

## Skills

- `blog-post-create`: orchestrate a post from topic through human review
- `blog-data-validate`: validate FRED and BEA identifiers and freshness
- `blog-chart-review`: visual-only desktop and mobile chart QA
- `blog-final-review`: non-visual accuracy, flow, and consistency gate
- External Grok skills (when present): topic-selection, architect,
  data-engineer, viz-specialist, narrative-writer, editor, publish

## Publishing requirements

Before merging a post into `main`, confirm:

- lint, repository audit, preflight, chart review, and final review pass;
- `stats/final_review_status.json` contains `PASS`;
- all inline values render (no raw `{python}` left in HTML) and all chart
  captions have source lines;
- every inline expression is fully backticked in `index.qmd`;
- the homepage card has one description and a valid preview image;
- `_freeze/` has only current outputs for the post;
- no unverified `# MANUAL:`, placeholder, or TODO value ships;
- the data-currency note is accurate;
- draft factory artifacts (`generated/*` reviews, `regen_charts.py`) are not
  required in the published commit.

Publish only after human approval; then undraft, move out of `posts/drafts/`,
freeze, gate, commit post + freeze only, merge `main`, push, verify Actions.
