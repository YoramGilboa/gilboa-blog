"""
01_fetch_data.py
----------------
Step 1 of the pipeline: download every FRED series this post uses.

Outputs CSVs under data/raw/, one per group. Later scripts read from those
files rather than the internet so downstream numbers are reproducible.

Set the FRED API key before running:
    PowerShell: $env:FRED_API_KEY="your_key_here"
    Bash:       export FRED_API_KEY=your_key_here

Run from the post folder:
    python scripts/01_fetch_data.py
"""

import os

import pandas as pd
from fredapi import Fred

# ---------------------------------------------------------------------------
# Series groups. Friendly names on the left, FRED IDs on the right.
# ---------------------------------------------------------------------------

CPI_START = "2018-01-01"
CPI_SERIES = {
    "headline_cpi": "CPIAUCSL",   # CPI all items, SA
    "core_cpi":     "CPILFESL",   # CPI ex food and energy, SA
    "energy_cpi":   "CPIENGSL",   # CPI energy, SA
    "headline_pce": "PCEPI",      # PCE price index, SA
    "core_pce":     "PCEPILFE",   # Core PCE price index, SA
}

LABOR_START = "2018-01-01"
LABOR_SERIES = {
    "payems":  "PAYEMS",   # Total nonfarm payrolls, thousands
    "unrate":  "UNRATE",   # Civilian unemployment rate, %
    "civpart": "CIVPART",  # Labor force participation, %
}

CLAIMS_SERIES = {
    "icsa": "ICSA",        # Initial unemployment claims, weekly
}

RATES_START = "2018-01-01"
RATES_SERIES = {
    "fedfunds":  "FEDFUNDS",   # Effective fed funds rate, monthly avg
    "dfedtarl":  "DFEDTARL",   # Target range lower bound, daily
    "dfedtaru":  "DFEDTARU",   # Target range upper bound, daily
    "dgs1":      "DGS1",       # 1-year Treasury constant maturity, daily
    "dgs2":      "DGS2",       # 2-year Treasury, daily
    "dgs10":     "DGS10",      # 10-year Treasury, daily
}

OUT_DIR = "data/raw"


def fetch_group(fred, series_map, start):
    """Download one group of series and align them by date."""
    frames = {}
    for name, sid in series_map.items():
        print(f"  {name:14s} <- {sid}")
        frames[name] = fred.get_series(sid, observation_start=start)
    df = pd.DataFrame(frames)
    df.index.name = "date"
    return df


def main():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY not found. Set it as an environment variable before running."
        )
    fred = Fred(api_key=api_key)
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Fetching monthly inflation series...")
    cpi = fetch_group(fred, CPI_SERIES, CPI_START)
    cpi.to_csv(f"{OUT_DIR}/fred_inflation_raw.csv")
    print(f"  saved {len(cpi)} rows, last month {cpi.index[-1].date()}\n")

    print("Fetching monthly labor series...")
    labor = fetch_group(fred, LABOR_SERIES, LABOR_START)
    labor.to_csv(f"{OUT_DIR}/fred_labor_raw.csv")
    print(f"  saved {len(labor)} rows, last month {labor.index[-1].date()}\n")

    print("Fetching weekly initial claims...")
    claims = fetch_group(fred, CLAIMS_SERIES, "2020-01-01")
    claims.to_csv(f"{OUT_DIR}/fred_claims_raw.csv")
    print(f"  saved {len(claims)} rows, last week {claims.index[-1].date()}\n")

    print("Fetching daily rates series...")
    rates = fetch_group(fred, RATES_SERIES, RATES_START)
    rates.to_csv(f"{OUT_DIR}/fred_rates_raw.csv")
    print(f"  saved {len(rates)} rows, last day {rates.index[-1].date()}")


if __name__ == "__main__":
    main()
