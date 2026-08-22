"""
Step 1 of 3: download FRED series and write curated FedWatch snapshots.

Run from the post directory:
  1. python scripts/01_fetch_data.py
  2. python scripts/02_clean_data.py
  3. python scripts/04_compute_stats.py

FRED supplies CPI, PCE, labor, retail, housing, and Treasury yields.
CME FedWatch probabilities are not a FRED series, so this script writes a
small curated snapshot table with source URLs in data/raw/sources.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from fredapi import Fred

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"

# Friendly name -> FRED series ID. These are the public series used in charts
# and in the prose stats file.
MONTHLY_SERIES = {
    "cpi_headline": "CPIAUCSL",
    "cpi_core": "CPILFESL",
    "cpi_headline_unadjusted": "CPIAUCNS",
    "cpi_core_unadjusted": "CPILFENS",
    "cpi_energy": "CPIENGSL",
    "cpi_food": "CPIFABSL",
    "cpi_shelter": "CUSR0000SAH1",
    "cpi_core_goods": "CUSR0000SACL1E",
    "pce_headline": "PCEPI",
    "pce_core": "PCEPILFE",
    "payems": "PAYEMS",
    "unrate": "UNRATE",
    "civpart": "CIVPART",
    "retail_sales": "RSAFS",
    "housing_starts": "HOUST",
}

DAILY_SERIES = {
    "fed_target_upper": "DFEDTARU",
    "fed_target_lower": "DFEDTARL",
    "dgs10": "DGS10",
}


def fetch_monthly_series(fred: Fred, series_id: str, start_date: str) -> pd.Series:
    """Fetch one FRED series and keep one value per calendar month."""
    series = fred.get_series(series_id, observation_start=start_date)
    if series.empty:
        raise RuntimeError(f"FRED series returned no observations: {series_id}")
    series.index = series.index.to_period("M").to_timestamp()
    return series.groupby(series.index).last().sort_index()


def fetch_daily_series(fred: Fred, series_id: str, start_date: str) -> pd.Series:
    """Fetch a daily FRED series without monthly aggregation."""
    series = fred.get_series(series_id, observation_start=start_date)
    if series.empty:
        raise RuntimeError(f"FRED series returned no observations: {series_id}")
    return series.sort_index()


def write_fedwatch_snapshots() -> None:
    """Write three CME FedWatch snapshots compiled from contemporaneous reports.

    CME does not publish a stable historical CSV, so these are documented
    point-in-time readings used only for the three-bar market chart.
    """
    snapshots = pd.DataFrame(
        [
            {
                "snapshot": "before_soft_data",
                "label": "Before soft data",
                "as_of": "2026-08-06",
                "sept_hike_prob": 55.0,
                "sept_hold_prob": 45.0,
                "source": "Barron's, 08/07/2026, citing CME FedWatch (Thursday close before jobs)",
            },
            {
                "snapshot": "after_soft_data",
                "label": "After soft data",
                "as_of": "2026-08-17",
                "sept_hike_prob": 30.6,
                "sept_hold_prob": 69.4,
                "source": "MacroMicro CME FedWatch series as of 08/17/2026",
            },
            {
                "snapshot": "after_minutes",
                "label": "After minutes",
                "as_of": "2026-08-21",
                "sept_hike_prob": 35.6,
                "sept_hold_prob": 64.4,
                "source": "Investing.com Fed rate monitor, CME futures implied, 08/21/2026",
            },
        ]
    )
    snapshots.to_csv(RAW_DIR / "fedwatch_snapshots.csv", index=False)

    sources = {
        "minutes": {
            "url": "https://www.federalreserve.gov/monetarypolicy/fomcminutes20260729.htm",
            "used_for": "Vote, dissents, and qualitative language from the July 28-29, 2026 meeting",
        },
        "fedwatch": {
            "tool": "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html",
            "used_for": "September 2026 hike vs hold probabilities at three dates",
            "snapshots": snapshots.to_dict(orient="records"),
        },
        "bls_jobs": {
            "url": "https://www.bls.gov/news.release/empsit.htm",
            "used_for": "July payroll first print and May/June revisions",
        },
        "census_retail": {
            "url": "https://www.census.gov/retail/sales.html",
            "used_for": "July advance retail sales confirmation",
        },
        "census_housing": {
            "url": "https://www.census.gov/construction/nrc/current/index.html",
            "used_for": "July housing starts confirmation",
        },
    }
    (RAW_DIR / "sources.json").write_text(
        json.dumps(sources, indent=2),
        encoding="utf-8",
    )


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

    write_fedwatch_snapshots()

    latest_dates = {
        column: monthly[column].dropna().index[-1].strftime("%Y-%m-%d")
        for column in monthly.columns
    }
    print("Wrote", RAW_DIR / "fred_monthly.csv")
    print(latest_dates)
    print("Wrote", RAW_DIR / "fedwatch_snapshots.csv")


if __name__ == "__main__":
    main()
