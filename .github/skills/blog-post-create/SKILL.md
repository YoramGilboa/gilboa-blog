---
name: blog-post-create
description: Orchestrate a new gilboa.blog data-visualization post from topic through pipeline, charts, prose, review, and human approval. Use when the user asks to create or write a post.
argument-hint: "<topic, optional date, and optional slug>"
---

# Blog post creation

Coordinate the full post workflow without bypassing approval gates.

Resolve the working post per `.github/copilot-instructions.md` **Working post**.
Do not review a live URL when `posts/drafts/` on the current `post/...` branch
is the work.

## 1. Architecture and chart plan

1. Create `posts/drafts/YYYY-MM-DD-slug/` from the template.
2. Create branch `post/YYYY-MM-DD-slug`.
3. Propose:
   - `title` (H1 finding), `description` (print dek), and `pagetitle` (Google
     tab) as three fields per posts.instructions.md;
   - framing (for non-macro one-offs: explicit "this blog is usually
     macro viz; today is a deliberate exception" frame);
   - three to five headline metrics;
   - two to five analytical sections with unnumbered `##` titles (one-offs may
     need more for multi-metric comparison);
   - conclusion with `### What it means for` audience lead-ins when multiple
     reader groups matter.
4. For each chart, list its `fig-` label, purpose, chart type, and required
   FRED IDs, BEA tables, curated files, or public benchmark sources.
5. Flag composite metrics that need peer comparison and underperformance
   subsections.
6. Stop and obtain explicit chart-plan approval before chart implementation
   unless the human already ordered full orchestration.

## 2. Data

1. Invoke `blog-data-validate` for every proposed FRED/BEA series.
2. For curated non-FRED posts, still use 01/02/04 and `data/raw/sources.json`
   (see pipelines instructions).
3. Choose inline fetching only for simple, single-source work. Otherwise use:
   - `scripts/01_fetch_data.py`
   - `scripts/02_clean_data.py`
   - optional `scripts/03_visualizations.py`
   - `scripts/04_compute_stats.py`
4. Compute all prose and card values in `stats/summary_stats.json`.
5. Format prose-facing calendar dates in stats as US month/day (e.g. `8/19`).
6. Run the pipeline and verify required keys and date coverage.

Follow `.github/instructions/pipelines.instructions.md`.

## 3. Write

Follow `.github/instructions/posts.instructions.md`:

- complete frontmatter with `draft: true`; set `title`, `description`, and
  `pagetitle` as three fields per posts.instructions.md;
- draft `categories:` from the preferred list in posts.instructions.md;
- reproducing callout says "this post", not "this draft";
- hidden setup, opening then callouts then metric cards;
- approved analytical sections and charts (unnumbered `##` titles);
- inline stats rather than hard-coded key values (every `{python}` backticked);
- dates from stats, US month/day; sparse bold; no single-item bullet lists;
- interpretive captions and standalone `.figure-source` lines;
- dual-meaning chart series labeled; no non-record scatter under frontiers;
- conclusion, audience implications, limitations, methodology, and data date.

## 3b. SEO tags and meta

Follow `.github/skills/blog-seo-tags/SKILL.md` on the draft `index.qmd` after
prose exists and before `blog-chart-review`. It may rewrite `pagetitle:`,
`description:`, and `categories:`. It does not rewrite the H1 `title:`.
Then continue.

## 4. Review

1. Run `python tools/validate_expressions.py <post-dir>` and fix any missing
   stats keys or unbackticked inline expressions before rendering.
2. Render the draft with the root `.venv`.
3. Run `python tools/validate_rendered_output.py <post-dir>` and fix any raw
   `{python}`, `NaN`, `undefined`, or `None%` in the rendered HTML.
4. Invoke `blog-chart-review`.
5. Fix and rerender until desktop and 400px chart checks pass.
6. Invoke `blog-final-review`.
7. If the review fails, fix with the named owner and rerun the review
   **without asking** which skill is next. If prose changes affect charts,
   rerun both reviews.
8. Require `stats/final_review_status.json` to contain `PASS`. Then stop and
   show the human.

## 5. Human handoff and publication

Report H1 `title`, dek `description`, `pagetitle`, tags, sections, chart
count, key metrics, caveats, final-review status, and rendered HTML path.
Wait for explicit human approval of that title block before publish.

After approval:

1. remove `draft: true`;
2. move source and freeze output to published paths;
3. rerender;
4. run the repository audit and local release gate;
5. commit on the post branch;
6. merge locally into `main`, then `git push origin main`, only when requested
   (see copilot-instructions Publishing requirements).
7. After the post is publication-ready (or once the user says it is live),
   offer to run `gilboa-blog-ai-visibility` to add the new URL to `/llms.txt`.
   Do not edit `robots.txt` or `llms.txt` inside this skill.

## After Publish Hook

When offering the handoff, include:

- Live post URL in sitemap form (`https://gilboa.blog/posts/YYYY-MM-DD-slug/`)
- One-line factual note for the llms.txt bullet (the print or the core claim)
- Reminder that crawl files live in the Quarto project root and need
  `quarto render` plus publish

If the user declines, stop. If they accept, follow `gilboa-blog-ai-visibility`.
