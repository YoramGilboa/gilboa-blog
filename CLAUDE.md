# gilboa.blog — Claude guidance

## Project overview

A Quarto-based data visualization blog hosted at **gilboa.blog** via GitHub Pages.
Posts are written in `.qmd` (Quarto Markdown) with embedded Python, rendered locally,
and published automatically when pushed to `main`.

**Stack:** Quarto · Python · matplotlib / seaborn · GitHub Actions

---

## Repository structure

```
gilboa-blog/
├── _quarto.yml                  ← site config (theme, navbar, footer)
├── index.qmd                    ← homepage / post listing
├── about.qmd                    ← about page
├── styles.css                   ← custom CSS
├── CNAME                        ← custom domain (gilboa.blog)
├── requirements.txt             ← all Python dependencies
├── .github/workflows/publish.yml
├── .githooks/pre-commit         ← runs lint_post.py on staged posts
├── .claude/commands/            ← blog-post-create, blog-chart-review, blog-data-validate, blog-final-review skills
├── tools/lint_post.py           ← deterministic post linter (pre-commit + CI gate)
├── scripts/check_post.ps1       ← per-post preflight: lint checks + render
├── _freeze/                     ← cached Python output — COMMIT THIS
├── posts/
│   ├── _metadata.yml            ← shared defaults for all posts
│   ├── YYYY-MM-DD-slug/         ← one folder per published post
│   │   ├── index.qmd
│   │   ├── data/                ← CSVs and other data files
│   │   ├── scripts/             ← pipeline scripts (optional)
│   │   └── stats/               ← pre-computed JSON stats (optional)
│   └── drafts/
│       ├── _template/index.qmd  ← copy this to start a new post
│       └── YYYY-MM-DD-slug/     ← work in progress (draft: true)
└── gilboa-blog_old/             ← archived backup — do not touch
```

### Key rules

- **One git repo.** Everything lives here. Do not create repos inside post folders.
- **One `.venv`.** Create it once at the repo root. Never create a `.venv` inside a post folder.
- **`_freeze/` is committed.** This is what allows GitHub Actions to publish without re-running Python.
- **`_site/` is gitignored.** It is generated output; never commit it.
- **Commit the data a post needs to render; do not commit regenerable caches.**
  Posts render in CI from the committed `_freeze/` cache, so Python does not
  re-run there. Commit cleaned/derived data a post reads at render time when it
  cannot be re-fetched in CI (e.g. the BTOS `.xlsx` source files, or
  `data/clean/*.csv`). Do **not** commit the large regenerable single-series
  FRED cache that jobs posts produce - those top-level `posts/*/data/*.csv`
  files are gitignored and rebuilt by `scripts/download_fred_data.py`. Always
  commit `index.qmd`, `scripts/`, `stats/`, `images/`, and the matching
  `_freeze/` entry.

---

## Workflow

