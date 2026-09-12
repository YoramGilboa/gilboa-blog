"""
01_fetch_data.py
================
STEP 1 of the data pipeline.

What this script does
---------------------
Downloads public FRED CPI indexes and the federal funds target range, and
writes the official BLS Table 1 August 2026 prints used as the release
anchor. No month-over-month or year-over-year rates are calculated here.

Pipeline order
--------------
    python scripts/01_fetch_data.py     # you are here: download
    python scripts/02_clean_data.py     # next: m/m, y/y, annualized rates
    python scripts/04_compute_stats.py  # then: stats JSON for the prose

FRED API key (required)
-----------------------
https://fred.stlouisfed.org/docs/api/api_key.html

    PowerShell:  $env:FRED_API_KEY="your_key_here"

Run from this post folder:
    python scripts/01_fetch_data.py

Friendly name -> FRED ID. Later scripts use the friendly names so they
never have to remember CUSR0000SASL2RS versus CPIAUCSL.

Raw CSV contents
----------------
fred_cpi_monthly.csv: one row per month, index levels (not rates).
fred_policy_daily.csv: daily federal funds target bounds.
bls_cpi_table1_august_2026.csv: official Table 1 rounded prints and
July relative-importance weights, entered from the BLS release.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from fredapi import Fred

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"

# CPI-U index levels. Seasonally adjusted (SA) series are used for monthly
# changes. Not seasonally adjusted (NSA) series are used for 12-month rates.
MONTHLY_SERIES = {
    "headline_sa": "CPIAUCSL",
    "headline_nsa": "CPIAUCNS",
    "core_sa": "CPILFESL",
    "core_nsa": "CPILFENS",
    "food_sa": "CPIUFDSL",
    "food_nsa": "CPIUFDNS",
    "energy_sa": "CPIENGSL",
    "energy_nsa": "CPIENGNS",
    "gasoline_sa": "CUSR0000SETB01",
    "gasoline_nsa": "CUUR0000SETB01",
    "core_goods_sa": "CUSR0000SACL1E",
    "core_goods_nsa": "CUUR0000SACL1E",
    "services_less_energy_sa": "CUSR0000SASLE",
    "services_less_energy_nsa": "CUUR0000SASLE",
    "services_less_shelter_sa": "CUSR0000SASL2RS",
    "services_less_shelter_nsa": "CUUR0000SASL2RS",
    "shelter_sa": "CUSR0000SAH1",
    "shelter_nsa": "CUUR0000SAH1",
    "rent_sa": "CUSR0000SEHA",
    "rent_nsa": "CUUR0000SEHA",
    "oer_sa": "CUSR0000SEHC",
    "oer_nsa": "CUUR0000SEHC",
}

DAILY_SERIES = {
    "fed_target_lower": "DFEDTARL",
    "fed_target_upper": "DFEDTARU",
}

BLS_CPI_URL = "https://www.bls.gov/news.release/cpi.t01.htm"
BLS_RELEASE_URL = "https://www.bls.gov/news.release/cpi.nr0.htm"
REQUIRED_MONTHLY = ("headline_sa", "headline_nsa", "core_sa", "core_nsa")


def fetch_series(fred: Fred, series_id: str, start_date: str) -> pd.Series:
    """Download one FRED series and keep FRED's published NaNs.

    Do not drop missing months here. A NaN is information: FRED has a
    date stamp but no value. October 2025 all-items CPI is the example.
    """
    series = fred.get_series(series_id, observation_start=start_date)
    if series is None or series.empty:
        raise RuntimeError(f"FRED series returned no observations: {series_id}")
    return series.sort_index()


def main() -> None:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY is required. Register at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)

    monthly = pd.DataFrame(
        {
            name: fetch_series(fred, series_id, "2020-01-01")
            for name, series_id in MONTHLY_SERIES.items()
        }
    ).sort_index()
    monthly.index = monthly.index.to_period("M").to_timestamp()
    monthly = monthly.groupby(monthly.index).last().sort_index()
    monthly.index.name = "date"
    monthly.to_csv(RAW_DIR / "fred_cpi_monthly.csv")

    daily = pd.DataFrame(
        {
            name: fetch_series(fred, series_id, "2026-01-01")
            for name, series_id in DAILY_SERIES.items()
        }
    ).sort_index()
    daily.index.name = "date"
    daily.to_csv(RAW_DIR / "fred_policy_daily.csv")

    # MANUAL: Official August 2026 CPI-U Table 1, released 9/11/2026.
    # https://www.bls.gov/news.release/cpi.t01.htm
    # Relative importance is the July 2026 weight used for the August change.
    release_rows = [
        ("all_items", 100.000, 0.1, 0.4, 3.4),
        ("food", 13.540, 0.1, 0.1, 2.7),
        ("energy", 7.347, -1.5, 2.1, 16.3),
        ("gasoline", 3.770, -2.9, 3.9, 27.4),
        ("core", 79.114, 0.2, 0.3, 2.4),
        ("core_goods", 18.842, 0.2, 0.1, 0.7),
        ("services_less_energy", 60.272, 0.2, 0.3, 3.0),
        ("shelter", 35.343, 0.1, 0.3, 3.0),
        ("rent", 7.735, 0.3, 0.2, 2.7),
        ("oer", 25.918, 0.3, 0.2, 3.1),
    ]
    release = pd.DataFrame(
        release_rows,
        columns=[
            "component",
            "relative_importance",
            "july_mom_sa",
            "august_mom_sa",
            "august_yoy_nsa",
        ],
    )
    release.to_csv(RAW_DIR / "bls_cpi_table1_august_2026.csv", index=False)

    sources = {
        "bls_cpi_release": BLS_RELEASE_URL,
        "bls_cpi_table_1": BLS_CPI_URL,
        "fred": "https://fred.stlouisfed.org/",
        "fred_series": MONTHLY_SERIES | DAILY_SERIES,
        "fomc_calendar": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "june_sep": "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260617.htm",
        "bea_schedule": "https://www.bea.gov/news/schedule",
        "notes": [
            "FRED CPIAUCSL/CPILFESL have a published NaN for 2025-10-01.",
            "Do not interpolate that month. Charts must show the calendar gap.",
        ],
    }
    (RAW_DIR / "sources.json").write_text(
        json.dumps(sources, indent=2) + "\n", encoding="utf-8"
    )

    missing = monthly.loc["2021-01-01":, list(REQUIRED_MONTHLY)]
    gap_months = [
        stamp.strftime("%Y-%m")
        for stamp, row in missing.iterrows()
        if row.isna().any()
    ]
    latest = monthly.dropna(how="all").index.max().strftime("%Y-%m-%d")
    print(f"Wrote official CPI histories through {latest}")
    print(f"Wrote {len(release)} verified BLS Table 1 rows")
    print(f"Headline/core FRED gap months: {gap_months or 'none'}")


if __name__ == "__main__":
    main()
