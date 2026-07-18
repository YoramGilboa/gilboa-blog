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
   - title and framing;
   - three to five headline metrics;
   - two to five analytical sections;
   - conclusion and audience framing.
4. For each chart, list its `fig-` label, purpose, chart type, and required
   FRED IDs, BEA tables, or files.
5. Stop and obtain explicit chart-plan approval before chart implementation.

## 2. Data

1. Invoke `blog-data-validate` for every proposed external series.
2. Choose inline fetching only for simple, single-source work. Otherwise use:
   - `scripts/01_fetch_data.py`
   - `scripts/02_clean_data.py`
   - optional `scripts/03_visualizations.py`
   - `scripts/04_compute_stats.py`
3. Compute all prose and card values in `stats/summary_stats.json`.
4. Run the pipeline and verify required keys and date coverage.

Follow `.github/instructions/pipelines.instructions.md`.

## 3. Write

Follow `.github/instructions/posts.instructions.md`:

- complete frontmatter with `draft: true`;
- hidden setup, responsive metric cards, and reproducibility callout;
- approved analytical sections and charts;
- inline stats rather than hard-coded key values;
- interpretive captions and standalone `.figure-source` lines;
- conclusion, audience implications, limitations, methodology, and data date.

## 4. Review

1. Render the draft with the root `.venv`.
2. Invoke `blog-chart-review`.
3. Fix and rerender until desktop and 400px chart checks pass.
4. Invoke `blog-final-review`.
5. If prose changes affect charts, rerun both reviews. If only prose changes,
   rerun final review.
6. Require `stats/final_review_status.json` to contain `PASS`.

## 5. Human handoff and publication

Report the title, sections, chart count, key metrics, caveats, final-review
status, and rendered HTML path. Wait for explicit human approval.

After approval:

1. remove `draft: true`;
2. move source and freeze output to published paths;
3. rerender;
4. run the repository audit and local release gate;
5. commit on the post branch;
6. merge and push only when requested.
