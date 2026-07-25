"""
Step 2 of 3: turn raw index levels into percent-change series.

Pipeline order (run from this post folder):
  1. python scripts/01_fetch_data.py   # downloads index levels
  2. python scripts/02_clean_data.py   <-- you are here
  3. python scripts/04_compute_stats.py

Input:  data/raw/fred_monthly.csv   (index *levels*, not rates)
Output: data/clean/main.csv         (levels + m/m + y/y + 3-month annualized)

Rate definitions used everywhere in this post
  - Month-over-month (m/m):
      100 * (value_t / value_{t-1} - 1)
  - Year-over-year (y/y):
      100 * (value_t / value_{t-12} - 1)
  - Three-month annualized (ann3):
      100 * ((value_t / value_{t-3}) ** (12/3) - 1)
      i.e. take the 3-month ratio, compound it to a 12-month pace.

Chart code in index.qmd only *plots* these columns. It does not recompute rates.
If you change a formula here, re-run 04_compute_stats.py and re-render the post.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"

# Same friendly names as in 01_fetch_data.py (column names in the raw CSV).
SERIES = [
    "ppi_final_demand",
    "ppi_final_demand_goods",
    "ppi_finished_goods",
    "ppi_final_demand_services",
    "ppi_energy",
    "ppi_foods",
    "ppi_goods_less_food_energy",
    "ppi_less_food_energy_trade",
    "ppi_trade_services",
    "cpi_headline",
    "cpi_core",
    "cpi_energy",
    "cpi_core_goods",
]


def annualized(series: pd.Series, months: int) -> pd.Series:
    """
    Compound a multi-month index ratio into an annualized percent rate.

    Example with months=3:
      if the index rose 1% over three months, the annualized rate is
      (1.01 ** 4 - 1) * 100, because there are four such quarters in a year.
    """
    return ((series / series.shift(months)) ** (12 / months) - 1) * 100


def main() -> None:
    raw = pd.read_csv(RAW_DIR / "fred_monthly.csv", index_col="date", parse_dates=True)

    # Same monthly normalization as the fetch step (defensive if CSV was edited).
    raw.index = raw.index.to_period("M").to_timestamp()
    raw = raw.groupby(raw.index).last().sort_index()

    clean = raw.copy()
    for column in SERIES:
        # fill_method=None avoids pandas quietly filling gaps before pct_change.
        # Missing months stay missing instead of inventing a flat path.
        clean[f"{column}_mom"] = raw[column].pct_change(fill_method=None) * 100
        clean[f"{column}_yoy"] = raw[column].pct_change(12, fill_method=None) * 100
        clean[f"{column}_ann3"] = annualized(raw[column], 3)

    clean.index.name = "date"
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    clean.to_csv(CLEAN_DIR / "main.csv")

    latest = clean[[f"{SERIES[0]}_yoy"]].dropna().index[-1]
    print(f"Wrote {CLEAN_DIR / 'main.csv'} through {latest.strftime('%Y-%m')}")


if __name__ == "__main__":
    main()
