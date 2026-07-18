---
applyTo: "posts/**/scripts/*.py"
---

# Post pipeline instructions

## Choose the simplest reproducible pattern

- Inline QMD fetching is suitable for a simple, single-source FRED post with
  minimal preprocessing.
- Use numbered scripts for multiple APIs/files, heavier transformations, or
  reusable processing.

The standard scripted layout is:

```text
scripts/
  01_fetch_data.py
  02_clean_data.py
  03_visualizations.py   # optional
  04_compute_stats.py
data/raw/
data/clean/
stats/summary_stats.json
```

## Pipeline rules

- Use explicit imports and type-safe, readable transformations.
- Read API keys from `FRED_API_KEY` and `BEA_API_KEY`; never commit secrets.
- Validate every new FRED series or BEA table before writing fetch logic.
- Save raw downloads under `data/raw/` and deterministic derived files under
  `data/clean/`.
- Compute all prose and card values in `04_compute_stats.py`.
- Do not hard-code release values. If a value is available only from a primary
  document, mark it `# MANUAL:` and include the source URL on the next line.
- Fail clearly on missing required data or malformed responses. Do not silently
  substitute success-shaped defaults.
- Keep time frequencies and date alignment explicit.
- Run scripts from the post directory in numeric order.

## Data sources

- FRED: `fredapi`, key in `FRED_API_KEY`,
  https://fred.stlouisfed.org/docs/api/api_key.html
- BEA NIPA: REST API, key in `BEA_API_KEY`,
  https://apps.bea.gov/api/signup/

Common BEA tables include `T10102`, `T10101`, `T20100`, and `T20301`. Confirm
table identity and freshness rather than relying on this short list.

## Data and dependency policy

- Add dependencies only to root `requirements.txt`.
- Never create a post-specific requirements file or environment.
- Commit data required to reproduce or render the post when CI cannot refetch
  it.
- Do not commit regenerable top-level single-series FRED caches matched by
  `posts/*/data/*.csv`.
- Always commit cleaned data, stats, images, scripts, and matching freeze output
  when the post depends on them.
