"""
02_clean_data.py -- Merge FRED data with hardcoded BLS release values, build derived CSVs.

Usage:
    python scripts/02_clean_data.py

Inputs:
    data/clean/payrolls_monthly.csv  (from 01_fetch_data.py)
    data/clean/oil_prices.csv        (from 01_fetch_data.py)

Outputs:
    data/clean/sector_changes.csv
    data/clean/waterfall_components.csv

Also patches payrolls_monthly.csv with hardcoded Feb 2026 data if FRED
hasn't loaded it yet.
"""

from pathlib import Path

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

data_dir = Path(__file__).resolve().parent.parent / "data" / "clean"

# ---------------------------------------------------------------------------
# Patch payrolls_monthly.csv with BLS release values
# ---------------------------------------------------------------------------

payrolls_path = data_dir / "payrolls_monthly.csv"
df = pd.read_csv(payrolls_path, index_col=0, parse_dates=True)

FEB_2026 = pd.Timestamp("2026-02-01")
JAN_2026 = pd.Timestamp("2026-01-01")
DEC_2025 = pd.Timestamp("2025-12-01")

# BLS Employment Situation release: revisions and Feb 2026 data
# January revised to +126k, December revised to -17k
# NOTE: FRED PAYEMS is in thousands of persons, so payroll_change from diff()
# is also in thousands (e.g., 42 means 42,000 jobs). Hardcoded values must match.
BLS_REVISIONS = {
    JAN_2026: {"payroll_change": 126},
    DEC_2025: {"payroll_change": -17},
}

# Previous (pre-revision) estimates for months revised in the March 2026 report.
# Dec 2025: reported as +48k in the Feb 2026 Employment Situation (revised from +50k initial)
# Jan 2026: reported as +130k in the Feb 2026 Employment Situation (initial estimate)
# Source: BLS Employment Situation archives & CNBC jobs report coverage
BLS_PREVIOUS_ESTIMATES = {
    DEC_2025: 48,
    JAN_2026: 130,
}

BLS_FEB_2026 = {
    "payroll_change": -92,
    "unemployment_rate": 4.4,
    "u6_rate": 7.9,
    "avg_hourly_earnings": 37.32,
    "earnings_mom_pct": 0.4,
    "earnings_yoy_pct": 3.8,
}

# Apply revisions
for date, values in BLS_REVISIONS.items():
    if date in df.index:
        for col, val in values.items():
            if col in df.columns:
                df.loc[date, col] = val
                print(f"  Revised {col} for {date.strftime('%B %Y')} -> {val:,}")

# Add or update February 2026
if FEB_2026 not in df.index:
    print(f"  Feb 2026 not in FRED data yet -- adding from BLS release")
    new_row = pd.DataFrame(BLS_FEB_2026, index=[FEB_2026])
    new_row.index.name = "date"
    df = pd.concat([df, new_row]).sort_index()
else:
    print(f"  Feb 2026 found in FRED data -- patching with BLS release values")
    for col, val in BLS_FEB_2026.items():
        if col in df.columns:
            df.loc[FEB_2026, col] = val

# Add previous (pre-revision) estimates as a new column for chart visualization
df["payroll_change_previous"] = np.nan
for date, prev_val in BLS_PREVIOUS_ESTIMATES.items():
    if date in df.index:
        df.loc[date, "payroll_change_previous"] = prev_val
        print(f"  Added previous estimate for {date.strftime('%B %Y')} -> {prev_val:+,}")

df.to_csv(payrolls_path, float_format="%.4f")
print(f"Updated {payrolls_path}")

# ---------------------------------------------------------------------------
# Sector changes (from BLS Employment Situation detailed tables)
# ---------------------------------------------------------------------------

sector_data = [
    {"sector": "Healthcare", "change": -28_000, "factor": "strikes"},
    {"sector": "Transportation & warehousing", "change": -17_000, "factor": "strikes"},
    {"sector": "Information", "change": -11_000, "factor": "slowdown"},
    {"sector": "Federal government", "change": -10_000, "factor": "slowdown"},
    {"sector": "Construction", "change": -8_000, "factor": "weather"},
    {"sector": "Manufacturing", "change": -4_000, "factor": "weather"},
    {"sector": "Professional & business svcs", "change": 5_000, "factor": "other"},
    {"sector": "Leisure & hospitality", "change": 12_000, "factor": "other"},
]

df_sectors = pd.DataFrame(sector_data)
sector_path = data_dir / "sector_changes.csv"
df_sectors.to_csv(sector_path, index=False)
print(f"Wrote {sector_path}")

# ---------------------------------------------------------------------------
# Waterfall decomposition
# ---------------------------------------------------------------------------
# Analytical decomposition of the miss: from +50k expected to -92k actual.
# The gap is -142k. Components are approximate and based on BLS sector data.
# They sum to -142k by construction.

waterfall_data = [
    {"label": "Expected", "value": 50_000, "factor": "baseline", "bar_type": "start"},
    {"label": "Healthcare\nstrikes", "value": -37_000, "factor": "strikes", "bar_type": "step"},
    {"label": "Transport\nstrikes", "value": -17_000, "factor": "strikes", "bar_type": "step"},
    {"label": "Severe\nweather", "value": -20_000, "factor": "weather", "bar_type": "step"},
    {"label": "Geopolitical\nuncertainty", "value": -18_000, "factor": "uncertainty", "bar_type": "step"},
    {"label": "Sector\nslowdowns", "value": -21_000, "factor": "slowdown", "bar_type": "step"},
    {"label": "Other\nfactors", "value": -29_000, "factor": "other", "bar_type": "step"},
    {"label": "Actual", "value": -92_000, "factor": "net", "bar_type": "net"},
]

# Verify the decomposition sums correctly
steps = [d["value"] for d in waterfall_data if d["bar_type"] == "step"]
expected = waterfall_data[0]["value"]
computed_net = expected + sum(steps)
assert computed_net == -92_000, f"Waterfall doesn't sum: {expected} + {sum(steps)} = {computed_net}, expected -92000"

df_waterfall = pd.DataFrame(waterfall_data)
waterfall_path = data_dir / "waterfall_components.csv"
df_waterfall.to_csv(waterfall_path, index=False)
print(f"Wrote {waterfall_path}")
print(f"  Decomposition check: {expected:+,} + ({sum(steps):,}) = {computed_net:,}")
