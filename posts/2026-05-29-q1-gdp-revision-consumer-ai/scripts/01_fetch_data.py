"""
01_fetch_data.py
----------------
Fetch GDP, investment, inflation, and labor market series from FRED
and save them to data/raw/.

FRED is a public data service run by the St. Louis Fed. This script requires
a free API key: https://fred.stlouisfed.org/docs/api/api_key.html

Before running, set your API key as an environment variable:
    Windows:   set FRED_API_KEY=your_key_here
    PowerShell: $env:FRED_API_KEY="your_key_here"
    Mac/Linux: export FRED_API_KEY=your_key_here

Run from the post folder:
    python scripts/01_fetch_data.py
"""

import os

import pandas as pd
from fredapi import Fred


# Quarterly GDP/investment series go back to 2001 so the expansion
# comparison chart can cover dot-com, GFC, and COVID recoveries.
QUARTERLY_START = "2001-01-01"
QUARTERLY_END = "2026-06-01"

# Monthly inflation/labor series only need recent history for context charts.
MONTHLY_START = "2022-01-01"
MONTHLY_END = "2026-06-01"

# Group A: Quarterly GDP, investment, and PCE series
QUARTERLY_SERIES = {
    "gdp_growth":           "A191RL1Q225SBEA",   # Real GDP pct change, SAAR
    "real_gdp_level":       "GDPC1",              # Real GDP level (chained 2017$)
    "pce_contribution":     "A014RE1Q156NBEA",    # PCE contribution to GDP (pp)
    "gpdi_contribution":    "A006RE1Q156NBEA",    # Gross private domestic investment (pp)
    "govt_contribution":    "A822RE1Q156NBEA",    # Government contribution (pp)
    "netex_contribution":   "A019RE1Q156NBEA",    # Net exports contribution (pp)
    "real_pce":             "PCEC96",              # Real PCE (chained 2017$)
    "pce_durable":          "PCEDG",               # PCE durable goods
    "pce_nondurable":       "PCEND",               # PCE nondurable goods
    "pce_services":         "PCESV",               # PCE services
    "nres_equipment":       "Y033RC1Q027SBEA",     # Nonresidential equipment
    "pnfi":                 "PNFI",                # Private nonresidential fixed investment
    "gdp_deflator":         "GDPDEF",              # GDP implicit price deflator (index)
}

# Group B: Monthly inflation and labor market series
MONTHLY_SERIES = {
    "pce_price_index":      "PCEPI",       # PCE price index
    "core_pce":             "PCEPILFE",    # Core PCE price index
    "unrate":               "UNRATE",      # Unemployment rate
    "payems":               "PAYEMS",      # Nonfarm payrolls (thousands)
    "productivity":         "OPHNFB",      # Output per hour, nonfarm business
    "consumer_sentiment":   "UMCSENT",     # Michigan consumer sentiment
}

QUARTERLY_OUT = "data/raw/fred_quarterly.csv"
MONTHLY_OUT = "data/raw/fred_monthly.csv"


def fetch_group(fred, series_dict, start, end, label):
    """Fetch a group of FRED series and return a combined DataFrame."""
    print(f"\nFetching {len(series_dict)} {label} series ({start} to {end})...\n")
    frames = {}
    for friendly_name, series_id in series_dict.items():
        try:
            data = fred.get_series(
                series_id,
                observation_start=start,
                observation_end=end,
            )
            frames[friendly_name] = data
            print(f"  {friendly_name:22s} <- {series_id}  ({len(data)} obs)")
        except Exception as e:
            print(f"  WARNING: could not fetch {friendly_name} ({series_id}): {e}")

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

    # Fetch quarterly series
    df_q = fetch_group(fred, QUARTERLY_SERIES, QUARTERLY_START, QUARTERLY_END, "quarterly")
    os.makedirs("data/raw", exist_ok=True)
    df_q.to_csv(QUARTERLY_OUT)
    print(f"\nSaved {len(df_q)} quarterly rows to {QUARTERLY_OUT}")

    # Fetch monthly series
    df_m = fetch_group(fred, MONTHLY_SERIES, MONTHLY_START, MONTHLY_END, "monthly")
    df_m.to_csv(MONTHLY_OUT)
    print(f"Saved {len(df_m)} monthly rows to {MONTHLY_OUT}")

    print("\nLast 3 quarterly rows:")
    print(df_q.tail(3).to_string())
    print("\nLast 3 monthly rows:")
    print(df_m.tail(3).to_string())


if __name__ == "__main__":
    main()
