"""
01_fetch_data.py
----------------
Fetch monthly CPI index levels from FRED and save them to
data/raw/fred_cpi_raw.csv.

FRED is a public data service run by the St. Louis Fed. This script requires
a free API key: https://fred.stlouisfed.org/docs/api/api_key.html

Before running, set your API key as an environment variable:
    Windows:   set FRED_API_KEY=your_key_here
    PowerShell: $env:FRED_API_KEY="your_key_here"
    Mac/Linux: export FRED_API_KEY=your_key_here

Run from the post folder:
    python scripts/01_fetch_data.py
"""

import os

import pandas as pd
from fredapi import Fred


# We fetch from 2022 onward so year-over-year values can be computed for
# every month shown in the charts beginning in 2023.
START_DATE = "2022-01-01"
END_DATE = "2026-03-01"

# FRED series IDs for the CPI components used in this post. These are
# seasonally adjusted series, which are appropriate for month-over-month
# comparisons because regular seasonal patterns have been removed.
SERIES = {
    "headline": "CPIAUCSL",      # CPI-U all items
    "core": "CPILFESL",         # CPI-U less food and energy
    "energy": "CPIENGSL",       # Energy CPI
    "shelter": "CUSR0000SAH1",  # Shelter CPI
    "food": "CPIFABSL",         # Food and beverages CPI
}

OUT_PATH = "data/raw/fred_cpi_raw.csv"


def main():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY not found. Set it as an environment variable before running."
        )

    fred = Fred(api_key=api_key)

    print(f"Fetching {len(SERIES)} CPI series from FRED ({START_DATE} to {END_DATE})...\n")

    # Fetch each FRED series into a pandas Series. The DatetimeIndex lets the
    # cleaning script align all components by month with no manual date joins.
    frames = {}
    for friendly_name, series_id in SERIES.items():
        print(f"  {friendly_name:10s} <- {series_id}")
        frames[friendly_name] = fred.get_series(
            series_id,
            observation_start=START_DATE,
            observation_end=END_DATE,
        )

    df = pd.DataFrame(frames)
    df.index.name = "date"

    # Drop incomplete months in case one FRED series is updated later than the
    # others. This keeps the downstream calculations aligned across components.
    df = df.dropna()

    os.makedirs("data/raw", exist_ok=True)
    df.to_csv(OUT_PATH)

    print(f"\nSaved {len(df)} monthly observations to {OUT_PATH}")
    print("\nLast 3 rows:")
    print(df.tail(3).to_string())


if __name__ == "__main__":
    main()
