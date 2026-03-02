"""
02_compute_stats.py — Compute summary statistics for the CPI/PPI divergence post.

Combines FRED-fetched data with hardcoded values from BLS detailed release tables
(component-level PPI data not available via FRED).

Usage:
    python scripts/02_compute_stats.py

Outputs:
    stats/summary_stats.json
"""

import json
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Load FRED data
# ---------------------------------------------------------------------------

data_dir = Path(__file__).resolve().parent.parent / "data" / "clean"
stats_dir = Path(__file__).resolve().parent.parent / "stats"
stats_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(data_dir / "cpi_ppi_monthly.csv", index_col=0, parse_dates=True)

# Latest month in data (should be January 2026)
latest = df.index[-1]
prev = df.index[-2]

latest_label = latest.strftime("%B %Y")
prev_label = prev.strftime("%B %Y")

# ---------------------------------------------------------------------------
# Extract key values from FRED data
# ---------------------------------------------------------------------------

def safe_get(col, idx):
    """Get value from df, return None if missing."""
    try:
        return round(float(df.loc[idx, col]), 1)
    except (KeyError, TypeError):
        return None

stats = {
    # Dates
    "latest_month": latest_label,
    "prev_month": prev_label,
    "data_current_as_of": "February 27, 2026 (January 2026 PPI release)",
    "cpi_release_date": "February 13, 2026",
    "ppi_release_date": "February 27, 2026",
    "next_cpi_date": "March 11, 2026",
    "next_ppi_date": "March 18, 2026",

    # CPI readings (from FRED where available, BLS release as fallback)
    "cpi_headline_mom": safe_get("cpi_all_mom", latest) or 0.2,
    "cpi_headline_mom_expected": 0.3,
    "cpi_core_mom": safe_get("cpi_core_mom", latest) or 0.3,
    "cpi_headline_yoy": safe_get("cpi_all_yoy", latest) or 2.4,
    "cpi_core_yoy": safe_get("cpi_core_yoy", latest) or 2.5,

    # PPI readings (from FRED where available, BLS release as fallback)
    "ppi_headline_mom": 0.5,
    "ppi_headline_mom_expected": 0.3,
    "ppi_core_services_mom": 0.8,
    # Note: WPSFD4111 is a goods measure, not the services measure we need.
    # The BLS "final demand services less food, energy, trade" isn't a clean FRED series.
    # Use the BLS release value directly.
    "ppi_core_yoy": 3.6,
    "ppi_services_mom_fred": safe_get("ppi_final_demand_mom", latest),
    "ppi_core_mom_fred": safe_get("ppi_core_mom", latest),

    # Component-level data (hardcoded from BLS detailed tables — not in FRED)
    "ppi_trade_services_mom": 2.5,
    "ppi_equip_wholesale_mom": 14.4,
    "ppi_equip_contribution_pct": 20,

    # Other
    "gasoline_mom": -3.2,

    # Market reactions (from financial reporting)
    "dow_drop_pts": 700,
    "june_cut_odds_pre": "60-70",
    "treasury_2y_spike_bps": 10,

    # Derived
    "ppi_core_services_annualized": round(((1 + 0.8/100) ** 12 - 1) * 100, 1),

    # Wage data
    "nominal_wage_growth_yoy": "3.5-4",
}

# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------

out_path = stats_dir / "summary_stats.json"
with open(out_path, "w") as f:
    json.dump(stats, f, indent=2)

print(f"Wrote {out_path}")
print(f"Latest month: {latest_label}")
print(f"Keys: {len(stats)}")
