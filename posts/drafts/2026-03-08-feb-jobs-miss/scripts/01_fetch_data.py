"""
01_fetch_data.py -- Fetch payroll, unemployment, wage, and oil data from FRED.

Usage:
    export FRED_API_KEY=your_key_here
    python scripts/01_fetch_data.py

Outputs:
    data/clean/payrolls_monthly.csv
    data/clean/oil_prices.csv
"""

import os
import sys
from pathlib import Path

import pandas as pd
from fredapi import Fred

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("FRED_API_KEY")
if not API_KEY:
    print("Error: set FRED_API_KEY environment variable.")
    sys.exit(1)

fred = Fred(api_key=API_KEY)

SERIES = {
    "nonfarm_payrolls": "PAYEMS",
    "unemployment_rate": "UNRATE",
    "u6_rate": "U6RATE",
    "avg_hourly_earnings": "CES0500000003",
}

START_DATE = "2025-01-01"

# ---------------------------------------------------------------------------
# Fetch payroll and labor market series
# ---------------------------------------------------------------------------

output_dir = Path(__file__).resolve().parent.parent / "data" / "clean"
output_dir.mkdir(parents=True, exist_ok=True)

frames = {}
for name, series_id in SERIES.items():
    print(f"Fetching {name} ({series_id})...")
    try:
        s = fred.get_series(series_id, observation_start=START_DATE)
        s.name = name
        frames[name] = s
    except Exception as e:
        print(f"  Warning: could not fetch {series_id}: {e}")

df = pd.DataFrame(frames)
df.index.name = "date"

# Compute month-over-month absolute change for payrolls (thousands)
if "nonfarm_payrolls" in df.columns:
    df["payroll_change"] = df["nonfarm_payrolls"].diff()

# Compute month-over-month percent change for earnings
if "avg_hourly_earnings" in df.columns:
    df["earnings_mom_pct"] = df["avg_hourly_earnings"].pct_change() * 100
    df["earnings_yoy_pct"] = df["avg_hourly_earnings"].pct_change(12) * 100

out_path = output_dir / "payrolls_monthly.csv"
df.to_csv(out_path, float_format="%.4f")
print(f"Wrote {out_path} ({len(df)} rows)")

# ---------------------------------------------------------------------------
# Fetch oil prices (WTI crude)
# ---------------------------------------------------------------------------

print("Fetching DCOILWTICO (WTI crude oil)...")
try:
    oil = fred.get_series("DCOILWTICO", observation_start=START_DATE)
    oil_monthly = oil.resample("MS").mean()
    oil_monthly.name = "wti_price"
    oil_df = oil_monthly.to_frame()
    oil_df.index.name = "date"

    oil_path = output_dir / "oil_prices.csv"
    oil_df.to_csv(oil_path, float_format="%.2f")
    print(f"Wrote {oil_path} ({len(oil_df)} rows)")
except Exception as e:
    print(f"  Warning: could not fetch oil prices: {e}")
    print("  Oil price chart will use hardcoded values in 02_clean_data.py")
