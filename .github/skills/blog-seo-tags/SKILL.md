---
name: blog-seo-tags
description: >
  Set gilboa.blog YAML categories (on-page tags) for listing and search SEO.
  Use after the draft exists and before chart/final review, or when the user
  asks to optimize tags or categories.
argument-hint: "<post directory or index.qmd>"
---

# Blog SEO tags

Set **only** `categories:` on the target `index.qmd`. Those values are the tags
under the subtitle. Vocabulary and formatting live in
`.github/instructions/posts.instructions.md` (Categories). Do not copy that
list here.

Keep this skill aligned with `~/.grok/skills/blog-seo-tags/SKILL.md`.

## When to run

- **Pipeline:** after prose exists, before `blog-chart-review` /
  `blog-final-review`.
- **Standalone:** user names a post and asks to optimize tags.
- **Review loop:** categories are hyphenated, duplicated, missing a preferred
  tag, or stuffed with headlines.

Do not retag a live post during publish unless the human asked.

## Inputs

1. Target `index.qmd` frontmatter, title, description, and `##` headings
2. Preferred tags in `posts.instructions.md`
3. Published `categories:` under `posts/*/index.qmd` (skip `posts/drafts/`)

## Rules

- 3–6 tags. Default 4.
- Lowercase, space-separated (`labor market`, not `labor-market`).
- Reuse catalog tags. Mint a new string only if no preferred tag fits and a
  published post already uses it.
- Macro default: `economics`, topic tag(s), `federal reserve` when the Fed is
  in the thesis, `data visualization` last.
- One-offs may add `technology` or `markets` per posts.instructions.md.
- Drop near-duplicates (`visualization` with `data visualization`).
- Do not change `title`, `pagetitle`, `description`, body, charts, or dates.

## Procedure

1. Read current `categories:` and the post topic from title + sections.
2. Map to the preferred list. Check the catalog only to reuse a string.
3. Patch only the `categories:` line.
4. Write `generated/seo_tags.md` in the post folder (create `generated/` if
   needed). Do not let listings treat it as a post.

## Output

```markdown
# SEO tags

- **Post:** `posts/.../index.qmd`
- **Before:** [...]
- **After:** [...]
- **Why:** one short paragraph
```

If tags were already correct, say so and leave YAML unchanged.

## Stop

If the post path is missing, ask which `index.qmd`. Then continue the parent
workflow (`blog-post-create` step 4, or the named review).
