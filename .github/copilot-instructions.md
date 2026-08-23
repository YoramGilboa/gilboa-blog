# gilboa.blog repository instructions

This is the repository-wide operating model. More specific rules:

- `.github/instructions/posts.instructions.md` — post prose and charts
- `.github/instructions/pipelines.instructions.md` — post data pipelines
- `.github/instructions/site.instructions.md` — About, navbar, theme, SEO tabs
- `.github/skills/` — Copilot creation and review workflows
- `~/.grok/skills/blog-*` — Grok factory skills (keep aligned with this file)

## Project

gilboa.blog is a Quarto data-visualization site published to GitHub Pages.
Posts combine QMD prose, Python, matplotlib or seaborn, and committed Quarto
freeze output.

Primary lane: US macro data (CPI, labor, Fed, PPI, BTOS) with reproducible
pipelines. Occasional high-signal one-offs (e.g. open-weight AI / sovereign AI)
are allowed when the human requests them; open with an explicit one-off frame
and keep a chartable data spine. House writing/chart rules live in
`.github/instructions/posts.instructions.md`. Site chrome rules live in
`.github/instructions/site.instructions.md`.

## Working directory

The Git root is `gilboa-blog/` (the folder that contains `_quarto.yml`). Never
treat `tests/` or a post folder as the repo root. Report absolute paths when
creating or editing `.qmd` files.

## Repository rules

- Use one Git repository and one root `.venv`.
- Never create a repository or virtual environment inside a post.
- Commit `_freeze/`; never commit `_site/`, local Quarto caches, or `generated/`
  factory notes.
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

## Site and experiment workflow

1. Site chrome, About, homepage, theme, or SEO-only front matter: branch
   `site/<name>` (not `post/...`).
2. Do not merge to `main` until the human signs off.
3. Do not run post freeze, `check_post`, or undraft steps for site-only work.
4. After sign-off, use **Publishing site changes** below.

## Orchestration

After any narrative, chart, or data fix, re-run the editor (Grok: `blog-editor`;
Copilot: `blog-final-review` plus chart review if visuals changed) **without
being asked**. If the ship bar is not met, keep looping with the named owner.
If it is met, stop and show the human. Do not ask which skill is next when the
review already named an owner.

Ready for human review is not published. Publish only after explicit sign-off.

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

## Local preview

Standard review server:

```powershell
quarto preview --port 4200 --no-browser
```

On Windows the watcher often serves a stale page or a `Quarto Render Error`
(`Bad resource ID` / Sass cache) for root pages such as `about.qmd`.

- Never `quarto render` while preview is holding files (locks `_freeze` / `_site`).
- After a site-page edit: stop preview **and** leftover `deno`/`quarto` on port
  4200, `quarto render <file>`, restart preview.
- Before telling the human localhost is updated, fetch the preview URL and
  confirm the new copy. Reject bodies that contain `Quarto Render Error`.
- When asked to stop preview, kill the process **and** anything still listening
  on 4200.

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

Grok: `blog-publish` post mode. Copilot: this checklist.

## Publishing site changes

Use this path for About, `_quarto.yml`, homepage chrome, CSS/theme, or SEO-only
post front matter. Do **not** run freeze, `check_post`, or undraft.

1. Commit only the signed-off files on `site/<name>`. Never `_site/`, never
   `generated/`, never leftover `index.html` next to a post.
2. `git checkout main` && `git pull origin main`.
3. Merge `site/<name>` into `main` locally (prefer fast-forward).
4. Only then `git push origin main`. Pushing the experiment branch alone does
   not update gilboa.blog.
5. `gh run list --workflow=publish.yml --limit 3` then
   `gh run watch <run-id> --exit-status`.
6. Fetch live URLs and confirm the new strings (not only HTTP 200):
   `https://gilboa.blog/`, `/about.html`, and any edited posts.

Grok: `blog-publish` site mode. Keep `site/<name>` after merge unless asked to
delete it.
