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

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Create a Post

Copy the draft template to a dated slug folder:

```powershell
Copy-Item -Recurse posts\drafts\_template posts\drafts\YYYY-MM-DD-slug
```

Write the post in `posts\drafts\YYYY-MM-DD-slug\index.qmd`. Keep `draft: true`
until it is ready to publish.

## Check and Render a Post

Run the project preflight from the repository root:

```powershell
.\scripts\check_post.ps1 posts\drafts\YYYY-MM-DD-slug\index.qmd -AllowDraft
```

To run numbered pipeline scripts before rendering:

```powershell
.\scripts\check_post.ps1 posts\drafts\YYYY-MM-DD-slug\index.qmd -AllowDraft -RunPipeline
```

The preflight checks for stale template headings, `draft: true`, `plt.show()`,
wildcard imports, missing stats files when stats are referenced, ignored `_site/`,
tracked `_freeze/`, and then renders the target post.

## Publish a Post

1. Remove `draft: true` from the post frontmatter.
2. Move the folder from `posts\drafts\YYYY-MM-DD-slug` to `posts\YYYY-MM-DD-slug`.
3. Run preflight on the published path without `-AllowDraft`.
4. Commit the post folder and `_freeze/`.
5. Push `main`; GitHub Actions publishes to `gh-pages`.

```powershell
git add posts\YYYY-MM-DD-slug _freeze
git commit -m "Add post: post title"
git push
```
