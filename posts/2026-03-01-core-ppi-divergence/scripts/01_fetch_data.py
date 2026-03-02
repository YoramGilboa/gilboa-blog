"""
01_fetch_data.py — Fetch CPI and PPI series from FRED for the CPI/PPI divergence post.

Usage:
    export FRED_API_KEY=your_key_here
    python scripts/01_fetch_data.py

Outputs:
    data/clean/cpi_ppi_monthly.csv
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

# Series IDs
SERIES = {
    "cpi_all":          "CPIAUCSL",     # CPI-U All Items, SA
    "cpi_core":         "CPILFESL",     # CPI-U Less Food & Energy, SA
    "ppi_final_demand": "PPIFIS",       # PPI Final Demand Services, SA
    "ppi_core":         "WPSFD4111",    # PPI Final Demand less food, energy, trade services, SA
}

START_DATE = "2024-06-01"

# ---------------------------------------------------------------------------
# Fetch
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

# Combine into a single DataFrame
df = pd.DataFrame(frames)
df.index.name = "date"

# Compute month-over-month percent changes
df_mom = df.pct_change() * 100
df_mom.columns = [f"{c}_mom" for c in df_mom.columns]

# Compute year-over-year percent changes
df_yoy = df.pct_change(12) * 100
df_yoy.columns = [f"{c}_yoy" for c in df_yoy.columns]

# Merge levels, m/m, and y/y
result = pd.concat([df, df_mom, df_yoy], axis=1).dropna(how="all")

out_path = output_dir / "cpi_ppi_monthly.csv"
result.to_csv(out_path, float_format="%.4f")
print(f"Wrote {out_path} ({len(result)} rows)")
