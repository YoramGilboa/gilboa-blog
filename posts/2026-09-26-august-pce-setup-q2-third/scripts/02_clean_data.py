"""
02_clean_data.py
================
STEP 2 of the data pipeline.

What this script does
---------------------
Turns raw FRED levels into the rate columns the charts plot. Charts must
not recompute these formulas.

Canonical rate definitions
--------------------------
Month-over-month (m/m) percent, from a dollar or index level:
    (this_month / previous_month - 1) * 100
    Example: an index move from 100.0 to 100.2 is +0.2%.
    A missing previous month stays missing. Nothing is interpolated.

Year-over-year (y/y) percent:
    (this_month / twelve_months_ago - 1) * 100
    PCE price indexes on FRED are seasonally adjusted. BEA's published
    12-month PCE rates use that same index, so both m/m and y/y come
    from PCEPI and PCEPILFE. This is not the CPI convention, where y/y
    uses a not-seasonally-adjusted index.

Three-month annualized percent:
    ((this_month / three_months_ago) ** 4 - 1) * 100
    Four quarters of the three-month change. It is a momentum reading,
    not a forecast.

The saving rate (PSAVERT) and the quarterly GDP rates are already
percents. This script does not convert them again.

History cutoff
--------------
Monthly rows after July 2026 are dropped, even if FRED has them.
Quarterly rows after 2026 Q2 (dated 2026-04-01) are dropped.
August PCE and the Q2 third estimate are out of sample on purpose.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"

# Last month BEA has published. Wednesday, September 30, is the August release.
MONTHLY_LAST = pd.Timestamp("2026-07-01")
# FRED dates quarterly observations at the first month of the quarter.
QUARTERLY_LAST = pd.Timestamp("2026-04-01")

YOY_START = pd.Timestamp("2022-01-01")
MOM_START = pd.Timestamp("2025-02-01")  # 18 months ending July 2026
REAL_START = pd.Timestamp("2025-02-01")
GDP_START = pd.Timestamp("2024-07-01")  # eight quarters ending 2026 Q2

LEVEL_COLUMNS = (
    "pce_price",
    "core_price",
    "real_pce",
    "personal_income",
    "disposable_pi",
    "nominal_pce",
)


def mom(series: pd.Series) -> pd.Series:
    """Month-over-month percent change. See the module docstring."""
    return series.pct_change(fill_method=None) * 100


def yoy(series: pd.Series) -> pd.Series:
    """Year-over-year percent change. See the module docstring."""
    return series.pct_change(12, fill_method=None) * 100


def ann3(series: pd.Series) -> pd.Series:
    """Three-month change, annualized. See the module docstring."""
    return ((series / series.shift(3)) ** 4 - 1) * 100


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    monthly_raw = pd.read_csv(RAW_DIR / "fred_pce_monthly.csv", index_col="date", parse_dates=True)
    quarterly_raw = pd.read_csv(RAW_DIR / "fred_gdp_quarterly.csv", index_col="date", parse_dates=True)

    dropped_months = monthly_raw.index[monthly_raw.index > MONTHLY_LAST]
    dropped_quarters = quarterly_raw.index[quarterly_raw.index > QUARTERLY_LAST]
    monthly = monthly_raw.loc[monthly_raw.index <= MONTHLY_LAST].sort_index()
    quarterly = quarterly_raw.loc[quarterly_raw.index <= QUARTERLY_LAST].sort_index()

    if monthly.index.max() != MONTHLY_LAST:
        raise RuntimeError(
            f"Monthly history does not reach July 2026. Last row is {monthly.index.max().date()}."
        )
    if quarterly.index.max() != QUARTERLY_LAST:
        raise RuntimeError(
            f"Quarterly history does not reach 2026 Q2. Last row is {quarterly.index.max().date()}."
        )

    clean = monthly.copy()
    for column in LEVEL_COLUMNS:
        clean[f"{column}_mom"] = mom(monthly[column])
        clean[f"{column}_yoy"] = yoy(monthly[column])
        clean[f"{column}_ann3"] = ann3(monthly[column])
    # PSAVERT is already a percent. Keep the level. Do not run it through mom().
    clean["saving_rate"] = monthly["saving_rate"]
    clean.to_csv(CLEAN_DIR / "pce_monthly.csv")

    gdp = quarterly.copy()
    gdp.index.name = "date"
    gdp.to_csv(CLEAN_DIR / "gdp_quarterly.csv")

    yoy_chart = clean.loc[clean.index >= YOY_START, ["pce_price_yoy", "core_price_yoy"]].rename(
        columns={"pce_price_yoy": "headline_yoy", "core_price_yoy": "core_yoy"}
    )
    yoy_chart.to_csv(CLEAN_DIR / "pce_yoy.csv")

    mom_chart = clean.loc[clean.index >= MOM_START, ["pce_price_mom", "core_price_mom"]].rename(
        columns={"pce_price_mom": "headline_mom", "core_price_mom": "core_mom"}
    )
    mom_chart.to_csv(CLEAN_DIR / "pce_mom.csv")

    # Bill is nominal spending (the cash register). Quantity is real spending.
    # The chart shades the gap. nominal_mom - real_mom is only an approximate
    # split of the bill into price and quantity. It is not the official PCE
    # price index, which is computed in pce_price_mom above.
    real_chart = clean.loc[
        clean.index >= REAL_START,
        ["nominal_pce_mom", "real_pce_mom", "saving_rate"],
    ].rename(columns={"nominal_pce_mom": "bill_mom", "real_pce_mom": "quantity_mom"})
    real_chart.to_csv(CLEAN_DIR / "real_saving.csv")

    gdp_chart = gdp.loc[gdp.index >= GDP_START, ["gdp_saar", "pdfp_saar"]]
    gdp_chart.to_csv(CLEAN_DIR / "gdp_vs_pdfp.csv")

    drop_note = CLEAN_DIR / "history_cutoff.txt"
    month_list = ", ".join(ts.strftime("%Y-%m") for ts in dropped_months) or "none"
    quarter_list = ", ".join(ts.strftime("%Y-%m") for ts in dropped_quarters) or "none"
    drop_note.write_text(
        "Monthly rows dropped because they are after July 2026: "
        + month_list
        + "\nQuarterly rows dropped because they are after 2026 Q2: "
        + quarter_list
        + "\nAugust PCE was not filled.\n",
        encoding="utf-8",
    )
    print(f"Monthly through {monthly.index.max().date()} ({len(monthly)} rows)")
    print(f"Quarterly through {quarterly.index.max().date()} ({len(quarterly)} rows)")
    print(f"Dropped months after July 2026: {month_list}")
    print(f"Dropped quarters after 2026 Q2: {quarter_list}")


if __name__ == "__main__":
    main()
