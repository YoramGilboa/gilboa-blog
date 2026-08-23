# Gilboa Blog

Quarto-based data visualization blog published at [gilboa.blog](https://gilboa.blog).
This directory is the canonical Git repository for the site.
For full editorial, chart, and pipeline standards, use
[.github/copilot-instructions.md](./.github/copilot-instructions.md) as the
canonical guide; this README is the quick-start.

## Repository Layout

- `_quarto.yml` - site configuration
- `posts/` - published posts
- `posts/drafts/` - draft posts
- `posts/drafts/_template/` - starting point for new posts
- `_freeze/` - committed Quarto execution cache used by publishing
- `_site/` - generated local output, ignored by Git
- `.github/instructions/` - scoped post, pipeline, and site-chrome guidance
- `.github/skills/` - tracked blog creation and review skills
- `scripts/` - reusable project-level utilities

## Local Setup

```bash
source .venv/Scripts/activate
pip install -r requirements.txt
git config core.hooksPath .githooks
```

Start the local site on the standard review port (from the repo root):

```bash
quarto preview --port 4200 --no-browser
```

Do not `quarto render` while preview is running. After editing `about.qmd` or
other root pages, stop preview (and leftover `deno` on 4200), render the file,
restart preview, then fetch the URL and confirm the new copy. Full recipe:
[.github/copilot-instructions.md](./.github/copilot-instructions.md) (Local
preview).

## Create a Post

Copy the draft template to a dated slug folder:

```bash
cp -r posts/drafts/_template posts/drafts/YYYY-MM-DD-slug
```

Write the post in `posts\drafts\YYYY-MM-DD-slug\index.qmd`. Keep `draft: true`
until it is ready to publish.

House writing and chart rules (including deliberate non-macro one-offs, US
month/day dates from stats, unnumbered section titles, sparse bold, no
single-item bullets, composite-metric caveats, frontier-chart hygiene) live in
[.github/instructions/posts.instructions.md](./.github/instructions/posts.instructions.md).
Pipeline rules live in
[.github/instructions/pipelines.instructions.md](./.github/instructions/pipelines.instructions.md).
About, navbar, and theme rules live in
[.github/instructions/site.instructions.md](./.github/instructions/site.instructions.md).

## Check and Render a Post

Run the project preflight from the repository root:

```bash
bash scripts/check_post.sh posts/drafts/YYYY-MM-DD-slug/index.qmd --allow-draft
```

PowerShell equivalent:

```powershell
.\scripts\check_post.ps1 posts\drafts\YYYY-MM-DD-slug\index.qmd -AllowDraft
```

To run numbered pipeline scripts before rendering:

```bash
bash scripts/check_post.sh posts/drafts/YYYY-MM-DD-slug/index.qmd --allow-draft --run-pipeline
```

PowerShell equivalent:

```powershell
.\scripts\check_post.ps1 posts\drafts\YYYY-MM-DD-slug\index.qmd -AllowDraft -RunPipeline
```

The preflight checks for stale template headings, `draft: true`, `plt.show()`,
wildcard imports, missing stats files when stats are referenced, ignored `_site/`,
tracked `_freeze/`, and then renders the target post.

After rendering, run visual and final editorial checks before human review
using the project Copilot skills:

```text
blog-chart-review posts/drafts/YYYY-MM-DD-slug
blog-final-review posts/drafts/YYYY-MM-DD-slug
```

## Repository Hygiene

Check for orphan freeze entries, stale figure outputs, generated tracked files,
nested repositories, and invalid new post slugs:

```bash
python tools/audit_repository.py
```

Preview safe removal of local Quarto output and Python caches:

```bash
python tools/clean_local.py
python tools/clean_local.py --apply
```

The cleanup tool never removes `.venv`, `_freeze`, or post data.

## Publish a Post

1. Create and work on a local branch: `git checkout -b post/YYYY-MM-DD-slug`.
2. Remove `draft: true` and move the folder from `posts\drafts\YYYY-MM-DD-slug` to `posts\YYYY-MM-DD-slug`.
3. Run `blog-final-review` and ensure `stats\final_review_status.json` has `"status": "PASS"`.
4. Re-render so `_freeze/` is current: `quarto render posts/YYYY-MM-DD-slug/index.qmd --to html`
   (HTML preview is under `_site/`; do not commit `_site/`.)
5. Run the repository audit and local release gate on the published post path:

```bash
python tools/audit_repository.py
# Windows:
.\scripts\check_post.ps1 posts\YYYY-MM-DD-slug\index.qmd
# or bash:
bash scripts/local_release_gate.sh posts/YYYY-MM-DD-slug/index.qmd
```

6. Commit **only** the post folder and its freeze cache (leave unrelated dirty files alone).
7. Merge locally into `main` only after the gate passes (prevents failed deploys on `main`).
8. Push `main`; GitHub Actions publishes to `gh-pages`.
9. Verify with GitHub CLI when available:

```bash
gh run list --workflow=publish.yml --limit 3
gh run watch <run-id> --exit-status
```

Live URL pattern: `https://gilboa.blog/posts/YYYY-MM-DD-slug/`

```bash
git add posts/YYYY-MM-DD-slug _freeze/posts/YYYY-MM-DD-slug
git commit -m "Add post: post title"
git push origin main
```

## Publish site changes (About, navbar, SEO YAML)

Do not use the post freeze / `check_post` path. Work on `site/<name>`, wait for
sign-off, merge that branch into `main` locally, then `git push origin main`.
Watch `publish.yml` and confirm live URLs contain the new copy.

Canonical checklist: [.github/copilot-instructions.md](./.github/copilot-instructions.md)
(Publishing site changes). Grok: `blog-publish` site mode.

Chart house typeface is **Calibri** (see blog-viz-specialist and the post setup
template). Example one-off with curated benchmarks:
`posts/2026-07-25-kimi-k3-open-weights-sovereign-ai/`.