### One-time setup (after cloning)

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# PowerShell instead: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
git config core.hooksPath .githooks   # activate the lint pre-commit hook
```

### Every session

```bash
source .venv/Scripts/activate
quarto preview                      # live-reloading local preview
```

### Creating a new post

1. Copy `posts/drafts/_template/` to `posts/drafts/YYYY-MM-DD-slug/`
2. **Chart plan:** Before writing any chart code, list each planned chart with
   a one-line description, the data series required, and the chart type (line,
   bar, multi-panel, etc.). Get approval on this list before coding. Changes to
   chart specifications after code is written are the single largest source of
   iteration cost.
3. Write the post with `draft: true` in the frontmatter
4. `quarto preview` re-renders on save; Python output is cached to `_freeze/` automatically
5. When ready to publish: remove `draft: true`, move folder to `posts/YYYY-MM-DD-slug/`
6. Commit and push:

```bash
git add posts/YYYY-MM-DD-slug/ _freeze/
git commit -m "Add post: your post title"
git push
```

GitHub Actions deploys to gilboa.blog within ~2 minutes.

---

## Guardrails and verification commands

Three layers enforce the rules in this file mechanically. All are driven by
`tools/lint_post.py` (stdlib only), which checks **form, not truth** - it
catches a stray `subtitle:` or an em dash, but cannot judge chart overlap
(use `/blog-chart-review`) or whether a number is correct.

```bash
python tools/lint_post.py posts/SLUG/index.qmd   # one post (or a post dir)
python tools/lint_post.py --staged               # what the pre-commit hook runs
python tools/lint_post.py --all                  # every published post (what CI runs)
```

Exit code 0 means no ERRORs (WARNs print but do not block); 1 blocks the
commit / fails the deploy.

1. **Pre-commit hook** (`.githooks/pre-commit`) - lints staged published
   posts. Requires one-time activation: `git config core.hooksPath .githooks`.
   Bypass only in an emergency with `git commit --no-verify`.
2. **CI gate** (`.github/workflows/publish.yml`) - runs `lint_post.py --all`
   before rendering; the backstop that cannot be bypassed. CI then renders
   from the committed `_freeze/` cache and publishes to the `gh-pages` branch.
   `FRED_API_KEY` is available as a repo secret in CI.
3. **Per-post preflight** (`scripts/check_post.ps1`) - PowerShell wrapper
   that checks stale template headings, `draft: true`, `plt.show()`, wildcard
   imports, missing stats files, then renders the target post:

```powershell
.\scripts\check_post.ps1 posts\drafts\YYYY-MM-DD-slug\index.qmd -AllowDraft
# -RunPipeline runs the numbered scripts/ first; -SkipRender skips the render
```

The `/blog-post-create`, `/blog-chart-review`, `/blog-data-validate`, and
`/blog-final-review` skills live in `.claude/commands/`. `BLOG_AUTOMATION.md` and
`BLOG_DEV_SETUP.md` describe a superseded 5-role automation experiment;
those four skills are the active replacements.

---

## Writing style rules

These rules apply to all prose in every post:

- **No em dashes or en dashes.** Do not use `---` (Quarto em dash) or `--` (en dash). Use spaced hyphens ` - `, commas, colons, periods, or restructured sentences instead.
- **No wildcard imports.** Never use `from pandas import *` or similar.
- **Full URLs for all links.** Never use "click here" as link text.
- **Never hard-code numbers in text.** Use inline `{python} fmt(stats['key'])` expressions. Wrap key numbers in `**bold**` on first mention.

---

## Post formatting

### YAML frontmatter

Every post must include:

```yaml
---
title: "Post Title"
date: "YYYY-MM-DD"
author: Yoram Gilboa
categories: [economics, data visualization]
description: "One sentence summary for social previews and search engines."
image: images/preview-image-name.png
draft: true                    # remove when publishing
toc: true
toc-location: right
code-fold: true
code-summary: "Show code"
---
```

`categories` should use lowercase, space-separated labels (no hyphens).
Existing categories:
`economics`, `data analysis`, `inflation`, `energy`, `federal reserve`, `fomc`,
`interest rates`, `labor market`, `markets`, `supreme court`, `data visualization`,
`visualization`, `law`, `politics`, `meta`, `python`, `insurance`, `actuarial`

**Do not add a `subtitle:` field.** On the homepage listing, a `subtitle`
renders *in addition to* the auto-extracted excerpt (or the `description`),
producing a doubled-up description block on the listing card that does not
match the other posts. Put the one-line summary in `description:` only. If you
need an SEO/social description that differs from the listing text, use
`description-meta:` (which sets the meta tags without affecting the visible
listing card) - but verify the listing card afterward (see publishing checklist).

---

### Responsive title style

The responsive `.quarto-title-meta` grid CSS and shared content styles (table
formatting, callout radius, heading spacing) live in `styles.css` at the repo
root. This file is loaded site-wide via `_quarto.yml`. **Do not add inline
`<style>` blocks in posts** - all shared styles belong in `styles.css`.

---

### Opening paragraph

Begin immediately after the frontmatter closing `---`, no `## Introduction`
heading at the top. Lead with the key finding or framing question. One tight
paragraph, no preamble.

---

### Reproducing this analysis callout

Include this immediately after the opening paragraph when the post uses a data pipeline:

```markdown
::: {.callout-note collapse="true"}
## Reproducing this analysis

The Python code used to generate each chart is included in this post. Click on any
code block to see the full implementation. The complete data pipeline includes:

- `01_fetch_data.py` - Fetches data from [source]
- `02_clean_data.py` - Cleans and computes derived series
- `03_visualizations.py` - Generates all charts
- `04_compute_stats.py` - Computes summary statistics

All data sourced from [Source Name](url).
:::
```

For posts with estimated or approximate data, use a data-caveat callout instead:

