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

---

## Workflow

### One-time setup (after cloning)

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
pip install -r requirements.txt
```

### Every session

```bash
source .venv/Scripts/activate
quarto preview                      # live-reloading local preview
```

### Creating a new post

1. Copy `posts/drafts/_template/` to `posts/drafts/YYYY-MM-DD-slug/`
2. Write the post with `draft: true` in the frontmatter
3. `quarto preview` re-renders on save; Python output is cached to `_freeze/` automatically
4. When ready to publish: remove `draft: true`, move folder to `posts/YYYY-MM-DD-slug/`
5. Commit and push:

```bash
git add posts/YYYY-MM-DD-slug/ _freeze/
git commit -m "Add post: your post title"
git push
```

GitHub Actions deploys to gilboa.blog within ~2 minutes.

---

## Writing style rules

These rules apply to all prose in every post:

- **No em dashes or en dashes.** Do not use `---` (Quarto em dash) or `--` (en dash). Use spaced hyphens ` - `, commas, colons, periods, or restructured sentences instead.
- **No wildcard imports.** Never use `from pandas import *` or similar.
- **No `plt.show()` in Quarto.** Quarto handles figure display automatically.
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
categories: [economics, data visualization]
draft: true                    # remove when publishing
toc: true
toc-location: right
code-fold: true
code-summary: "Show code"
---
```

`categories` should use lowercase, consistent labels. Existing categories:
`economics`, `data analysis`, `inflation`, `supreme court`, `data visualization`,
`law`, `politics`, `meta`, `python`, `visualization`, `insurance`, `actuarial`

---

### Opening paragraph

Begin immediately after the frontmatter, no `## Introduction` heading at the top.
Lead with the key finding or framing question. One tight paragraph, no preamble.

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
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from IPython.display import HTML

# Load pre-computed statistics
with open("stats/summary_stats.json") as f:
    stats = json.load(f)

# Load cleaned data
df = pd.read_csv("data/clean/main.csv", index_col=0, parse_dates=True)

# Tufte-inspired color palette
COLORS = {
    'primary':   '#2e5984',
    'accent':    '#8b0000',
    'secondary': '#6b8e6b',
    'neutral':   '#4a4a4a',
    'light':     '#b0b0b0',
    'fed_target':'#cc0000',
}

plt.rcParams.update({
    'font.family':        'serif',
    'font.size':          10,
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'axes.grid':          False,
    'figure.facecolor':   'white',
    'axes.facecolor':     '#fafafa',
    'axes.linewidth':     0.5,
})

def fmt(n):
    """Format numbers for inline display."""
    if isinstance(n, float):
        return f"{n:.1f}"
    return f"{n:,}"
```

Keep this palette consistent across all charts in a post. Do not introduce
one-off colors mid-post.

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

**Shading:**
- Use `ax.axvspan()` for recession bands with `alpha=0.08, color='#888888'`
- Use `ax.fill_between()` for area under a line with `alpha=0.1`

**Reference lines:**
- Use `ax.axhline()` with `linestyle='--', linewidth=1, alpha=0.5` for targets/thresholds

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
1. Opening paragraph (no heading)
2. Reproducing this analysis (callout)
3. Key Metrics (cards)
4. Analytical sections (2-5 charts with prose)
5. Conclusion / What It Means
6. Methodology & Data (table)
7. References (if applicable)

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
├── 01_fetch_data.py      ← download raw data from APIs / BLS / FRED / etc.
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

## Publishing checklist

Before removing `draft: true` and pushing:

- [ ] All inline `{python}` values render correctly (`quarto preview`)
- [ ] All charts display without errors
- [ ] Figure captions are complete sentences
- [ ] The "Reproducing this analysis" callout accurately describes the pipeline
- [ ] `stats/summary_stats.json` is up to date
- [ ] Data currency note at the bottom is accurate
- [ ] `_freeze/` reflects the latest render (run `quarto render` if unsure)
- [ ] Post folder is moved out of `drafts/` into `posts/`
