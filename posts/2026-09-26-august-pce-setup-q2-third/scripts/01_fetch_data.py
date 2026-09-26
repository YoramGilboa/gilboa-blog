"""
01_fetch_data.py
================
STEP 1 of the data pipeline.

What this script does
---------------------
Downloads published FRED history for prices, income, real spending, the
saving rate, and quarterly GDP. It also writes the non-FRED facts this
post is allowed to cite (the September FOMC, August CPI, August payrolls,
the BEA second-estimate advance column, and the annual-update window).

No month-over-month or year-over-year rates are calculated here.

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

Friendly name -> FRED series ID
--------------------------------
Monthly levels (not rates):
    pce_price        PCEPI              headline PCE price index
    core_price       PCEPILFE           PCE price index ex food and energy
    real_pce         PCEC96             real personal consumption expenditures
    saving_rate      PSAVERT            personal saving as a percent of DPI
    personal_income  PI                 personal income, billions of dollars
    disposable_pi    DSPI               disposable personal income
    nominal_pce      PCE                nominal personal consumption expenditures

Quarterly percent changes, already published by BEA as SAAR rates:
    gdp_saar         A191RL1Q225SBEA    real GDP growth
    pdfp_saar        PB0000031Q225SBEA  real final sales to private domestic purchasers

Raw CSV contents
----------------
fred_pce_monthly.csv: one row per month, levels (saving rate is already a percent).
fred_gdp_quarterly.csv: one row per quarter, percent changes.
manual_priors.json: transcribed official facts with source URLs.
sources.json: the URL list.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from fredapi import Fred

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"

# History starts in 2018 so a 12-month rate exists well before the charts do.
FETCH_START = "2018-01-01"

MONTHLY_SERIES = {
    "pce_price": "PCEPI",
    "core_price": "PCEPILFE",
    "real_pce": "PCEC96",
    "saving_rate": "PSAVERT",
    "personal_income": "PI",
    "disposable_pi": "DSPI",
    "nominal_pce": "PCE",
}

QUARTERLY_SERIES = {
    "gdp_saar": "A191RL1Q225SBEA",
    "pdfp_saar": "PB0000031Q225SBEA",
}

# MANUAL: facts that are not a FRED calculation. URLs are the primary sources.
# Do not add August 2026 PCE or a Q2 third-estimate growth rate here.
MANUAL_PRIORS = {
    "pce_release_url": "https://www.bea.gov/news/2026/personal-income-and-outlays-july-2026",
    "gdp_second_url": "https://www.bea.gov/news/2026/gdp-second-estimate-and-corporate-profits-2nd-quarter-2026",
    "annual_update_url": "https://www.bea.gov/information-updates-national-regional-economic-accounts",
    "annual_update_blog_url": "https://www.bea.gov/news/blog/2026-08-17/annual-update-gdp-industry-and-state-stats-publicly-available-starting-sept-30",
    "fomc_statement_url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
    "fomc_sep_url": "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm",
    "fomc_calendar_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "minutes_calendar_url": "https://www.federalreserve.gov/newsevents/2026-october.htm",
    "cpi_release_url": "https://www.bls.gov/news.release/cpi.nr0.htm",
    "payrolls_url": "https://www.bls.gov/news.release/empsit.nr0.htm",
    "target_range": "3.75 to 4.00",
    "hike_bp": 25,
    "sep_funds_2026": 4.1,
    "dots_one_more": 12,
    "dots_total": 18,
    "cpi_headline_mom": 0.4,
    "cpi_core_mom": 0.3,
    "cpi_gasoline_mom": 3.9,
    "payroll_aug_k": 162,
    "gdp_q2_advance": 1.5,
    "pdfp_q2_advance": 3.9,
    "revision_window": "Q1 2021 through Q1 2026",
    "annual_update_scope": "national, industry, and regional statistics begin on the same day for the first time",
    "reference_year": 2017,
}


def fetch_series(fred: Fred, series_id: str) -> pd.Series:
    """Download one FRED series and keep published gaps.

    A missing month stays missing. Do not fill it.
    """
    series = fred.get_series(series_id, observation_start=FETCH_START)
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
        {name: fetch_series(fred, series_id) for name, series_id in MONTHLY_SERIES.items()}
    ).sort_index()
    monthly.index = monthly.index.to_period("M").to_timestamp()
    monthly = monthly.groupby(monthly.index).last().sort_index()
    monthly.index.name = "date"
    monthly.to_csv(RAW_DIR / "fred_pce_monthly.csv")

    quarterly = pd.DataFrame(
        {name: fetch_series(fred, series_id) for name, series_id in QUARTERLY_SERIES.items()}
    ).sort_index()
    quarterly.index.name = "date"
    quarterly.to_csv(RAW_DIR / "fred_gdp_quarterly.csv")

    (RAW_DIR / "manual_priors.json").write_text(
        json.dumps(MANUAL_PRIORS, indent=2) + "\n",
        encoding="utf-8",
    )
    sources = {
        "fred_monthly": MONTHLY_SERIES,
        "fred_quarterly": QUARTERLY_SERIES,
        "manual": {
            key: value
            for key, value in MANUAL_PRIORS.items()
            if key.endswith("_url")
        },
        "history_rule": "Monthly charts stop at July 2026. Quarterly charts stop at the Q2 2026 second estimate. August PCE is not filled.",
    }
    (RAW_DIR / "sources.json").write_text(
        json.dumps(sources, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote monthly rows: {len(monthly):,}  last={monthly.index.max().date()}")
    print(f"Wrote quarterly rows: {len(quarterly):,}  last={quarterly.index.max().date()}")


if __name__ == "__main__":
    main()
