"""
01_fetch_data.py
----------------
Step 1 of the pipeline: download every data series this post uses.

What this script does, in plain English:
  1. Connects to FRED, the free public data service run by the Federal
     Reserve Bank of St. Louis. Almost every official US statistic this post
     needs (consumer prices, wages, oil prices, Treasury yields) is
     republished there under a short series code, like CPIAUCSL for the
     Consumer Price Index.
  2. Downloads each series and collects related ones into a table where each
     row is a date and each column is one series.
  3. Saves those tables as CSV files (plain spreadsheets) under data/raw/,
     untouched. Later scripts read from these files instead of the internet,
     which keeps every downstream number reproducible.

FRED requires a free API key (a personal access code):
https://fred.stlouisfed.org/docs/api/api_key.html

Before running, set your key as an environment variable:
    Windows:    set FRED_API_KEY=your_key_here
    PowerShell: $env:FRED_API_KEY="your_key_here"
    Mac/Linux:  export FRED_API_KEY=your_key_here

Run from the post folder:
    python scripts/01_fetch_data.py
"""

import os

import pandas as pd
from fredapi import Fred

# ---------------------------------------------------------------------------
# The shopping list: every FRED series the post uses, grouped by how often
# the data is published (monthly, daily, or weekly). The left-hand names are
# friendly labels used as column headers; the right-hand codes are FRED IDs.
# ---------------------------------------------------------------------------

# Monthly consumer price indexes, seasonally adjusted (regular seasonal
# swings, like summer gasoline demand, are already removed, which makes
# month-to-month comparisons meaningful). The download starts in 1999 on
# purpose: the post compares today's energy shock with the 2008 and 2022
# episodes, and computing a year-over-year change for January 2000 requires
# data back to January 1999.
CPI_START = "1999-01-01"
CPI_SERIES = {
    "headline": "CPIAUCSL",          # CPI, all items: the headline inflation basket
    "core": "CPILFESL",              # CPI excluding food and energy ("core")
    "energy": "CPIENGSL",            # Energy prices only
    "gasoline": "CUSR0000SETB01",    # Gasoline prices only
    "shelter": "CUSR0000SAH1",       # Rent and owners' equivalent rent
    "food": "CPIFABSL",              # Food and beverages
    "core_goods": "CUSR0000SACL1E",  # Physical goods, excluding food and energy
    "core_services": "CUSR0000SASLE",  # Services, excluding energy services
}

# Monthly labor market series, used for the wages section.
LABOR_START = "2015-01-01"
LABOR_SERIES = {
    "ahe": "CES0500000003",  # Average hourly earnings, private workers, $/hour
    "payems": "PAYEMS",      # Total jobs on nonfarm payrolls, in thousands
    "unrate": "UNRATE",      # Unemployment rate, percent
}

# Daily financial market series, used for the oil-passthrough and
# interest-rate sections.
MARKET_START = "2024-01-01"
DAILY_SERIES = {
    "wti": "DCOILWTICO",     # WTI crude oil spot price, dollars per barrel
    "brent": "DCOILBRENTEU",  # Brent crude (international benchmark), $/barrel
    "dgs2": "DGS2",          # 2-year US Treasury yield, percent
    "dgs10": "DGS10",        # 10-year US Treasury yield, percent
    "fedtarl": "DFEDTARL",   # Fed funds target range, lower bound, percent
    "fedtaru": "DFEDTARU",   # Fed funds target range, upper bound, percent
}

# Weekly series: the national average pump price, surveyed every Monday by
# the Energy Information Administration and republished on FRED.
WEEKLY_SERIES = {
    "gas_retail": "GASREGW",  # Regular gasoline retail price, dollars per gallon
}

OUT_DIR = "data/raw"


def fetch_group(fred, series_map, start):
    """Download one group of series and line them up in a single table.

    Each series arrives as a list of (date, value) pairs. Putting them in one
    DataFrame (a spreadsheet-like table) aligns them by date automatically:
    row 2026-05-01 holds the May 2026 value of every column.
    """
    frames = {}
    for friendly_name, series_id in series_map.items():
        print(f"  {friendly_name:14s} <- {series_id}")
        frames[friendly_name] = fred.get_series(series_id, observation_start=start)
    df = pd.DataFrame(frames)
    df.index.name = "date"
    return df


def main():
    # The API key is read from the environment rather than written in the
    # code, so the script can be shared publicly without sharing the key.
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY not found. Set it as an environment variable before running."
        )
    fred = Fred(api_key=api_key)
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Fetching monthly CPI series...")
    # Important: missing months are kept as blanks, NOT deleted. October 2025
    # CPI was never published, so the table genuinely has a hole there. If
    # that row were deleted, a later step that counts "12 rows back" to
    # compute a 12-month change would silently reach back 13 calendar months
    # and produce wrong numbers. Keeping the blank row preserves the calendar.
    cpi = fetch_group(fred, CPI_SERIES, CPI_START)
    cpi.to_csv(f"{OUT_DIR}/fred_cpi_raw.csv")
    print(f"  saved {len(cpi)} rows, last month {cpi.index[-1].date()}\n")

    print("Fetching monthly labor series...")
    labor = fetch_group(fred, LABOR_SERIES, LABOR_START)
    labor.to_csv(f"{OUT_DIR}/fred_labor_raw.csv")
    print(f"  saved {len(labor)} rows, last month {labor.index[-1].date()}\n")

    print("Fetching daily market series...")
    # Daily series have natural gaps too (weekends, holidays, publication
    # lags), and different series take days off on different dates. Those
    # gaps are also kept as blanks here and handled in the cleaning step.
    daily = fetch_group(fred, DAILY_SERIES, MARKET_START)
    daily.to_csv(f"{OUT_DIR}/fred_daily_raw.csv")
    print(f"  saved {len(daily)} rows, last day {daily.index[-1].date()}\n")

    print("Fetching weekly gasoline series...")
    weekly = fetch_group(fred, WEEKLY_SERIES, MARKET_START)
    weekly.to_csv(f"{OUT_DIR}/fred_weekly_raw.csv")
    print(f"  saved {len(weekly)} rows, last week {weekly.index[-1].date()}")


if __name__ == "__main__":
    main()
