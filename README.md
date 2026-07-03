# Gilboa Blog

Quarto-based data visualization blog published at [gilboa.blog](https://gilboa.blog).
This directory is the canonical Git repository for the site.

## Repository Layout

- `_quarto.yml` - site configuration
- `posts/` - published posts
- `posts/drafts/` - draft posts
- `posts/drafts/_template/` - starting point for new posts
- `_freeze/` - committed Quarto execution cache used by publishing
- `_site/` - generated local output, ignored by Git
- `scripts/` - reusable project-level utilities

## Local Setup

```bash
source .venv/Scripts/activate
pip install -r requirements.txt
git config core.hooksPath .githooks
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

To run numbered pipeline scripts before rendering:

```bash
bash scripts/check_post.sh posts/drafts/YYYY-MM-DD-slug/index.qmd --allow-draft --run-pipeline
```

The preflight checks for stale template headings, `draft: true`, `plt.show()`,
wildcard imports, missing stats files when stats are referenced, ignored `_site/`,
tracked `_freeze/`, and then renders the target post.

After rendering, run visual and final editorial AI checks before human review:

```text
/blog-chart-review posts/drafts/YYYY-MM-DD-slug
/blog-final-review posts/drafts/YYYY-MM-DD-slug
```

## Publish a Post

1. Create and work on a local branch: `git checkout -b post/YYYY-MM-DD-slug`.
2. Remove `draft: true` and move the folder from `posts\drafts\YYYY-MM-DD-slug` to `posts\YYYY-MM-DD-slug`.
3. Run `/blog-final-review` and ensure `stats\final_review_status.json` has `"status": "PASS"`.
4. Run the local release gate on the published post path:

```bash
bash scripts/local_release_gate.sh posts/YYYY-MM-DD-slug/index.qmd
```

5. Commit changes on the post branch.
6. Merge locally into `main` only after the gate passes.
7. Push `main`; GitHub Actions publishes to `gh-pages`.

```bash
git add posts/YYYY-MM-DD-slug _freeze
git commit -m "Add post: post title"
git push
```