```markdown
::: {.callout-note collapse="true"}
## Note on data

[Explain the source, what is estimated vs. exact, and where to find primary sources.]
:::
```

---

### Setup code block

The first code block in every post is a hidden setup block — it loads data,
sets the color palette, and configures matplotlib. Always `#| echo: false`.

```python
#| echo: false

import json
import warnings
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from adjustText import adjust_text
from IPython.display import HTML

warnings.filterwarnings("ignore", category=UserWarning)

POST_DIR = Path(".").resolve()
DATA_DIR = POST_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
IMG_DIR = POST_DIR / "images"
STATS_DIR = POST_DIR / "stats"
for folder in [RAW_DIR, CLEAN_DIR, IMG_DIR, STATS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Load pre-computed statistics
with open(STATS_DIR / "summary_stats.json", encoding="utf-8") as f:
    stats = json.load(f)

# Load cleaned data
df = pd.read_csv(CLEAN_DIR / "main.csv", index_col=0, parse_dates=True)

# Tufte-inspired color palette
COLORS = {
    "primary":    "#2e5984",
    "accent":     "#8b0000",
    "secondary":  "#6b8e6b",
    "neutral":    "#4a4a4a",
    "light":      "#b0b0b0",
    "warning":    "#cc7722",
    "fed_target": "#cc0000",
    "recession":  "#888888",
}

plt.rcParams.update({
    "font.family":        "serif",
    "font.size":          10,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          False,
    "figure.facecolor":   "white",
    "axes.facecolor":     "#fafafa",
    "axes.linewidth":     0.5,
})

def fmt(n):
    """Format numbers for inline display."""
    if isinstance(n, float):
        return f"{n:.1f}"
    return f"{n:,}"

def fmt_chg(n):
    """Format signed change values with + prefix."""
    if isinstance(n, float):
        return f"{n:+.1f}"
    return f"{n:+,}"
```

Keep this palette consistent across all charts in a post. Add topic-specific
color keys as needed (e.g., `"soft"` for shading), but always extend `COLORS`
rather than introducing one-off hex values mid-post.

Every chart block should end with `plt.tight_layout()` and optionally
`fig.savefig(IMG_DIR / "chart-name.png", dpi=150, bbox_inches="tight")`
for social preview images. Set the `image:` frontmatter field to one of
these saved PNGs.

---

### Key metrics cards

Use an HTML grid immediately after the setup block when there are 3-5 headline
numbers to surface. Always pull values from `stats/summary_stats.json`:

```python
#| echo: false

html = f"""
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 1rem; margin: 1.5rem 0;">
  <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
              padding: 1.25rem; text-align: center;">
    <div style="font-size: 1.75rem; font-weight: 700; color: #2e5984;">{stats['key_value']}%</div>
    <div style="font-size: 0.8rem; color: #64748b;">Label</div>
  </div>
</div>
<p style="font-size: 0.75rem; color: #94a3b8; text-align: center; margin-top: -0.5rem;">
  Data as of {stats['latest_month']} | Source: [Source Name]
</p>
"""
HTML(html)
```

---

### Chart code blocks

Every chart block must have a label and figure caption:

```python
#| echo: true
#| label: fig-descriptive-name
#| fig-cap: "One sentence describing what the chart shows and what to notice."
```

- `#| echo: true` for charts (readers can expand the code)
- `#| echo: false` for setup and data-wrangling blocks only
- Labels use `fig-` prefix and kebab-case: `fig-headline`, `fig-shelter-detail`
- Figure captions are full sentences. They describe the chart AND call out the key takeaway.
- Treat `#| fig-cap:` as the chart's interpretation sentence. Do not repeat that same interpretation inside the plotted image with `fig.text()` or `ax.text()`.
- Put `Source:` on its own line directly below the rendered figure in the post body, not inside the image. Use the shared `.figure-source` style from `styles.css` rather than inline styling.
- If a line chart marks the latest point with an endpoint dot, label that dot by default unless doing so would create a worse overlap problem than the unlabeled point.
- Size charts for the article column first. Prefer figure widths that render near column width so the browser does not aggressively shrink the PNG and make chart typography look smaller than intended.

---

### Chart style standards

These rules apply to every chart:

**Axes:**
- Remove top and right spines (handled by `rcParams`, but verify per chart)
- Use `plt.tight_layout()` at the end of every chart block
- Format date axes with `mdates.DateFormatter('%Y')` for multi-year series,
  `mdates.DateFormatter('%b\n%Y')` for shorter windows

