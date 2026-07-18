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
- Shared responsive and content styles belong in root `styles.css`, not inline
  `<style>` blocks.

## Writing

- Begin with the key finding immediately after frontmatter. Do not add an
  Introduction heading.
- Use direct, sophisticated but accessible prose.
- Do not use em or en dashes in prose. Restructure or use spaced hyphens.
- Use full URLs with descriptive link text. Never use "click here."
- Never hard-code key figures in prose. Read them from
  `stats/summary_stats.json` with inline Python.
- Bold a key number on its first important mention.
- Use `##` for sections and `###` for subsections. Never use `#` in the body.
- Prefer two to five analytical sections and a linear narrative.
- End with a conclusion, limitations when needed, methodology/data table, and
  an italicized data-currency note.

## Reproducibility callout

Place a collapsed "Reproducing this analysis" callout after the opening. For a
scripted pipeline, list each numbered script and source. For inline fetching,
describe the hidden fetch and transform blocks and fallback behavior.

If data are estimated or approximate, add a collapsed "Note on data" callout
that distinguishes exact and estimated values and links primary sources.

## Setup block

- The first code block is hidden with `#| echo: false`.
- Import explicitly; wildcard imports are prohibited.
- Load stats and cleaned data from paths relative to the post.
- Define one semantic `COLORS` mapping and reuse it.
- Configure matplotlib after any `sns.set_theme()` call.
- Define `fmt()` and `fmt_chg()` helpers.
- Use the root `.venv`; never add post-specific environments or requirements.

## Metric cards

- Use a responsive grid for three to five headline metrics.
- Pull every value from `stats/summary_stats.json`.
- Keep cards readable on narrow screens and include a short source/date line.

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

## Chart style

- Hide top and right spines.
- Use `%Y` ticks for multi-year charts and `%b\n%Y` for shorter windows.
- Prefer direct endpoint labels over legends.
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
- Avoid legends or annotations that obscure data.

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
10. data-dependent fragility if values move.

## Structure and closing sections

A typical data post uses:

1. hidden setup;
2. metric cards;
3. opening paragraph;
4. reproducibility or data-note callout;
5. analytical sections and charts;
6. conclusion or "What this means";
7. limitations when applicable;
8. methodology/data table;
9. references when applicable;
10. data-currency note.

Use bold audience lead-ins where useful:

```markdown
**For households:** ...

**For investors:** ...

**For policymakers:** ...
```

Use pipe tables for structured data and include a caption. Use Quarto footnotes
for technical definitions, acronyms, and legal citations.
