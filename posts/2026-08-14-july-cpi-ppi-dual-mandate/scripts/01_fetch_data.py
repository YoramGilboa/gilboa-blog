"""
Step 1 of 3: download the monthly price, labor, and policy series for this post.

Run from the post directory:
  1. python scripts/01_fetch_data.py
  2. python scripts/02_clean_data.py
  3. python scripts/04_compute_stats.py

The script prefers FRED series because they provide a stable, reproducible feed
for CPI, PPI, labor-market, wages, and policy-rate context.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from fredapi import Fred

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"

MONTHLY_SERIES = {
    "cpi_headline": "CPIAUCSL",
    "cpi_core": "CPILFESL",
    "cpi_headline_unadjusted": "CPIAUCNS",
    "cpi_core_unadjusted": "CPILFENS",
    "cpi_energy": "CPIENGSL",
    "cpi_food": "CPIFABSL",
    "cpi_shelter": "CUSR0000SAH1",
    "cpi_core_goods": "CUSR0000SACL1E",
    "cpi_medical_services": "CUSR0000SAM2",
    "ppi_final_demand": "PPIFIS",
    "ppi_final_demand_goods": "PPIFDG",
    "ppi_final_demand_services": "PPIFDS",
    "ppi_energy": "PPIFDE",
    "ppi_less_food_energy_trade": "WPSFD49116",
    "ahe_total_private": "CES0500000003",
    "payems": "PAYEMS",
    "unrate": "UNRATE",
    "civpart": "CIVPART",
}

DAILY_SERIES = {
    "fed_target_upper": "DFEDTARU",
    "fed_target_lower": "DFEDTARL",
}


def fetch_monthly_series(fred: Fred, series_id: str, start_date: str) -> pd.Series:
    """Fetch one FRED series and normalize it to one value per calendar month."""
    series = fred.get_series(series_id, observation_start=start_date)
    if series.empty:
        raise RuntimeError(f"FRED series returned no observations: {series_id}")
    series.index = series.index.to_period("M").to_timestamp()
    series = series.groupby(series.index).last().sort_index()
    return series


def fetch_daily_series(fred: Fred, series_id: str, start_date: str) -> pd.Series:
    """Fetch a daily FRED series without monthly aggregation."""
    series = fred.get_series(series_id, observation_start=start_date)
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
        monthly_frames[name] = fetch_monthly_series(fred, series_id, "2019-01-01")

    monthly = pd.DataFrame(monthly_frames).sort_index()
    monthly.index.name = "date"
    monthly.to_csv(RAW_DIR / "fred_monthly.csv")

    daily_frames: dict[str, pd.Series] = {}
    for name, series_id in DAILY_SERIES.items():
        print(f"Fetching {name} ({series_id})")
        daily_frames[name] = fetch_daily_series(fred, series_id, "2025-01-01")

    daily = pd.DataFrame(daily_frames).sort_index()
    daily.index.name = "date"
    daily.to_csv(RAW_DIR / "fred_daily.csv")

    latest_dates = {
        column: monthly[column].dropna().index[-1].strftime("%Y-%m-%d")
        for column in monthly.columns
    }
    print("Wrote", RAW_DIR / "fred_monthly.csv")
    print(latest_dates)


if __name__ == "__main__":
    main()