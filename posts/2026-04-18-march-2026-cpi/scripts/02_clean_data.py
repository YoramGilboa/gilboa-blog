"""
02_clean_data.py
----------------
Convert raw FRED CPI index levels into the trend table used by the post.

Outputs:
    data/clean/cpi_trends.csv

The output keeps the original index levels and adds:
    *_yoy columns: year-over-year percent changes
    *_mom columns: month-over-month percent changes

Run from the post folder after 01_fetch_data.py:
    python scripts/02_clean_data.py
"""

import os

import pandas as pd


IN_PATH = "data/raw/fred_cpi_raw.csv"
OUT_PATH = "data/clean/cpi_trends.csv"


def main():
    # parse_dates converts the CSV date column into pandas datetime values so
    # the result can be filtered and plotted cleanly by month.
    df = pd.read_csv(IN_PATH, index_col="date", parse_dates=True)

    print(f"Loaded {len(df)} rows from {IN_PATH}")
    print(f"Date range: {df.index.min().date()} to {df.index.max().date()}\n")

    # Year-over-year percent change compares each month with the same month
    # one year earlier. This removes seasonality and is the standard way most
    # CPI releases discuss 12-month inflation.
    yoy = df.pct_change(12) * 100
    yoy.columns = [f"{col}_yoy" for col in yoy.columns]

    # Month-over-month percent change compares each month with the prior month.
    # Because the input series are seasonally adjusted, these short-term moves
    # can be compared across months.
    mom = df.pct_change(1) * 100
    mom.columns = [f"{col}_mom" for col in mom.columns]

    # Keep raw levels and derived rates together. The post mostly charts the
    # derived rates, but keeping levels makes the CSV easier to audit.
    result = pd.concat([df, yoy, mom], axis=1)

    # The first 12 months cannot have YoY changes, so remove them before charting.
    result = result.dropna(subset=["headline_yoy"])

    # Start the chart-ready dataset in 2023. The post visualizes 2024 onward,
    # but 2023 context is useful for validation and future chart variants.
    result = result[result.index >= "2023-01-01"]

    os.makedirs("data/clean", exist_ok=True)
    result.to_csv(OUT_PATH)

    print(f"Saved {len(result)} rows to {OUT_PATH}")
    print("\nMarch 2026 snapshot:")
    mar = result.loc["2026-03-01"]
    for col in ["headline_yoy", "core_yoy", "energy_yoy", "shelter_yoy", "food_yoy"]:
        print(f"  {col:20s}: {mar[col]:+.2f}%")


if __name__ == "__main__":
    main()
