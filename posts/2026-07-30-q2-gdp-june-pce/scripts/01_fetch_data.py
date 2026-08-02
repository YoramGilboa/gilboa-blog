"""
01_fetch_data.py
================
STEP 1 of 3 in the data pipeline.

What this script does (beginner version)
----------------------------------------
1. Connects to FRED (Federal Reserve Economic Data), a free public database.
2. Downloads a small set of economic time series (GDP, investment, PCE prices, etc.).
3. Saves the raw downloads as CSV files under data/raw/.

Nothing is cleaned or calculated here. That is step 2 (02_clean_data.py).
Summary numbers for the blog prose are step 3 (04_compute_stats.py).

Pipeline order
--------------
    python scripts/01_fetch_data.py   # you are here: download
    python scripts/02_clean_data.py   # next: compute growth rates
    python scripts/04_compute_stats.py  # then: build stats JSON for the post

FRED API key (required)
-----------------------
Get a free key: https://fred.stlouisfed.org/docs/api/api_key.html

Set it before running:
    PowerShell:  $env:FRED_API_KEY="your_key_here"
    Mac/Linux:   export FRED_API_KEY=your_key_here

Run from the post folder (not the repo root):
    python scripts/01_fetch_data.py

Outputs
-------
    data/raw/fred_quarterly.csv  - one column per quarterly series
    data/raw/fred_monthly.csv    - one column per monthly series

Each CSV has a date index and the friendly column names defined below.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
from fredapi import Fred

# Paths are relative to this post folder so the script works no matter where
# the repo is cloned.
POST_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = POST_DIR / "data" / "raw"

# How far back to download. Quarterly charts need a longer history than
# monthly inflation panels.
QUARTERLY_START = "2005-01-01"
QUARTERLY_END = "2026-09-01"
MONTHLY_START = "2018-01-01"
MONTHLY_END = "2026-09-01"

# ---------------------------------------------------------------------------
# Friendly name -> FRED series ID
#
# FRED uses short IDs (like GDPC1). We rename them to readable column names
# so later scripts never need to remember the raw codes.
#
# IMPORTANT: keep quarterly series and monthly series in separate groups.
# Mixing them in one DataFrame forces a monthly index and breaks quarterly charts.
# ---------------------------------------------------------------------------
QUARTERLY_SERIES = {
    # Real GDP growth rate, already published as SAAR percent change.
    "gdp_growth": "A191RL1Q225SBEA",
    # Real GDP level in chained dollars (used if we need level-based calcs).
    "real_gdp_level": "GDPC1",
    # These contribution IDs are fetched for history/context; the post's Q2
    # contribution snapshot is also written manually from the BEA release
    # in 02/04 because FRED can lag on advance-day detail.
    "pce_contribution": "A014RE1Q156NBEA",
    "gpdi_contribution": "A006RE1Q156NBEA",
    "govt_contribution": "A822RE1Q156NBEA",
    "netex_contribution": "A019RE1Q156NBEA",
    # Nonresidential equipment spending (servers, machines, etc.).
    "nres_equipment": "Y033RC1Q027SBEA",
    # Private nonresidential fixed investment (broader business capex).
    "pnfi": "PNFI",
    # GDP price index (level); growth is computed in 02 if needed.
    "gdp_deflator": "GDPDEF",
}

MONTHLY_SERIES = {
    # Real consumer spending level (inflation-adjusted dollars).
    "real_pce": "PCEC96",
    # Headline PCE price index (includes food and energy).
    "pce_price_index": "PCEPI",
    # Core PCE price index (excludes food and energy) - Fed's preferred gauge.
    "core_pce": "PCEPILFE",
    # Real disposable personal income.
    "real_dpi": "DSPIC96",
    # Personal saving as a percent of disposable income.
    "saving_rate": "PSAVERT",
    # Unemployment rate (context; not a main chart in this post).
    "unrate": "UNRATE",
    # Nonfarm payrolls in thousands of jobs.
    "payems": "PAYEMS",
}


def fetch_group(
    fred: Fred,
    series_dict: dict[str, str],
    start: str,
    end: str,
    label: str,
) -> pd.DataFrame:
    """
    Download every series in series_dict and glue them into one wide table.

    Parameters
    ----------
    fred : Fred
        Authenticated FRED client.
    series_dict : dict
        Keys = friendly column names, values = FRED series IDs.
    start, end : str
        Inclusive date window (YYYY-MM-DD).
    label : str
        Only used for console progress messages ("quarterly" / "monthly").

    Returns
    -------
    DataFrame with DatetimeIndex named "date" and one column per series.
    """
    print(f"\nFetching {len(series_dict)} {label} series ({start} to {end})...\n")
    frames: dict[str, pd.Series] = {}

    for friendly_name, series_id in series_dict.items():
        # FRED sometimes rate-limits; retry a few times with a short wait.
        for attempt in range(3):
            try:
                data = fred.get_series(
                    series_id,
                    observation_start=start,
                    observation_end=end,
                )
                frames[friendly_name] = data
                print(f"  {friendly_name:22s} <- {series_id}  ({len(data)} obs)")
                break
            except Exception as exc:  # noqa: BLE001 - surface fetch failures clearly
                if "Rate Limit" in str(exc) and attempt < 2:
                    wait = 10 * (attempt + 1)
                    print(f"  {friendly_name:22s} <- rate limited, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(
                        f"Could not fetch {friendly_name} ({series_id}): {exc}"
                    ) from exc
        # Small pause between series to stay polite to the API.
        time.sleep(0.4)

    df = pd.DataFrame(frames)
    df.index.name = "date"
    return df


def main() -> None:
    """Entry point: authenticate, fetch both groups, write CSVs."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY not found. Set it as an environment variable before running."
        )

    # Create data/raw/ if this is the first run on a fresh checkout.
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)

    quarterly = fetch_group(
        fred, QUARTERLY_SERIES, QUARTERLY_START, QUARTERLY_END, "quarterly"
    )
    monthly = fetch_group(
        fred, MONTHLY_SERIES, MONTHLY_START, MONTHLY_END, "monthly"
    )

    q_path = RAW_DIR / "fred_quarterly.csv"
    m_path = RAW_DIR / "fred_monthly.csv"
    quarterly.to_csv(q_path)
    monthly.to_csv(m_path)

    print(f"\nSaved {q_path}  shape={quarterly.shape}")
    print(f"Saved {m_path}  shape={monthly.shape}")
    print("\nDone. Next: python scripts/02_clean_data.py")


if __name__ == "__main__":
    main()
