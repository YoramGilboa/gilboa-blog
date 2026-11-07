"""
02_clean_data.py
================
STEP 2 of the data pipeline.

What this script does
---------------------
Turns the committed FRED levels into chart-ready changes and percent rates.

Canonical definitions (charts plot these columns; they do not re-derive them):
- Employment change, thousands of jobs: this month's level minus last month's
  level. PAYEMS is already in thousands, so an October level 165 above
  September is +165 thousand jobs.
- Month-over-month percent: (this month / last month - 1) * 100.
  Used for average hourly earnings. Not used for payroll counts.
- Year-over-year percent: (this month / same month a year earlier - 1) * 100.
  Used for average hourly earnings.

A blank FRED month stays blank. diff() and pct_change(fill_method=None) do
not invent a value across a hole, and this script does not drop those rows.
October 2025 is missing on the household survey. JOLTS has no October 2026
row because that survey ends in September.

The published Employment Situation changes are checked in 04. When a FRED
level difference disagrees with the news release, 04 keeps the news release.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"

OCTOBER = pd.Timestamp("2026-10-01")
SEPTEMBER = pd.Timestamp("2026-09-01")

LEVEL_CHANGE_COLS = [
    "payems",
    "uspriv",
    "usgovt",
    "professional",
    "healthcare",
    "manufacturing",
    "construction",
    "information",
    "financial",
    "leisure",
    "temp_help",
    "labor_force",
    "employed",
    "unemployed",
    "pte_economic",
    "long_term_unemployed",
]


def mom(series: pd.Series) -> pd.Series:
    """Month-over-month percent change from a level.

    Example: hourly earnings of $37.86 then $38.00 is about +0.4 percent.
    """
    return series.pct_change(fill_method=None) * 100


def yoy(series: pd.Series) -> pd.Series:
    """Year-over-year percent change: this month versus the same month last year."""
    return series.pct_change(12, fill_method=None) * 100


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, lineterminator="\n")


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    monthly = pd.read_csv(RAW_DIR / "fred_monthly.csv", index_col="date", parse_dates=True)
    monthly.index = monthly.index.to_period("M").to_timestamp()
    monthly = monthly.groupby(monthly.index).last().sort_index()
    weekly = pd.read_csv(RAW_DIR / "fred_weekly.csv", index_col="date", parse_dates=True).sort_index()

    if OCTOBER not in monthly.index or SEPTEMBER not in monthly.index:
        raise RuntimeError("The committed snapshot has no October or September 2026 row.")

    clean = monthly.copy()
    for col in LEVEL_CHANGE_COLS:
        clean[f"{col}_chg"] = monthly[col].diff()
    clean["ahe_mom"] = mom(monthly["ahe"])
    clean["ahe_yoy"] = yoy(monthly["ahe"])
    clean["ahe_prod_mom"] = mom(monthly["ahe_prod"])
    clean["ahe_prod_yoy"] = yoy(monthly["ahe_prod"])
    # Three current-vintage changes. This is not the October 2 average.
    clean["payroll_3m_avg"] = clean["payems_chg"].rolling(3, min_periods=3).mean()
    clean.index.name = "date"
    write_csv(clean, CLEAN_DIR / "labor_monthly.csv")

    earnings = clean.loc[:, ["ahe", "ahe_mom", "ahe_yoy"]].copy()
    earnings.index.name = "date"
    write_csv(earnings, CLEAN_DIR / "earnings.csv")

    jolts = clean.loc[:SEPTEMBER, ["jolts_openings_rate", "jolts_quits_rate"]].copy()
    jolts.index.name = "date"
    write_csv(jolts, CLEAN_DIR / "jolts_rates.csv")

    claims = weekly.copy()
    claims.index.name = "date"
    write_csv(claims, CLEAN_DIR / "claims_weekly.csv")

    oct_change = float(clean.loc[OCTOBER, "payems_chg"])
    print("Wrote", CLEAN_DIR / "labor_monthly.csv")
    print("Wrote", CLEAN_DIR / "earnings.csv")
    print("Wrote", CLEAN_DIR / "jolts_rates.csv")
    print("Wrote", CLEAN_DIR / "claims_weekly.csv")
    print("October payroll change from levels (thousands):", round(oct_change, 1))


if __name__ == "__main__":
    main()
