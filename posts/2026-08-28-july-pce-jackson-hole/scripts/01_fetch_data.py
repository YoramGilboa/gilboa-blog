"""
01_fetch_data.py
================
STEP 1 of the data pipeline.

What this script does
---------------------
Downloads public FRED series used in the July PCE / Jackson Hole post
and writes them as raw CSVs. No rates are calculated here.

Pipeline order
--------------
    python scripts/01_fetch_data.py     # you are here: download
    python scripts/02_clean_data.py     # next: rates and July overlay
    python scripts/03_visualizations.py # then: save the five PNGs
    python scripts/04_compute_stats.py  # then: stats JSON for the prose

FRED API key (required)
-----------------------
https://fred.stlouisfed.org/docs/api/api_key.html

    PowerShell:  $env:FRED_API_KEY="your_key_here"

Run from this post folder:
    python scripts/01_fetch_data.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from fredapi import Fred

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"

# Friendly column name -> FRED series ID.
# Friendly name -> FRED ID. FRED IDs are short codes; we rename them so
# later scripts never have to remember PCEPI vs PCEPILFE.
MONTHLY_SERIES = {
    "pce_headline": "PCEPI",       # price index for all household spending
    "pce_core": "PCEPILFE",        # same index excluding food and energy
    "saving_rate": "PSAVERT",      # saving as a % of after-tax income
    "payems": "PAYEMS",            # nonfarm payrolls, thousands
    "unrate": "UNRATE",            # unemployment rate, % of the labor force
    "civpart": "CIVPART",          # labor-force participation rate, % of adults
    "real_pce": "DPCERA3M086SBEA", # inflation-adjusted spending volume (index)
}

DAILY_SERIES = {
    "fed_target_upper": "DFEDTARU",
}


def fetch_monthly(fred: Fred, series_id: str, start: str) -> pd.Series:
    """Download one FRED series and keep one value per calendar month.

    FRED sometimes stamps a month as the first day (2026-07-01). Converting
    to a monthly period, then back to a timestamp, makes later joins easy.
    If two rows land in the same month, we keep the last one.
    """
    series = fred.get_series(series_id, observation_start=start)
    if series.empty:
        raise RuntimeError(f"FRED series returned no observations: {series_id}")
    series.index = series.index.to_period("M").to_timestamp()
    return series.groupby(series.index).last().sort_index()


def fetch_daily(fred: Fred, series_id: str, start: str) -> pd.Series:
    """Download a daily series (the fed-funds target can change mid-month)."""
    series = fred.get_series(series_id, observation_start=start)
    if series.empty:
        raise RuntimeError(f"FRED series returned no observations: {series_id}")
    return series.sort_index()


def main() -> None:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY is required. Get one at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)

    monthly_frames: dict[str, pd.Series] = {}
    for name, series_id in MONTHLY_SERIES.items():
        print(f"Fetching {name} ({series_id})")
        monthly_frames[name] = fetch_monthly(fred, series_id, "2019-01-01")

    monthly = pd.DataFrame(monthly_frames).sort_index()
    monthly.index.name = "date"
    monthly.to_csv(RAW_DIR / "fred_monthly.csv")

    daily_frames: dict[str, pd.Series] = {}
    for name, series_id in DAILY_SERIES.items():
        print(f"Fetching {name} ({series_id})")
        daily_frames[name] = fetch_daily(fred, series_id, "2019-01-01")

    daily = pd.DataFrame(daily_frames).sort_index()
    daily.index.name = "date"
    daily.to_csv(RAW_DIR / "fred_daily.csv")

    latest = {
        column: monthly[column].dropna().index[-1].strftime("%Y-%m-%d")
        for column in monthly.columns
    }
    print("Wrote", RAW_DIR / "fred_monthly.csv")
    print("Latest FRED months:", latest)


if __name__ == "__main__":
    main()
