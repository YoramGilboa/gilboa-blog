"""Clean raw FRED series and compute chart-ready rates for the July CPI/PPI post."""

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
    "cpi_medical_services",
    "ppi_final_demand",
    "ppi_final_demand_goods",
    "ppi_final_demand_services",
    "ppi_energy",
    "ppi_less_food_energy_trade",
    "ahe_total_private",
]

# MANUAL: Rounded December 2025 CPI relative-importance shares for directional
# monthly-contribution estimates.
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

    clean = monthly.copy()
    for column in INDEX_SERIES:
        clean[f"{column}_mom"] = monthly[column].pct_change(fill_method=None) * 100
        clean[f"{column}_yoy"] = monthly[column].pct_change(12, fill_method=None) * 100
        clean[f"{column}_ann3"] = annualized(monthly[column], 3)

    # Payroll and participation context are used to connect this post to the
    # earlier labor-market post without repeating its full analysis.
    clean["payroll_change_k"] = monthly["payems"].diff()
    clean["payroll_three_month_avg_k"] = clean["payroll_change_k"].rolling(3).mean()

    # Real average hourly earnings deflate nominal hourly pay by the CPI index.
    clean["real_ahe_index"] = (monthly["ahe_total_private"] / monthly["cpi_headline"]) * 100
    clean["real_ahe_yoy"] = clean["real_ahe_index"].pct_change(12, fill_method=None) * 100

    # The published BLS year-over-year CPI headline and core figures use
    # unadjusted indexes, even when the month-over-month figures are seasonally
    # adjusted. Keep both versions so the draft can match the release text.
    clean["cpi_headline_release_yoy"] = (
        monthly["cpi_headline_unadjusted"].pct_change(12, fill_method=None) * 100
    )
    clean["cpi_core_release_yoy"] = (
        monthly["cpi_core_unadjusted"].pct_change(12, fill_method=None) * 100
    )

    for component, weight in WEIGHTS.items():
        suffix = component.replace("cpi_", "")
        clean[f"contrib_{suffix}_mom_pp"] = weight * clean[f"{component}_mom"]

    known = sum(
        clean[f"contrib_{component.replace('cpi_', '')}_mom_pp"]
        for component in WEIGHTS
    )
    clean["contrib_other_services_mom_pp"] = clean["cpi_headline_mom"] - known

    daily = pd.read_csv(RAW_DIR / "fred_daily.csv", index_col="date", parse_dates=True)
    daily = daily.sort_index()
    daily["fed_target_midpoint"] = (daily["fed_target_upper"] + daily["fed_target_lower"]) / 2
    policy_monthly = daily.resample("MS").last()

    main_frame = clean.join(policy_monthly, how="left").sort_index()
    main_frame.index.name = "date"

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    main_frame.to_csv(CLEAN_DIR / "main.csv")

    latest = main_frame["cpi_headline_yoy"].dropna().index[-1]
    print(f"Wrote {CLEAN_DIR / 'main.csv'} through {latest.strftime('%Y-%m')}")


if __name__ == "__main__":
    main()