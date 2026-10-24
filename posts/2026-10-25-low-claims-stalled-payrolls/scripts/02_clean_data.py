"""
02_clean_data.py
================
STEP 2 of the data pipeline.

Reads data/raw/fred_weekly.csv and data/raw/fred_monthly.csv.
Writes chart-ready files under data/clean/. Does not download.

Canonical definitions (charts plot these columns; they do not recompute them)
--------------------------------------------------------------------------------
Monthly change, payrolls
    payems_change = this month's PAYEMS level minus the previous month's level.
    PAYEMS is already in thousands of jobs, so a value of 29 means 29,000 jobs.
    This is a difference of levels, not a percent.

Year rate, average hourly earnings
    ahe_yoy = (this month / the same month a year earlier - 1) * 100.
    A year rate compares a month with the same month one year earlier.
    It is not a monthly percent, and this post does not print the wage index level.

Three-month average, payrolls
    payems_change_3m = the arithmetic mean of the last three monthly changes,
    including the current month. It is in thousands of jobs.
    It is not annualized. This post does not use a 3-month annualized rate.

Weekly claims stay in persons. A missing week stays missing. This script does
not drop rows to close a gap, and it does not average weekly claims onto months.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    weekly = pd.read_csv(RAW_DIR / "fred_weekly.csv", index_col="date", parse_dates=True).sort_index()
    monthly = pd.read_csv(RAW_DIR / "fred_monthly.csv", index_col="date", parse_dates=True).sort_index()

    claims = pd.DataFrame(
        {
            "initial_claims": weekly["initial_claims"],
            "claims_4wk_avg": weekly["claims_4wk"],
            "continuing_claims": weekly["continuing_claims"],
            "continuing_4wk_avg": weekly["continuing_4wk"],
            "insured_rate": weekly["insured_rate"],
        }
    )
    claims.index.name = "date"
    claims_path = CLEAN_DIR / "claims_weekly.csv"
    claims.to_csv(claims_path)

    payrolls = pd.DataFrame({"payems": monthly["payems"]})
    payrolls["payems_change"] = payrolls["payems"].diff()
    payrolls["payems_change_3m"] = payrolls["payems_change"].rolling(3, min_periods=3).mean()
    payrolls.index.name = "date"
    payrolls_path = CLEAN_DIR / "payrolls_monthly.csv"
    payrolls.to_csv(payrolls_path)

    household = monthly[["unrate", "civpart"]].copy()
    household.index.name = "date"
    household_path = CLEAN_DIR / "household_monthly.csv"
    household.to_csv(household_path)

    earnings = pd.DataFrame({"ahe": monthly["ahe"]})
    earnings["ahe_yoy"] = (earnings["ahe"] / earnings["ahe"].shift(12) - 1.0) * 100.0
    earnings.index.name = "date"
    earnings_path = CLEAN_DIR / "earnings_monthly.csv"
    earnings.to_csv(earnings_path)

    recessions = monthly[["usrec"]].copy()
    recessions.index.name = "date"
    recessions_path = CLEAN_DIR / "recessions.csv"
    recessions.to_csv(recessions_path)

    for path in (claims_path, payrolls_path, household_path, earnings_path, recessions_path):
        print("Wrote", path)


if __name__ == "__main__":
    main()
