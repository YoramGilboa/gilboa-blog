---
name: blog-seo-tags
description: >
  Set gilboa.blog YAML pagetitle, description, and categories for search,
  social, and listing SEO. Use after the draft exists and before chart/final
  review, or when the user asks to optimize tags, meta, title tag, or
  description.
argument-hint: "<post directory or index.qmd>"
---

# Blog SEO tags and meta

Set YAML `pagetitle:`, `description:`, and `categories:` on the target
`index.qmd`. Those become the HTML `<title>` / `og:title`, the dek plus meta /
Open Graph description, and the tags under the subtitle.

Wording and tag vocabulary live in `.github/instructions/posts.instructions.md`
(Frontmatter and Categories). Do not copy those lists here.

Keep this skill aligned with `~/.grok/skills/blog-seo-tags/SKILL.md`.

Do not change the H1 `title:`, body, charts, or dates. Use `description-meta:`
only when SEO text must differ from the visible dek.

## When to run

- **Pipeline:** after prose exists, before `blog-chart-review` /
  `blog-final-review`.
- **Standalone:** user names a post and asks to optimize tags or meta.
- **Review loop:** pagetitle copies the H1 or misses prints, description is
  jargon-first or too long, or categories are hyphenated, duplicated, missing
  a preferred tag, or stuffed with headlines.

Do not retag a live post during publish unless the human asked. After a live
YAML change, re-render freeze so `html.json` updates.

## Inputs

1. Target `index.qmd` frontmatter, H1 `title:`, description, and `##` headings
2. Official prints from `stats/summary_stats.json` (or the opening)
3. Frontmatter and Categories rules in `posts.instructions.md`
4. Published `categories:` under `posts/*/index.qmd` (skip `posts/drafts/`)

## pagetitle (HTML title)

Follow posts.instructions.md. Then count the characters.

- Month, year, release name, and the key print or prints
- 50-65 characters. Cap 70. If under 50, add a second print. If over 70, cut
  words, not the prints
- Must not be a copy of `title:`
- Compact range punctuation is allowed here (`3.75-4.00%`) so the string fits

## description (dek and meta)

Follow posts.instructions.md. Then count the characters.

- Lead with official prints and spell out "percent"
- About 150-160 characters. Do not drop prints to hit the cap
- This field is the listing card, the line under the H1, and the HTML meta
  description unless `description-meta:` is set

## categories (on-page tags)

- 3-6 tags. Default 4.
- Lowercase, space-separated (`labor market`, not `labor-market`).
- Reuse catalog tags. Mint a new string only if no preferred tag fits and a
  published post already uses it.
- Macro default: `economics`, topic tag(s), `federal reserve` when the Fed is
  in the thesis, `data visualization` last.
- One-offs may add `technology` or `markets` per posts.instructions.md.
- Drop near-duplicates (`visualization` with `data visualization`).

## Procedure

1. Collect current `pagetitle:`, `description:`, `categories:`, and the prints.
2. Draft `pagetitle:` and `description:`. Count both. Patch if they miss prints,
   copy the H1, or fall outside the length bands.
3. Map tags to the preferred list. Check the catalog only to reuse a string.
4. Patch only those YAML lines.
5. Write `generated/seo_tags.md` in the post folder (create `generated/` if
   needed). Do not let listings treat it as a post.

## Output

```markdown
# SEO tags

- **Post:** `posts/.../index.qmd`
- **pagetitle before/after (N chars):** ...
- **description before/after (N chars):** ...
- **categories before:** [...]
- **categories after:** [...]
- **Why:** one short paragraph
```

If a field was already correct, say so and leave it unchanged.

## Stop

If the post path is missing, ask which `index.qmd`. Then continue the parent
workflow (`blog-post-create` step 3b, or the named review).
