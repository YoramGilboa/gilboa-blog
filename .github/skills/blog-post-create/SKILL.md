---
name: blog-post-create
description: Orchestrate a new gilboa.blog data-visualization post from topic through pipeline, charts, prose, review, and human approval. Use when the user asks to create or write a post.
argument-hint: "<topic, optional date, and optional slug>"
---

# Blog post creation

Coordinate the full post workflow without bypassing approval gates.

## 1. Architecture and chart plan

1. Create `posts/drafts/YYYY-MM-DD-slug/` from the template.
2. Create branch `post/YYYY-MM-DD-slug`.
3. Propose:
   - title and framing (for non-macro one-offs: explicit "this blog is usually
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

- complete frontmatter with `draft: true`; if title/description change later,
  keep `pagetitle` in sync with `title`;
- hidden setup, opening then callouts then metric cards;
- approved analytical sections and charts (unnumbered `##` titles);
- inline stats rather than hard-coded key values (every `{python}` backticked);
- dates from stats, US month/day; sparse bold; no single-item bullet lists;
- interpretive captions and standalone `.figure-source` lines;
- dual-meaning chart series labeled; no non-record scatter under frontiers;
- conclusion, audience implications, limitations, methodology, and data date.

## 4. Review

1. Render the draft with the root `.venv`.
2. Invoke `blog-chart-review`.
3. Fix and rerender until desktop and 400px chart checks pass.
4. Invoke `blog-final-review`.
5. If the review fails, fix with the named owner and rerun the review
   **without asking** which skill is next. If prose changes affect charts,
   rerun both reviews.
6. Require `stats/final_review_status.json` to contain `PASS`. Then stop and
   show the human.

## 5. Human handoff and publication

Report the title, sections, chart count, key metrics, caveats, final-review
status, and rendered HTML path. Wait for explicit human approval.

After approval:

1. remove `draft: true`;
2. move source and freeze output to published paths;
3. rerender;
4. run the repository audit and local release gate;
5. commit on the post branch;
6. merge locally into `main`, then `git push origin main`, only when requested
   (see copilot-instructions Publishing requirements).