**Labels:**
- Use direct end-of-line labels instead of legends where possible
- If a legend is needed, place it `loc='upper right'` with `fontsize=8`
- Annotate key points (peaks, current value) with `ax.annotate()` and arrows
- Avoid mixing multiple caption systems. The chart should have one figure caption, one source line, and then only data labels or annotations that are truly part of the visual.

**Shading:**
- Use `ax.axvspan()` for recession bands with `alpha=0.08, color='#888888'`
- Use `ax.fill_between()` for area under a line with `alpha=0.1`

**Reference lines:**
- Use `ax.axhline()` with `linestyle='--', linewidth=1, alpha=0.5` for targets/thresholds

---

### Chart quality: preventing overlaps

Visual overlap is the most common chart defect. These rules are mandatory.

**End-of-line labels (the #1 overlap source):**

The default pattern is a plain text label placed immediately to the right of an
endpoint dot. No connector lines, no `arrowprops`. This is the settled style
across all gilboa.blog charts:

```python
# 1. Endpoint dot on the last data point
ax.scatter(series.index[-1], series.iloc[-1],
           s=40, color=color, zorder=5, edgecolors="white", linewidth=0.8)

# 2. Value label just to the right of the dot
last_val = series.iloc[-1]
ax.text(series.index[-1], last_val, f"  {last_val:+.1f}%",
        fontsize=9, color=color, fontweight="bold", va="center")

# 3. Extend x-axis to make room for labels
date_range = series.index[-1] - series.index[0]
ax.set_xlim(right=series.index[-1] + date_range * 0.12)
```

**When to use adjustText (4+ overlapping labels only):**

If a chart has four or more end-of-line labels whose values are close enough
to overlap, use `adjustText` for automatic collision avoidance. Do not use it
for fewer labels - manual positioning is more predictable and avoids silent
repositioning bugs:

```python
from adjustText import adjust_text

texts = []
for label, col, color in series_list:
    last_val = df[col].dropna().iloc[-1]
    last_date = df[col].dropna().index[-1]
    t = ax.text(last_date, last_val, f"  {label}",
                fontsize=9, color=color, va="center", fontweight="bold")
    texts.append(t)

adjust_text(texts, ax=ax, only_move={"text": "y"},
            arrowprops=dict(arrowstyle="-", color="#4a4a4a", lw=1.0))
```

**Annotation placement:**

- Always add a semi-transparent background to annotations over data:
  `bbox=dict(facecolor="#fafafa", edgecolor="none", pad=1.5, alpha=0.85)`
- Use `zorder=5` on annotation text so it renders above lines (`zorder=2`)
  and fills (`zorder=1`)
- When placing multiple annotations, check that they do not share the same
  approximate y-position. If they do, stagger `xytext` offsets vertically.

**Bar chart value labels:**

- Compute padding proportionally: `xpad = data_range * 0.04`, not a fixed constant
- For horizontal bars, flip labels inside when they approach the axis limit:
  ```python
  near_edge = abs(value) >= 0.85 * max_abs_value
  if near_edge:
      ax.text(value - xpad, i, txt, ha="right", color="white")
  else:
      ax.text(value + xpad, i, txt, ha="left", color="#334155")
  ```
- For vertical bars, check that `value + offset < ylim_max` before placing
  above; place inside the bar if it would clip.

**Dual-axis (twinx) charts:**

Always apply these three steps when using `ax.twinx()`:

```python
ax2 = ax.twinx()
ax2.grid(False)                         # 1. disable secondary grid
ax2.spines["top"].set_visible(False)    # 2. clean top spine
# 3. synchronize tick count so grids align:
ax.set_yticks(np.linspace(ax.get_ylim()[0], ax.get_ylim()[1], 6))
ax2.set_yticks(np.linspace(ax2.get_ylim()[0], ax2.get_ylim()[1], 6))
```

**Axis margins for labels:**

- Extend `xlim` at least 10% past the last data point when using
  end-of-line labels (not a fixed number of days)
- Use `ax.margins(y=0.1)` or manually pad `ylim` to prevent top/bottom clipping
- For the right edge: `ax.set_xlim(right=last_date + (last_date - first_date) * 0.1)`

**Seaborn interaction:**

If using `seaborn`, call `sns.set_theme()` **before** `plt.rcParams.update()`
so that rcParams overrides take precedence. Never let seaborn re-enable grids
after the setup block.

---

### Chart review checklist

Run this checklist on every chart before finalizing a post. Use `quarto preview`
and visually inspect each rendered chart:

1. **Label overlap** - Do any end-of-line labels touch or overlap each other?
2. **Label clipping** - Are any labels cut off at the axes boundary?
3. **Legend occlusion** - Does the legend cover any data points or trend lines?
4. **Annotation collision** - Do annotation boxes or arrows overlap each other
   or overlap data?
5. **Axis readability** - Are tick labels readable? Do date labels overlap?
6. **Dual-axis grids** - On twinx charts, is only one grid visible?
7. **Bar labels** - Are value labels inside the bars when they approach the axis
   limit? Is text color readable against the bar color?
8. **Color contrast** - Are all text labels readable against their background?
   Light text on light bars? Dark text on dark fills?
9. **Mobile width** - At 400px viewport width, do charts remain legible?
10. **Data-dependent fragility** - If the data values shift by 20%, would any
    labels collide? Test by mentally moving values closer together.

---

### Inline Python values in text

Use inline expressions to pull live values from `stats` into prose.
Never hard-code numbers in text:

```markdown
Headline CPI fell to **`{python} fmt(stats['headline_yoy'])`%** in
`{python} stats['latest_month']`, down from `{python} fmt(stats['prev_headline_yoy'])`%.
```

Wrap key numbers in `**bold**` on first mention in a section.

---

### Callout types

| Type | Use case |
|---|---|
| `.callout-note collapse="true"` | Methodology notes, data caveats, "Reproducing this analysis" |
| `.callout-warning` | Caveats the reader must see before interpreting a chart |
| `.callout-tip` | Optional context or further reading |

Always use `collapse="true"` for methodology/data notes so they don't interrupt reading flow.

---

### Footnotes

Use Quarto footnotes for technical terms, acronyms, or legal citations:

```markdown
IEEPA^[IEEPA: the International Emergency Economic Powers Act, a 1977 federal law
(50 U.S.C. §§ 1701-1708) that grants the President broad authority to regulate
commerce during national emergencies.]
```

---

### Tables

Use pipe tables for structured data. Add a caption line below:

```markdown
| Column A | Column B | Column C |
|---|---|---|
| Value | Value | Value |

: Table caption explaining what the reader should take away.
```

For data-source attribution, use a table with columns: Series, Description, Source.

---

### Sections and headings

- `##` for major sections
- `###` for subsections within a major section
- Never use `#` (conflicts with the post title)
- Numbered sections (`## 1. Vote Breakdown`) for posts with a clear analytical sequence
- Unnumbered sections for narrative posts

Standard section order for data posts:
1. Style block (responsive title CSS)
2. Setup code block (hidden, `#| echo: false`)
3. Key Metrics cards (hidden, `#| echo: false`)
4. Opening paragraph (no heading)
5. Reproducing this analysis / Note on data (callout)
6. Analytical sections (2-5 charts with numbered headings, e.g., `## 1. Title`)
7. Conclusion / What It Means
8. Methodology & Data (table)
9. References (if applicable)

End with a horizontal rule and an italicized data-currency note:

```markdown
---

*Data current as of `{python} stats['data_current_as_of']`.*
```

---

### Conclusion / What It Means

Structure the conclusion with **bold lead-in labels** for each stakeholder or implication:

```markdown
**For [audience]:** [implication in 2-3 sentences]

**For [audience]:** [implication in 2-3 sentences]
```

---

### Limitations section

Include a `### Limitations` subsection in the conclusion when data is estimated,
approximate, or subject to methodological caveats. Use a bullet list.

---

## Python pipeline conventions

When a post requires fetching or processing external data, organize scripts as:

```
posts/YYYY-MM-DD-slug/scripts/
├── 01_fetch_data.py      ← download raw data from FRED and BEA NIPA API
├── 02_clean_data.py      ← clean, compute derived series, output to data/clean/
├── 03_visualizations.py  ← (optional) standalone chart exports
└── 04_compute_stats.py   ← compute summary_stats.json used in the post
```

Output goes to:
- `data/clean/*.csv` — cleaned data read by the `.qmd`
- `stats/summary_stats.json` — pre-computed numbers for inline values and cards

Run scripts from the post folder:
```bash
cd posts/YYYY-MM-DD-slug
python scripts/01_fetch_data.py
python scripts/02_clean_data.py
python scripts/04_compute_stats.py
```

Then render:
```bash
quarto render posts/YYYY-MM-DD-slug/index.qmd
```

### Data sources

**FRED (Federal Reserve Economic Data):**
- API key: `FRED_API_KEY` environment variable
- Python package: `fredapi` (in requirements.txt)
- Registration: https://fred.stlouisfed.org/docs/api/api_key.html

**BEA NIPA (Bureau of Economic Analysis):**
- API key: `BEA_API_KEY` environment variable
- Access: Direct REST API (`https://apps.bea.gov/api/data/`)
- Registration: https://apps.bea.gov/api/signup/
- Common tables: `T10102` (contributions to GDP growth), `T10101` (GDP percent
  change), `T20100` (personal income), `T20301` (PCE by category)

**Rule: No hardcoded release values.** All statistics in `04_compute_stats.py`
must be computed from fetched data in `data/raw/` or `data/clean/`. If a value
cannot be fetched programmatically (e.g., it exists only in a press release
PDF), document it with a `# MANUAL:` comment and the source URL. Run
`/blog-data-validate` before writing fetch scripts to confirm all series IDs
are valid.

---

## Dependencies

All packages go in `requirements.txt` at the repo root. Do not add post-specific
`requirements.txt` files. If a new post needs a new package (e.g. `networkx`,
`fredapi`), add it to the root `requirements.txt` and commit.

```bash
pip install new-package
pip freeze | grep new-package >> requirements.txt
```

---

## Git workflow

New posts are developed on a local branch and merged to `main` before pushing:

```bash
# Start a new post
git checkout -b post/YYYY-MM-DD-slug

# ... write the post, render, commit ...

# When ready to publish
git checkout main
git merge post/YYYY-MM-DD-slug
git push origin main
# GitHub Actions deploys to gilboa.blog within ~2 minutes
```

Branch naming convention: `post/YYYY-MM-DD-slug` (matches the post folder name).

---

## Publishing checklist

Before merging to `main` and pushing:

- [ ] **`python tools/lint_post.py <post-dir>` passes with no errors.** This is
      the deterministic guardrail (also run by the pre-commit hook and the CI
      gate). It enforces the frontmatter, prose-style, and `# MANUAL:`-source
      rules mechanically so they do not depend on memory. It checks form, not
      truth - it cannot judge chart overlap (use `/blog-chart-review`) or
      whether a value is correct.
- [ ] All inline `{python}` values render correctly (`quarto preview`)
- [ ] All charts display without errors
- [ ] All charts pass `/blog-chart-review` (no label overlaps, no clipping, readable at 400px)
- [ ] Post passes `/blog-final-review` (accuracy, flow, and consistency)
- [ ] `stats/final_review_status.json` reviewed; resolve any non-PASS warning before publishing
- [ ] **Homepage listing card checked**, not just the post page. View the post in
      the `index.qmd` listing and confirm the card shows a single, clean
      description line (title → categories → one description → date/author).
      A doubled-up description usually means a stray `subtitle:` field (see the
      YAML frontmatter rules).
- [ ] Figure captions are complete sentences
- [ ] Figure caption, source line, and any endpoint labels follow the shared chart presentation pattern
- [ ] No duplicate chart interpretation text appears both in the Quarto caption and inside the image
- [ ] The "Reproducing this analysis" callout accurately describes the pipeline
- [ ] `stats/summary_stats.json` is up to date
- [ ] **No unverified placeholder values shipping.** Grep the post and
      `04_compute_stats.py` for `# MANUAL:`, `placeholder`, and `TODO`. Any
      `# MANUAL:` value (e.g. a consensus estimate that cannot be fetched from
      FRED) must be confirmed against its primary source before publishing.
- [ ] Data currency note at the bottom is accurate
- [ ] `_freeze/` reflects the latest render (run `quarto render` if unsure)
- [ ] Rendered HTML checked for raw `{python}` leaks, stale duplicate figure outputs in `_freeze`, and oversized figures that are being visibly downscaled by the browser
- [ ] Post folder is moved out of `drafts/` into `posts/`
- [ ] Social preview image saved to `images/` and referenced in `image:` frontmatter
- [ ] All FRED/BEA series IDs validated via `/blog-data-validate`
