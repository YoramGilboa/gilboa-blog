---
applyTo: "posts/**/*.qmd"
---

# Post prose and chart instructions

## Frontmatter

New drafts use:

```yaml
---
title: "Post Title"
date: "YYYY-MM-DD"
author: Yoram Gilboa
categories: [economics, data visualization]
description: "One sentence for the listing and social preview."
image: images/preview-image.png
draft: true
toc: true
toc-location: right
code-fold: true
code-summary: "Show code"
---
```

- Remove `draft: true` only when publishing.
- Never add `subtitle:`. It duplicates the listing description.
- Categories are lowercase and space-separated, not hyphenated.
- Use `description-meta:` only when SEO text must differ from visible listing
  text.
- When changing `title` or `description`, set `pagetitle` to the same string as
  `title` unless the human wants a different browser tab title.
- Shared responsive and content styles belong in root `styles.css`, not inline
  `<style>` blocks.

## Scope of the blog

Default lane: US macro data visualization (CPI, labor, Fed/FOMC, PPI, BTOS) with
reproducible pipelines.

**Deliberate one-off posts** (tech, AI policy, markets structure, court data)
are allowed when the human asks or topic selection marks a high-signal moment.
For one-offs:

1. State in the opening that the blog is primarily data viz / reproducibility
   and that this post is an intentional exception.
2. Keep a data spine (curated public tables, independent benchmarks, or official
   series) and charts. Pure opinion without numbers is not a post.
3. Categories may include `technology` or `markets` alongside
   `data visualization` when appropriate.
4. Do not put architecture notes, editor reviews, or other `generated/*.md`
   where Quarto listings will treat them as posts. Keep factory artifacts under
   `generated/` only while drafting; strip before publish if they render.

Reference example: `posts/2026-07-25-kimi-k3-open-weights-sovereign-ai/`.

## Writing

- Begin with the key finding immediately after frontmatter. Do not add an
  Introduction heading.
- Tone: **adult engagement, plain vocabulary**. A careful high-school graduate
  should follow the argument; do not talk down. Define jargon once on first use.
- Do not use em dashes, en dashes, or a spaced hyphen as a dash. Break the
  sentence with a period or a comma, or restructure. Write ranges with "to".
- Use full URLs with descriptive link text. Never use "click here."
- Never hard-code key figures in prose. Read them from
  `stats/summary_stats.json` with inline Python.
- **Dates in prose:** US month/day order, **from stats**, never invented in
  the `.qmd`. Short forms are preferred (`8/19`, `8/19/26`). Leading zeros are
  not required. YAML frontmatter `date:` stays ISO `YYYY-MM-DD`.
- **Bold is sparse.** Prefer no decorative bold in body paragraphs. Use bold
  for audience lead-ins in the conclusion (see below). Do not blanket-bold every
  first-mention statistic unless the human asks for that house style on a
  specific post.
- Use `##` for sections and `###` for subsections. Never use `#` in the body.
- Section titles are unnumbered (`## Labor breadth`, not `## 1. Labor breadth`).
- Prefer two to five analytical sections and a linear narrative (one-offs may
  run longer when strategy or multi-metric comparison requires it).
- **Never use a bullet list for a single item.** Convert one-item lists to a
  sentence. Use bullets only for two or more parallel items.
- End with a conclusion, limitations when needed, methodology/data table, and
  an italicized data-currency note.

### Multi-metric and composite scores

When a post leans on a composite index or leaderboard (e.g. Intelligence Index):

1. Define what the metric measures in plain English.
2. Show peer comparison scores (not only the hero model).
3. Put the composite **in perspective**: where the subject underperforms on
   task-level tests, reliability, cost, or UX.
4. Prefer short subsections or labeled score blocks over a single dense bullet
   list of unrelated metrics.

### Inline Python hygiene

- Every inline expression must be fully backticked:
  `` `{python} stats['key']` `` or `` `{python} fmt(stats['key'])` ``.
- Never leave bare `{python} ...` in prose (breaks render; preflight fails).
- Data-currency line example:

```markdown
*Data current as of `{python} stats['data_current_as_of']`. `{python} stats['release_note']`*
```

## Reproducibility callout

Place a collapsed "Reproducing this analysis" callout after the opening. For a
scripted pipeline, list each numbered script and source. For inline fetching,
describe the hidden fetch and transform blocks and fallback behavior.

If data are estimated, approximate, third-party benchmarks, or a teaching
rubric, add a collapsed "Note on data" callout that distinguishes exact and
estimated values and links primary sources.

## Setup block

