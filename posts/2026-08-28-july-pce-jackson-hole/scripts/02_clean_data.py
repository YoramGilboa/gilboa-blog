"""
02_clean_data.py
================
STEP 2 of the data pipeline.

What this script does
---------------------
Turns raw FRED indexes into chart-ready monthly and yearly percent changes.

Canonical rate definitions (used by charts and stats):
- Month-over-month (m/m): percent change from last month to this month.
  Formula: (this_month / last_month - 1) * 100
- Year-over-year (YoY): compared with the same month last year.
  Formula: (this_month / month_12_ago - 1) * 100

If FRED has not yet published July 2026 PCE prints, this script appends the
official BEA values and flags reconstructed_july = True for the stats step.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"

JULY = pd.Timestamp("2026-07-01")

# MANUAL: BEA Personal Income and Outlays, July 2026, released 8/26/2026.
# https://www.bea.gov/news/2026/personal-income-and-outlays-july-2026
BEA_JULY_HEADLINE_MOM = 0.2
BEA_JULY_HEADLINE_YOY = 3.7
BEA_JULY_CORE_MOM = 0.2
BEA_JULY_CORE_YOY = 3.3
BEA_JULY_SAVING_RATE = 3.0


def mom(series: pd.Series) -> pd.Series:
    """Month-over-month percent change from the index level.

    Example: if the index is 100 in June and 100.2 in July, m/m is +0.2%.
    fill_method=None means we do not invent values across missing months.
    """
    return series.pct_change(fill_method=None) * 100


def yoy(series: pd.Series) -> pd.Series:
    """Year-over-year percent change: this month versus the same month last year.

    Example: July 2026 versus July 2025. Charts and prose both use this column
    so a reader never sees two different 'yearly' formulas.
    """
    return series.pct_change(12, fill_method=None) * 100


def implied_index(previous: float, mom_pct: float) -> float:
    """Back out an index level from last month's level and an official m/m print."""
    return previous * (1.0 + mom_pct / 100.0)


def main() -> None:
    monthly = pd.read_csv(RAW_DIR / "fred_monthly.csv", index_col="date", parse_dates=True)
    monthly.index = monthly.index.to_period("M").to_timestamp()
    monthly = monthly.groupby(monthly.index).last().sort_index()

    daily = pd.read_csv(RAW_DIR / "fred_daily.csv", index_col="date", parse_dates=True)
    daily = daily.sort_index()
    policy_monthly = daily.resample("MS").last()

    reconstructed_july = False
    pce_latest = monthly["pce_headline"].dropna().index.max()
    if pce_latest < JULY:
        print(
            "WARNING: FRED PCE history ends "
            f"{pce_latest.strftime('%Y-%m')}. "
            "Appending official July 2026 BEA prints. Replace this overlay "
            "before publish if FRED later carries the same month."
        )
        reconstructed_july = True
        june = monthly.loc[pd.Timestamp("2026-06-01")]
        if JULY not in monthly.index:
            monthly.loc[JULY] = pd.Series({col: pd.NA for col in monthly.columns})
        # Overlay only PCE-related fields. Do not overwrite PAYEMS/UNRATE if
        # FRED already published the July jobs print.
        monthly.loc[JULY, "pce_headline"] = implied_index(
            float(june["pce_headline"]), BEA_JULY_HEADLINE_MOM
        )
        monthly.loc[JULY, "pce_core"] = implied_index(
            float(june["pce_core"]), BEA_JULY_CORE_MOM
        )
        monthly.loc[JULY, "saving_rate"] = BEA_JULY_SAVING_RATE
        if pd.isna(monthly.loc[JULY, "real_pce"]) and pd.notna(june["real_pce"]):
            monthly.loc[JULY, "real_pce"] = float(june["real_pce"])
        monthly = monthly.sort_index()

    clean = monthly.copy()
    clean["pce_headline_mom"] = mom(monthly["pce_headline"])
    clean["pce_headline_yoy"] = yoy(monthly["pce_headline"])
    clean["pce_core_mom"] = mom(monthly["pce_core"])
    clean["pce_core_yoy"] = yoy(monthly["pce_core"])
    clean["real_pce_mom"] = mom(monthly["real_pce"])
    clean["real_pce_yoy"] = yoy(monthly["real_pce"])
    clean["payroll_change_k"] = monthly["payems"].diff()

    # Always pin July 2026 PCE rates to the official BEA release so prose
    # matches the print even if FRED rounding differs by a hundredth.
    if JULY in clean.index:
        clean.loc[JULY, "pce_headline_mom"] = BEA_JULY_HEADLINE_MOM
        clean.loc[JULY, "pce_headline_yoy"] = BEA_JULY_HEADLINE_YOY
        clean.loc[JULY, "pce_core_mom"] = BEA_JULY_CORE_MOM
        clean.loc[JULY, "pce_core_yoy"] = BEA_JULY_CORE_YOY
        clean.loc[JULY, "saving_rate"] = BEA_JULY_SAVING_RATE
        clean.loc[JULY, "real_pce_mom"] = 0.0

    main_frame = clean.join(policy_monthly, how="left").sort_index()
    main_frame.index.name = "date"
    main_frame["reconstructed_july"] = reconstructed_july

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    main_frame.to_csv(CLEAN_DIR / "main.csv")
    flag_path = CLEAN_DIR / "reconstructed_july.txt"
    flag_path.write_text("true" if reconstructed_july else "false", encoding="utf-8")
    print(f"Wrote {CLEAN_DIR / 'main.csv'} through {main_frame.index.max().strftime('%Y-%m')}")
    print(f"reconstructed_july={reconstructed_july}")


if __name__ == "__main__":
    main()
