"""
01_fetch_data.py
================
STEP 1 of the data pipeline.

What this script does
---------------------
Downloads public FRED series for the August 2026 jobs post and writes raw
CSVs. No rates or monthly job changes are calculated here.

Pipeline order
--------------
    python scripts/01_fetch_data.py     # you are here: download
    python scripts/02_clean_data.py     # next: changes, m/m, y/y
    python scripts/04_compute_stats.py  # then: stats JSON for the prose

FRED API key (required)
-----------------------
https://fred.stlouisfed.org/docs/api/api_key.html

    PowerShell:  $env:FRED_API_KEY="your_key_here"

Run from this post folder:
    python scripts/01_fetch_data.py

Friendly name -> FRED ID. Later scripts use the friendly names so they
never have to remember CES7072200001 versus PAYEMS.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from fredapi import Fred

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"

# Employment levels are in thousands of jobs unless noted.
MONTHLY_SERIES = {
    "payems": "PAYEMS",  # total nonfarm payrolls
    "uspriv": "USPRIV",  # private payrolls
    "usgovt": "USGOVT",  # government payrolls
    "unrate": "UNRATE",  # unemployment rate, % of the labor force
    "u6rate": "U6RATE",  # U-6 underutilization rate, %
    "civpart": "CIVPART",  # labor-force participation rate, % of adults
    "emratio": "EMRATIO",  # employment-population ratio, %
    "ahe": "CES0500000003",  # average hourly earnings, all private employees, $
    "ahe_prod": "AHETPI",  # average hourly earnings, production workers, $
    "hours": "AWHAETP",  # average weekly hours, all private employees
    "food_services": "CES7072200001",  # food services and drinking places
    "local_education": "CES9093161101",  # local government education
    "construction": "USCONS",
    "manufacturing": "MANEMP",
    "information": "USINFO",
    "leisure": "USLAH",  # leisure and hospitality (includes food services)
    "healthcare": "CES6562000101",
    "labor_force": "CLF16OV",  # civilian labor force, thousands
    "employed": "CE16OV",  # civilian employment, thousands
    "nilf": "LNS15000000",  # not in labor force, thousands
    "unemployed": "UNEMPLOY",  # unemployment level, thousands
    "pte_economic": "LNS12032194",  # part time for economic reasons, thousands
    "jolts_openings": "JTSJOL",  # job openings, thousands (lags the jobs print)
    "jolts_quits_rate": "JTSQUR",  # quits rate, % (lags the jobs print)
}

WEEKLY_SERIES = {
    "initial_claims": "ICSA",  # new unemployment insurance claims
}


def fetch_monthly(fred: Fred, series_id: str, start: str) -> pd.Series:
    """Download one FRED series and keep one value per calendar month.

    FRED stamps months as the first day (2026-08-01). Converting to a monthly
    period, then back to a timestamp, makes later joins easy.
    """
    series = fred.get_series(series_id, observation_start=start)
    if series.empty:
        raise RuntimeError(f"FRED series returned no observations: {series_id}")
    series.index = series.index.to_period("M").to_timestamp()
    return series.groupby(series.index).last().sort_index()


def fetch_weekly(fred: Fred, series_id: str, start: str) -> pd.Series:
    """Download a weekly series (initial claims, Saturday weeks)."""
    series = fred.get_series(series_id, observation_start=start)
    if series.empty:
        raise RuntimeError(f"FRED series returned no observations: {series_id}")
    return series.sort_index()


def main() -> None:
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY is required. Get one at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)

    monthly_frames: dict[str, pd.Series] = {}
    latest: dict[str, str] = {}
    for name, series_id in MONTHLY_SERIES.items():
        print(f"Fetching {name} ({series_id})")
        info = fred.get_series_info(series_id)
        monthly_frames[name] = fetch_monthly(fred, series_id, "2019-01-01")
        last = monthly_frames[name].dropna().index[-1].strftime("%Y-%m-%d")
        latest[name] = last
        print(f"  {info['title'][:70]} | last={last}")

    monthly = pd.DataFrame(monthly_frames).sort_index()
    monthly.index.name = "date"
    monthly.to_csv(RAW_DIR / "fred_monthly.csv")

    weekly_frames: dict[str, pd.Series] = {}
    for name, series_id in WEEKLY_SERIES.items():
        print(f"Fetching {name} ({series_id})")
        weekly_frames[name] = fetch_weekly(fred, series_id, "2019-01-01")
        last = weekly_frames[name].dropna().index[-1].strftime("%Y-%m-%d")
        latest[name] = last
        print(f"  last={last}")

    weekly = pd.DataFrame(weekly_frames).sort_index()
    weekly.index.name = "date"
    weekly.to_csv(RAW_DIR / "fred_weekly.csv")

    sources = {
        "retrieved_for": "August 2026 Employment Situation",
        "bls_release_url": "https://www.bls.gov/news.release/empsit.nr0.htm",
        "fred": "https://fred.stlouisfed.org/",
        "monthly_series": MONTHLY_SERIES,
        "weekly_series": WEEKLY_SERIES,
        "latest_observation": latest,
        "notes": [
            "PAYEMS and industry CES series are employment levels in thousands.",
            "JOLTS series lag the monthly jobs print; do not treat them as August.",
            "First-print payroll revisions are not in FRED vintages and are pinned in 04.",
        ],
    }
    (RAW_DIR / "sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    print("Wrote", RAW_DIR / "fred_monthly.csv")
    print("Wrote", RAW_DIR / "fred_weekly.csv")
    print("Wrote", RAW_DIR / "sources.json")


if __name__ == "__main__":
    main()
