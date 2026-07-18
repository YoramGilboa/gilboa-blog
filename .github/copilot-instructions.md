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

## Skills

- `blog-post-create`: orchestrate a post from topic through human review
- `blog-data-validate`: validate FRED and BEA identifiers and freshness
- `blog-chart-review`: visual-only desktop and mobile chart QA
- `blog-final-review`: non-visual accuracy, flow, and consistency gate

## Publishing requirements

Before merging a post into `main`, confirm:

- lint, repository audit, preflight, chart review, and final review pass;
- `stats/final_review_status.json` contains `PASS`;
- all inline values render and all chart captions have source lines;
- the homepage card has one description and a valid preview image;
- `_freeze/` has only current outputs for the post;
- no unverified `# MANUAL:`, placeholder, or TODO value ships;
- the data-currency note is accurate.