- The first code block is hidden with `#| echo: false`.
- Import explicitly; wildcard imports are prohibited.
- Load stats and cleaned data from paths relative to the post.
- Define one semantic `COLORS` mapping and reuse it.
- Configure matplotlib after any `sns.set_theme()` call.
- Define `fmt()`, `fmt_chg()`, and `fmt2()` when money or two-decimal values appear.
- House chart typeface is **Calibri** via `rcParams`.
- Use the root `.venv`; never add post-specific environments or requirements.

## Metric cards

- Use a responsive grid for three to five headline metrics.
- Pull every value from `stats/summary_stats.json`.
- Keep cards readable on narrow screens and include a short source/date line.
- Cards appear **after** the opening paragraphs and Reproducing / data callouts
  (not before the opening).

## Chart blocks

Every chart block includes:

```python
#| echo: true
#| label: fig-descriptive-name
#| fig-cap: "A full sentence that states what the chart shows and why it matters."
```

- Labels use `fig-` and kebab-case.
- Use hidden chunks only for setup or non-reader-facing data preparation.
- Treat the Quarto caption as the interpretation sentence. Do not repeat it
  inside the image.
- Put `Source:` in a standalone `.figure-source` block directly below the
  figure, not inside the image.
- End each chart block with `plt.tight_layout()`.
- Save one representative PNG under `images/` for the social preview.
- Size figures for the article column before considering desktop expansion.
- Standard figsize width is **8.0** inches (house viz kit).

## Chart style

- Hide top and right spines; no background grids.
- Use `%Y` ticks for multi-year charts and `%b\n%Y` for shorter windows.
- Prefer direct endpoint labels over legends when possible.
- A labeled line endpoint normally has a 40-point dot, white edge, and plain
  text immediately to its right.
- Extend the x-axis by at least 10 percent of the displayed date range when
  endpoint labels need room.
- Use manual offsets for fewer than four labels. Use `adjustText` only for four
  or more genuinely colliding labels.
- Give annotations a semi-transparent plot-background box and `zorder=5`.
- Compute bar-label padding from the data range. Put labels inside bars when
  outside labels would clip.
- For `twinx()`, disable the secondary grid, hide its top spine, and align tick
  counts across axes.
- Use light recession or area shading and subdued dashed reference lines.
- Avoid legends or annotations that obscure data. Prefer `loc="upper right"` or
  another free corner when a legend is required.

### Chart design lessons (required)

1. **Frontier / record lines.** If the series is a running maximum or size
   frontier, plot only the frontier and labeled record points. Do **not**
   scatter every non-record observation as gray/green dots below the line;
   readers read those as errors.
2. **Dual meanings.** When two quantities can be confused (e.g. MoE total
   parameters vs active parameters vs expert counts), state the mapping in
   prose and in the `fig-cap`. Label missing published quantities honestly
   rather than inventing them.
3. **Cost vs quality.** When comparing models or vendors, consider a cost-per-
   task (or similar) chart plus a cost-vs-score scatter or table when both
   dimensions matter for the decision.
4. **One idea per chart.** Keep captions as full sentences with the takeaway.

## Visual review checklist

Review every chart at desktop width and 400px:

1. label overlap;
2. label clipping;
3. legend occlusion;
4. annotation collision;
5. axis readability;
6. dual-axis grid alignment;
7. bar-label placement and contrast;
8. overall color contrast;
9. endpoint dots and label consistency;
10. data-dependent fragility if values move;
11. no stray non-record scatter under frontier lines;
12. dual-metric charts labeled so series meanings cannot be confused.

## Structure and closing sections

Preferred order:

1. hidden setup;
2. opening paragraph(s) (no `## Introduction`); one-offs may open with blog-scope
   framing then the finding;
3. reproducibility and optional data-note callouts;
4. metric cards;
5. analytical sections and charts;
6. conclusion with audience implications;
7. limitations when applicable;
8. methodology/data table;
9. references when applicable;
10. data-currency note.

Preferred multi-audience conclusion form:

```markdown
### What it means for

**Investors and executives.** ...

**Product and engineering leaders.** ...

**Policymakers.** ...
```

Macro posts may keep **For markets:** / **For the Fed:** lead-ins instead.

Use pipe tables for structured data and include a caption. Use Quarto footnotes
for technical definitions, acronyms, and legal citations.

## Policy and strategy sections

When a post discusses regulation or industrial policy (e.g. open weights):

- Prefer two sharp points over a large forced table of hypothetical cases.
- Include competitive-cost angles when relevant (e.g. domestic bans while
  foreign firms use cheaper open backends).
- Attribute institutional claims (white papers, CEOs) with links in Methodology.
