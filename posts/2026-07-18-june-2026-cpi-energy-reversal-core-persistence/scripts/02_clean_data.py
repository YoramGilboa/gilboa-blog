"""Clean the fetched series and compute the chart-ready monthly dataset."""

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"

INDEX_SERIES = [
    "headline",
    "core",
    "energy",
    "gasoline",
    "shelter",
    "food",
    "core_goods",
]

# MANUAL: Rounded December 2025 CPI relative-importance shares.
# https://www.bls.gov/cpi/tables/relative-importance/2025.htm
# The residual category is calculated, not assigned a fixed share.
WEIGHTS = {
    "energy": 0.065,
    "food": 0.143,
    "core_goods": 0.185,
    "shelter": 0.364,
}


def annualized(series, months):
    return ((series / series.shift(months)) ** (12 / months) - 1) * 100


def main():
    monthly = pd.read_csv(
        RAW_DIR / "fred_monthly.csv", index_col="date", parse_dates=True
    )
    monthly.index = monthly.index.to_period("M").to_timestamp()
    monthly = monthly.groupby(monthly.index).last().sort_index()

    for column in INDEX_SERIES:
        monthly[f"{column}_mom"] = monthly[column].pct_change(fill_method=None) * 100
        monthly[f"{column}_yoy"] = (
            monthly[column].pct_change(12, fill_method=None) * 100
        )
        monthly[f"{column}_ann3"] = annualized(monthly[column], 3)

    monthly["payroll_change_k"] = monthly["payems"].diff()

    for component, weight in WEIGHTS.items():
        monthly[f"contrib_{component}_mom_pp"] = (
            weight * monthly[f"{component}_mom"]
        )

    known = sum(
        monthly[f"contrib_{component}_mom_pp"] for component in WEIGHTS
    )
    monthly["contrib_other_services_mom_pp"] = monthly["headline_mom"] - known

    daily = pd.read_csv(
        RAW_DIR / "fred_daily.csv", index_col="date", parse_dates=True
    )
    rates = daily.resample("MS").last()
    rates["curve_10y_2y"] = rates["dgs10"] - rates["dgs2"]

    main = monthly.join(rates, how="outer").sort_index()
    main.index.name = "date"

    fomc = pd.read_csv(
        RAW_DIR / "fred_fomc.csv", index_col="date", parse_dates=True
    ).sort_index()

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    main.to_csv(CLEAN_DIR / "main.csv")
    fomc.to_csv(CLEAN_DIR / "fomc_sep.csv")

    latest = main["headline_yoy"].dropna().index[-1]
    print(f"Clean CPI data through {latest.date()}")


if __name__ == "__main__":
    main()
