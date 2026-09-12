"""
02_clean_data.py
================
STEP 2 of the data pipeline.

What this script does
---------------------
Turns raw FRED CPI index levels into chart-ready monthly changes, 12-month
rates, and short annualized windows. It also builds the approximate August
contribution table. Charts should plot these columns and not re-derive them.

Canonical rate definitions
--------------------------
Month-over-month (m/m) percent, seasonally adjusted:
    (this_month_SA / last_month_SA - 1) * 100
    Example: if the SA index goes from 100.0 to 100.3, m/m is +0.3%.
    Missing last month (FRED NaN) yields NaN. We do not interpolate.

Year-over-year (y/y) percent, not seasonally adjusted:
    (this_month_NSA / month_12_ago_NSA - 1) * 100
    This is the published 12-month CPI rate convention.

N-month annualized percent, seasonally adjusted:
    ((this_month_SA / SA_N_months_ago) ** (12 / N) - 1) * 100
    For N=3 this is the three-month annualized pace. It is a momentum
    measure, not a forecast, and it can swing when energy moves.

Approximate contribution (percentage points):
    July relative importance (share of the CPI basket) times the August
    SA m/m percent for that component, divided by 100 in the weight.
    Official CPI uses chained aggregation, so the pieces are not expected
    to add exactly to the headline print.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"
AUGUST = pd.Timestamp("2026-08-01")
RECENT_START = pd.Timestamp("2025-12-01")

COMPONENTS = [
    "headline",
    "core",
    "food",
    "energy",
    "gasoline",
    "core_goods",
    "services_less_energy",
    "services_less_shelter",
    "shelter",
    "rent",
    "oer",
]

RELEASE_COMPONENTS = {
    "all_items": "headline",
    "food": "food",
    "energy": "energy",
    "gasoline": "gasoline",
    "core": "core",
    "core_goods": "core_goods",
    "services_less_energy": "services_less_energy",
    "shelter": "shelter",
    "rent": "rent",
    "oer": "oer",
}


def mom(series: pd.Series) -> pd.Series:
    """Month-over-month percent change from a level. See module docstring."""
    return series.pct_change(fill_method=None) * 100


def yoy(series: pd.Series) -> pd.Series:
    """Year-over-year percent change: this month versus the same month last year."""
    return series.pct_change(12, fill_method=None) * 100


def annualized(series: pd.Series, months: int) -> pd.Series:
    """Compound a months-long SA change into an annualized percent rate.

    If any month in the closed window from t-minus-N through t is missing,
    the annualized value is NaN. That keeps a FRED hole from producing a
    3-month rate that skips the missing month in the middle.
    """
    rate = ((series / series.shift(months)) ** (12 / months) - 1) * 100
    hole_in_window = series.isna().rolling(months + 1, min_periods=1).max().eq(1.0)
    return rate.where(~hole_in_window)


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(RAW_DIR / "fred_cpi_monthly.csv", index_col="date", parse_dates=True)
    raw.index = raw.index.to_period("M").to_timestamp()
    raw = raw.groupby(raw.index).last().sort_index()
    release = pd.read_csv(RAW_DIR / "bls_cpi_table1_august_2026.csv").set_index("component")

    clean = raw.copy()
    for component in COMPONENTS:
        clean[f"{component}_mom"] = mom(raw[f"{component}_sa"])
        clean[f"{component}_yoy"] = yoy(raw[f"{component}_nsa"])
        clean[f"{component}_ann3"] = annualized(raw[f"{component}_sa"], 3)
        clean[f"{component}_ann6"] = annualized(raw[f"{component}_sa"], 6)

    if AUGUST not in clean.index:
        raise RuntimeError("Validated FRED histories do not contain August 2026")
    if pd.isna(clean.loc[AUGUST, "headline_sa"]) or pd.isna(clean.loc[AUGUST, "core_sa"]):
        raise RuntimeError("August 2026 headline or core SA index is missing from FRED")

    recent = clean.loc[RECENT_START:AUGUST, ["headline_sa", "core_sa"]]
    if recent.isna().any().any():
        raise RuntimeError(
            "Headline or core SA is missing in Dec 2025 through August 2026. "
            "Re-run 01_fetch_data.py after FRED backfills the print."
        )

    gap_months = [
        stamp.strftime("%Y-%m")
        for stamp, row in clean.loc["2021-01-01":AUGUST, ["headline_sa", "core_sa"]].iterrows()
        if row.isna().any()
    ]

    for release_name, component in RELEASE_COMPONENTS.items():
        expected_mom = float(release.loc[release_name, "august_mom_sa"])
        expected_yoy = float(release.loc[release_name, "august_yoy_nsa"])
        observed_mom = round(float(clean.loc[AUGUST, f"{component}_mom"]), 1)
        observed_yoy = round(float(clean.loc[AUGUST, f"{component}_yoy"]), 1)
        if observed_mom != expected_mom or observed_yoy != expected_yoy:
            raise RuntimeError(
                f"{component} differs from BLS Table 1: "
                f"FRED {observed_mom:.1f}/{observed_yoy:.1f}, "
                f"BLS {expected_mom:.1f}/{expected_yoy:.1f}"
            )

    weights = release["relative_importance"] / 100
    august = clean.loc[AUGUST]
    contribution_rows = [
        ("Energy", weights["energy"] * august["energy_mom"]),
        ("Food", weights["food"] * august["food_mom"]),
        ("Shelter", weights["shelter"] * august["shelter_mom"]),
        ("Core goods", weights["core_goods"] * august["core_goods_mom"]),
        (
            "Other services",
            weights["services_less_energy"] * august["services_less_energy_mom"]
            - weights["shelter"] * august["shelter_mom"],
        ),
    ]
    contributions = pd.DataFrame(contribution_rows, columns=["component", "contribution_pp"])
    gasoline_contrib = float(weights["gasoline"] * august["gasoline_mom"])
    contributions["approximate_total_pp"] = contributions["contribution_pp"].sum()
    contributions["official_headline_mom"] = release.loc["all_items", "august_mom_sa"]
    contributions["gasoline_contrib_pp"] = gasoline_contrib

    clean.index.name = "date"
    clean.to_csv(CLEAN_DIR / "cpi_history.csv")
    contributions.to_csv(CLEAN_DIR / "august_contributions.csv", index=False)
    release.reset_index().to_csv(CLEAN_DIR / "bls_release_table.csv", index=False)

    print("BLS/FRED rounded-rate checks: PASS")
    print(f"Headline/core FRED gap months (not interpolated): {gap_months or 'none'}")
    print(
        "Approximate contribution sum: "
        f"{contributions['contribution_pp'].sum():.3f} pp "
        f"vs official {release.loc['all_items', 'august_mom_sa']:.1f}%"
    )


if __name__ == "__main__":
    main()
