"""
Step 2 of 3: convert raw FRED pulls into chart-ready rates and contributions.

Canonical rate definitions live here so chart code only plots columns:
  month over month (m/m) = percent change from the prior month
  year over year (y/y)   = percent change from 12 months earlier
  3-month annualized     = ((latest / value 3 months ago)^(12/3) - 1) * 100
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"

INDEX_SERIES = [
    "cpi_headline",
    "cpi_core",
    "cpi_headline_unadjusted",
    "cpi_core_unadjusted",
    "cpi_energy",
    "cpi_food",
    "cpi_shelter",
    "cpi_core_goods",
    "pce_headline",
    "pce_core",
    "retail_sales",
]

# MANUAL: Rounded December 2025 CPI relative-importance shares for directional
# monthly-contribution estimates. This is a fixed-weight approximation, not the
# official BLS chained contribution method.
# https://www.bls.gov/cpi/tables/relative-importance/2025.htm
WEIGHTS = {
    "cpi_energy": 0.065,
    "cpi_food": 0.143,
    "cpi_core_goods": 0.185,
    "cpi_shelter": 0.364,
}


def annualized(series: pd.Series, months: int) -> pd.Series:
    """Compound an m-month index change into an annualized percent rate."""
    return ((series / series.shift(months)) ** (12 / months) - 1) * 100


def main() -> None:
    monthly = pd.read_csv(RAW_DIR / "fred_monthly.csv", index_col="date", parse_dates=True)
    monthly.index = monthly.index.to_period("M").to_timestamp()
    monthly = monthly.groupby(monthly.index).last().sort_index()

    inflation = monthly[
        [
            "cpi_headline",
            "cpi_core",
            "cpi_headline_unadjusted",
            "cpi_core_unadjusted",
            "cpi_energy",
            "cpi_food",
            "cpi_shelter",
            "cpi_core_goods",
            "pce_headline",
            "pce_core",
        ]
    ].copy()
    for column in [
        "cpi_headline",
        "cpi_core",
        "cpi_headline_unadjusted",
        "cpi_core_unadjusted",
        "cpi_energy",
        "cpi_food",
        "cpi_shelter",
        "cpi_core_goods",
        "pce_headline",
        "pce_core",
    ]:
        inflation[f"{column}_mom"] = monthly[column].pct_change(fill_method=None) * 100
        inflation[f"{column}_yoy"] = monthly[column].pct_change(12, fill_method=None) * 100
        inflation[f"{column}_ann3"] = annualized(monthly[column], 3)

    # Published BLS year-over-year CPI uses unadjusted indexes.
    inflation["cpi_headline_release_yoy"] = (
        monthly["cpi_headline_unadjusted"].pct_change(12, fill_method=None) * 100
    )
    inflation["cpi_core_release_yoy"] = (
        monthly["cpi_core_unadjusted"].pct_change(12, fill_method=None) * 100
    )
    inflation["pce_headline_yoy"] = inflation["pce_headline_yoy"]
    inflation["pce_core_yoy"] = inflation["pce_core_yoy"]

    for component, weight in WEIGHTS.items():
        suffix = component.replace("cpi_", "")
        inflation[f"contrib_{suffix}_mom_pp"] = weight * inflation[f"{component}_mom"]

    known = sum(
        inflation[f"contrib_{component.replace('cpi_', '')}_mom_pp"]
        for component in WEIGHTS
    )
    inflation["contrib_other_services_mom_pp"] = inflation["cpi_headline_mom"] - known

    labor = monthly[["payems", "unrate", "civpart"]].copy()
    labor["payroll_change_k"] = monthly["payems"].diff()
    labor["payroll_three_month_avg_k"] = labor["payroll_change_k"].rolling(3).mean()

    activity = monthly[["retail_sales", "housing_starts"]].copy()
    activity["retail_sales_mom"] = monthly["retail_sales"].pct_change(fill_method=None) * 100
    activity["retail_sales_yoy"] = monthly["retail_sales"].pct_change(12, fill_method=None) * 100
    activity["housing_starts_mom"] = (
        monthly["housing_starts"].pct_change(fill_method=None) * 100
    )

    daily = pd.read_csv(RAW_DIR / "fred_daily.csv", index_col="date", parse_dates=True)
    daily = daily.sort_index()
    daily["fed_target_midpoint"] = (
        daily["fed_target_upper"] + daily["fed_target_lower"]
    ) / 2

    fedwatch = pd.read_csv(RAW_DIR / "fedwatch_snapshots.csv")
    latest = inflation["cpi_headline_mom"].dropna().index[-1]
    contrib = pd.DataFrame(
        {
            "component": [
                "Energy",
                "Core goods",
                "Shelter",
                "Other services",
                "Food",
            ],
            "contribution_pp": [
                inflation.loc[latest, "contrib_energy_mom_pp"],
                inflation.loc[latest, "contrib_core_goods_mom_pp"],
                inflation.loc[latest, "contrib_shelter_mom_pp"],
                inflation.loc[latest, "contrib_other_services_mom_pp"],
                inflation.loc[latest, "contrib_food_mom_pp"],
            ],
        }
    )

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    inflation.index.name = "date"
    labor.index.name = "date"
    activity.index.name = "date"
    daily.index.name = "date"
    inflation.to_csv(CLEAN_DIR / "inflation.csv")
    labor.to_csv(CLEAN_DIR / "labor.csv")
    activity.to_csv(CLEAN_DIR / "activity.csv")
    daily.to_csv(CLEAN_DIR / "rates_daily.csv")
    fedwatch.to_csv(CLEAN_DIR / "fedwatch.csv", index=False)
    contrib.to_csv(CLEAN_DIR / "cpi_contributions.csv", index=False)
    print(f"Wrote clean CSVs through {latest.strftime('%Y-%m')}")


if __name__ == "__main__":
    main()
