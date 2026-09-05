"""
02_clean_data.py
================
STEP 2 of the data pipeline.

What this script does
---------------------
Turns raw FRED levels into chart-ready monthly changes and percent rates.

Canonical definitions (used by charts and stats; do not re-derive in charts):
- Employment change (thousands of jobs): this month's level minus last month's
  level. PAYEMS is already in thousands, so August 159,075 minus July 158,913
  is +162 thousand jobs.
- Month-over-month (m/m) percent: (this_month / last_month - 1) * 100.
  Used for average hourly earnings, not for payroll counts.
- Year-over-year (y/y) percent: (this_month / month_12_ago - 1) * 100.
  Used for average hourly earnings.

The three-month average of payroll changes is a simple mean of the latest
three monthly job changes. It is not annualized.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"

AUGUST = pd.Timestamp("2026-08-01")

LEVEL_CHANGE_COLS = [
    "payems",
    "uspriv",
    "usgovt",
    "food_services",
    "local_education",
    "construction",
    "manufacturing",
    "information",
    "leisure",
    "healthcare",
    "labor_force",
    "employed",
    "nilf",
    "unemployed",
    "pte_economic",
]


def mom(series: pd.Series) -> pd.Series:
    """Month-over-month percent change from a level.

    Example: hourly earnings $37.65 in July and $37.75 in August is +0.3%.
    fill_method=None means we do not invent values across missing months.
    """
    return series.pct_change(fill_method=None) * 100


def yoy(series: pd.Series) -> pd.Series:
    """Year-over-year percent change: this month versus the same month last year."""
    return series.pct_change(12, fill_method=None) * 100


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    monthly = pd.read_csv(RAW_DIR / "fred_monthly.csv", index_col="date", parse_dates=True)
    monthly.index = monthly.index.to_period("M").to_timestamp()
    monthly = monthly.groupby(monthly.index).last().sort_index()

    weekly = pd.read_csv(RAW_DIR / "fred_weekly.csv", index_col="date", parse_dates=True)
    weekly = weekly.sort_index()

    clean = monthly.copy()
    for col in LEVEL_CHANGE_COLS:
        if col in clean.columns:
            clean[f"{col}_chg"] = monthly[col].diff()

    clean["ahe_mom"] = mom(monthly["ahe"])
    clean["ahe_yoy"] = yoy(monthly["ahe"])
    clean["ahe_prod_mom"] = mom(monthly["ahe_prod"])
    clean["ahe_prod_yoy"] = yoy(monthly["ahe_prod"])
    clean["payroll_3m_avg"] = clean["payems_chg"].rolling(3).mean()
    clean["two_sector_chg"] = clean["food_services_chg"] + clean["local_education_chg"]
    clean["rest_chg"] = clean["payems_chg"] - clean["two_sector_chg"]
    clean["two_sector_share_pct"] = (clean["two_sector_chg"] / clean["payems_chg"]) * 100

    clean.index.name = "date"
    clean.to_csv(CLEAN_DIR / "labor_monthly.csv")

    if AUGUST not in clean.index:
        raise RuntimeError(
            "Clean labor file has no August 2026 row. Re-run 01_fetch_data.py "
            "after FRED carries the BLS print, or add a BLS overlay."
        )

    aug = clean.loc[AUGUST]
    sector_rows = [
        ("Food services", float(aug["food_services_chg"])),
        ("Local gov education", float(aug["local_education_chg"])),
        ("Construction", float(aug["construction_chg"])),
        ("Manufacturing", float(aug["manufacturing_chg"])),
        ("Health care", float(aug["healthcare_chg"])),
        ("Information", float(aug["information_chg"])),
    ]
    listed_sum = sum(change for _, change in sector_rows)
    sector_rows.append(("All other", float(aug["payems_chg"]) - listed_sum))
    sector = pd.DataFrame(sector_rows, columns=["industry", "change_k"])
    sector["change_k"] = sector["change_k"].round(1)
    sector.to_csv(CLEAN_DIR / "sector_august.csv", index=False)

    claims = weekly.rename(columns={"initial_claims": "initial_claims"}).copy()
    claims["claims_4wk_avg"] = claims["initial_claims"].rolling(4).mean()
    claims.index.name = "date"
    claims.to_csv(CLEAN_DIR / "claims_weekly.csv")

    print("Wrote", CLEAN_DIR / "labor_monthly.csv")
    print("Wrote", CLEAN_DIR / "sector_august.csv")
    print("Wrote", CLEAN_DIR / "claims_weekly.csv")
    print(
        "August payroll change (thousands):",
        round(float(aug["payems_chg"]), 1),
    )


if __name__ == "__main__":
    main()
