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
- `.github/instructions/` - scoped post and pipeline guidance for Copilot
- `.github/skills/` - tracked blog creation and review skills
- `scripts/` - reusable project-level utilities

## Local Setup

```bash
source .venv/Scripts/activate
pip install -r requirements.txt
git config core.hooksPath .githooks
```

Start the local site on the standard review port:

```bash
quarto preview --port 4200 --no-browser
```

## Create a Post

Copy the draft template to a dated slug folder:

```bash
cp -r posts/drafts/_template posts/drafts/YYYY-MM-DD-slug
```

Write the post in `posts\drafts\YYYY-MM-DD-slug\index.qmd`. Keep `draft: true`
until it is ready to publish.

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
4. Run the repository audit and local release gate on the published post path:

```bash
python tools/audit_repository.py
bash scripts/local_release_gate.sh posts/YYYY-MM-DD-slug/index.qmd
```

5. Commit changes on the post branch.
6. Merge locally into `main` only after the gate passes (prevents failed deploys on `main`).
7. Push `main`; GitHub Actions publishes to `gh-pages`.

```bash
git add posts/YYYY-MM-DD-slug _freeze
git commit -m "Add post: post title"
git push
```
