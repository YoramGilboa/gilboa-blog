"""
Step 1 of 3: download raw price indexes from FRED.

Pipeline order (run from this post folder):
  1. python scripts/01_fetch_data.py   <-- you are here
  2. python scripts/02_clean_data.py   # builds m/m, y/y, 3-month rates
  3. python scripts/04_compute_stats.py  # writes stats for the prose/cards

What this script does
  - Calls the St. Louis Fed FRED API for each BLS price index we need.
  - Saves one tidy CSV: data/raw/fred_monthly.csv
  - Does NOT compute percent changes (that is 02_clean_data.py).

Setup for beginners
  - Get a free API key: https://fred.stlouisfed.org/docs/api/api_key.html
  - Set it in your environment before running, for example (PowerShell):
      $env:FRED_API_KEY = "your_key_here"
  - Install deps from the repo root: pip install -r requirements.txt
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from fredapi import Fred

# Post folder is one level above scripts/ (…/2026-07-25-…-pipeline/).
POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"

# Friendly name -> FRED series ID.
# Friendly names become column names in the raw CSV and in clean data.
# Full plain-English labels also appear in the post Methodology table.
SERIES = {
    # --- Producer Price Index (upstream / producer side) ---
    "ppi_final_demand": "PPIFIS",  # Headline final demand PPI
    "ppi_final_demand_goods": "PPIFDG",  # Goods only at final demand
    "ppi_finished_goods": "WPSFD49207",  # Finished goods stage
    "ppi_final_demand_services": "PPIFDS",  # Services at final demand
    "ppi_energy": "PPIFDE",  # Energy component of final demand
    "ppi_foods": "WPSFD4111",  # Finished consumer foods
    "ppi_goods_less_food_energy": "WPSFD413",  # Core-ish goods at producer level
    # Cleaner pipeline gauge (removes food, energy, and trade services)
    "ppi_less_food_energy_trade": "WPSFD49116",
    # Trade-services margins (used in prose only, not plotted)
    "ppi_trade_services": "PPITSS",
    # --- Consumer Price Index (downstream / household side) ---
    "cpi_headline": "CPIAUCSL",
    "cpi_core": "CPILFESL",  # CPI less food and energy
    "cpi_energy": "CPIENGSL",
    "cpi_core_goods": "CUSR0000SACL1E",  # Commodities less food and energy
}

# Start date for the download window. Charts later may zoom further in.
START_DATE = "2023-01-01"


def fetch_monthly_series(fred: Fred, series_id: str) -> pd.Series:
    """
    Pull one FRED series and force a clean monthly date index.

    FRED sometimes returns daily-stamped monthly values. Converting to a
    monthly period and taking the last observation per month keeps one
    row per calendar month, which matches how BLS publishes these indexes.
    """
    series = fred.get_series(series_id, observation_start=START_DATE)
    if series.empty:
        raise RuntimeError(f"FRED series returned no observations: {series_id}")

    # Normalize to month-start timestamps (e.g. 2026-06-01 for June 2026).
    series.index = series.index.to_period("M").to_timestamp()
    series = series.groupby(series.index).last().sort_index()
    series.name = series_id
    return series


def main() -> None:
    # Never hard-code the API key in the file. Read it from the environment.
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY is required. Get one at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)

    # Download each series one at a time so failures name the bad ID.
    frames: dict[str, pd.Series] = {}
    for name, series_id in SERIES.items():
        print(f"Fetching {name} ({series_id})")
        frames[name] = fetch_monthly_series(fred, series_id)

    # Align all series on a shared date index (outer join via DataFrame).
    raw = pd.DataFrame(frames).sort_index()
    raw.index.name = "date"
    raw.to_csv(RAW_DIR / "fred_monthly.csv")

    # Helpful checkpoint: when does each column last have a real value?
    latest_dates = {
        column: raw[column].dropna().index[-1].strftime("%Y-%m-%d")
        for column in raw.columns
    }
    print("Wrote", RAW_DIR / "fred_monthly.csv")
    print(latest_dates)


if __name__ == "__main__":
    main()
