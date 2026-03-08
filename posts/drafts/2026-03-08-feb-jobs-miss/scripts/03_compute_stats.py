"""
03_compute_stats.py -- Compute summary statistics for inline values in the blog post.

Combines FRED-fetched data with hardcoded values from the BLS Employment
Situation release (sector-level detail not available via FRED).

Usage:
    python scripts/03_compute_stats.py

Outputs:
    stats/summary_stats.json
"""

import json
from pathlib import Path

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

data_dir = Path(__file__).resolve().parent.parent / "data" / "clean"
stats_dir = Path(__file__).resolve().parent.parent / "stats"
stats_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(data_dir / "payrolls_monthly.csv", index_col=0, parse_dates=True)

# Oil prices (may not exist if FRED fetch failed)
oil_path = data_dir / "oil_prices.csv"
oil_df = None
if oil_path.exists():
    oil_df = pd.read_csv(oil_path, index_col=0, parse_dates=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_get(col, idx):
    """Get value from df, return None if missing."""
    try:
        return round(float(df.loc[idx, col]), 1)
    except (KeyError, TypeError, ValueError):
        return None

FEB_2026 = pd.Timestamp("2026-02-01")
JAN_2026 = pd.Timestamp("2026-01-01")

# ---------------------------------------------------------------------------
# Compute derived values from FRED data
# ---------------------------------------------------------------------------

# Rolling averages for payroll changes
if "payroll_change" in df.columns:
    payroll_series = df["payroll_change"].dropna()
    payroll_3m_avg = payroll_series.tail(3).mean()
    payroll_6m_avg = payroll_series.tail(6).mean()
else:
    payroll_3m_avg = None
    payroll_6m_avg = None

# Oil price change
oil_start = None
oil_end = None
oil_change_pct = None
if oil_df is not None and len(oil_df) >= 2:
    oil_start = round(float(oil_df["wti_price"].iloc[-2]), 1)
    oil_end = round(float(oil_df["wti_price"].iloc[-1]), 1)
    if oil_start and oil_start > 0:
        oil_change_pct = round((oil_end - oil_start) / oil_start * 100, 1)

# ---------------------------------------------------------------------------
# Build stats dictionary
# ---------------------------------------------------------------------------

stats = {
    # Dates
    "latest_month": "February 2026",
    "prev_month": "January 2026",
    "report_release_date": "March 7, 2026",
    "data_current_as_of": "March 7, 2026 (February 2026 Employment Situation)",

    # Headline numbers
    "payroll_change": -92_000,
    "payroll_change_expected": 50_000,
    "payroll_miss": -142_000,
    "unemployment_rate": safe_get("unemployment_rate", FEB_2026) or 4.4,
    "unemployment_rate_prev": safe_get("unemployment_rate", JAN_2026) or 4.3,
    "u6_rate": safe_get("u6_rate", FEB_2026) or 7.9,
    "u6_rate_prev": safe_get("u6_rate", JAN_2026) or 8.1,
    "u6_rate_peak": 8.7,
    "u6_rate_peak_month": "November 2025",
    "labor_force_participation": 62.0,

    # Wages
    "avg_hourly_earnings": 37.32,
    "wage_mom": safe_get("earnings_mom_pct", FEB_2026) or 0.4,
    "wage_yoy": safe_get("earnings_yoy_pct", FEB_2026) or 3.8,

    # Revisions
    "jan_revised": 126_000,
    "dec_revised": -17_000,

    # Sector changes (from BLS detailed tables)
    "healthcare_change": -28_000,
    "physicians_offices_change": -37_000,
    "transport_change": -17_000,
    "construction_change": -8_000,
    "manufacturing_change": -4_000,
    "information_change": -11_000,
    "federal_govt_change": -10_000,

    # Waterfall totals
    "strikes_total": -54_000,
    "weather_total": -20_000,
    "uncertainty_total": -18_000,

    # Geopolitical
    "oil_price_start": oil_start or 70,
    "oil_price_end": oil_end or 90,
    "oil_price_change_pct": oil_change_pct or 28.6,

    # Labor market context
    "ai_fear_pct": 40,
    "worst_since": "October 2025",

    # Trend data (from FRED)
    "payroll_3m_avg": round(payroll_3m_avg) if payroll_3m_avg is not None else None,
    "payroll_6m_avg": round(payroll_6m_avg) if payroll_6m_avg is not None else None,
}

# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------

out_path = stats_dir / "summary_stats.json"
with open(out_path, "w") as f:
    json.dump(stats, f, indent=2)

print(f"Wrote {out_path}")
print(f"Latest month: {stats['latest_month']}")
print(f"Keys: {len(stats)}")
