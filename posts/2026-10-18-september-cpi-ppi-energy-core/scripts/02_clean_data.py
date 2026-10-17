"""
02_clean_data.py
================
STEP 2 of the data pipeline.

What this script does
---------------------
Turns the locked CPI and PPI index levels into monthly and yearly percent
changes, and passes through the official September CPI contribution effects.

Canonical rate definitions
--------------------------
Month-over-month percent, from a seasonally adjusted index unless noted:
    (this_month / previous_month - 1) * 100
    A missing month stays missing. This script does not interpolate.

Year-over-year percent, from the not-seasonally-adjusted index:
    (this_month / same_month_last_year - 1) * 100
    This is the published 12-month convention.

The September gasoline month change is also computed from the unadjusted
index. That NSA change is the 6.5 percent print. It is not the 9.1 percent
seasonally adjusted print.

Charts plot these columns. They do not recompute the rates.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"
SEP = pd.Timestamp("2026-09-01")
AUG = pd.Timestamp("2026-08-01")
JUL = pd.Timestamp("2026-07-01")


def mom(series: pd.Series) -> pd.Series:
    """Month-over-month percent. See the module docstring."""
    return series.pct_change(fill_method=None) * 100


def yoy(series: pd.Series) -> pd.Series:
    """Year-over-year percent versus the same month a year earlier."""
    return series.pct_change(12, fill_method=None) * 100


def round_half_up(value: float, places: str) -> Decimal:
    """Round half away from zero so 0.25 becomes 0.3 at one decimal."""
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def require(frame: pd.DataFrame, column: str, stamp: pd.Timestamp, expected: str) -> None:
    observed = round_half_up(float(frame.loc[stamp, column]), "0.1")
    if str(observed) != expected:
        raise RuntimeError(
            f"{column} on {stamp.date()} is {observed}, expected {expected}. "
            "The vintage does not match the locked BLS print."
        )


def load_levels(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, index_col="date", parse_dates=True)
    frame.index = frame.index.to_period("M").to_timestamp()
    frame = frame.groupby(frame.index).last().sort_index()
    frame.index.name = "date"
    return frame


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    cpi_levels = load_levels(RAW_DIR / "fred_cpi_monthly.csv")
    ppi_levels = load_levels(RAW_DIR / "fred_ppi_monthly.csv")

    cpi = pd.DataFrame(index=cpi_levels.index)
    cpi.index.name = "date"
    sa_mom = {
        "headline_mom": "headline_sa",
        "core_mom": "core_sa",
        "energy_mom": "energy_sa",
        "gasoline_mom": "gasoline_sa",
        "food_mom": "food_sa",
        "shelter_mom": "shelter_sa",
        "services_mom": "services_sa",
        "core_goods_mom": "core_goods_sa",
    }
    nsa_yoy = {
        "headline_yoy": "headline_nsa",
        "core_yoy": "core_nsa",
        "energy_yoy": "energy_nsa",
        "gasoline_yoy": "gasoline_nsa",
        "food_yoy": "food_nsa",
        "shelter_yoy": "shelter_nsa",
        "services_yoy": "services_nsa",
    }
    for column, source in sa_mom.items():
        cpi[column] = mom(cpi_levels[source])
    for column, source in nsa_yoy.items():
        cpi[column] = yoy(cpi_levels[source])
    cpi["gasoline_nsa_mom"] = mom(cpi_levels["gasoline_nsa"])
    cpi["headline_nsa_mom"] = mom(cpi_levels["headline_nsa"])
    cpi["core_nsa_mom"] = mom(cpi_levels["core_nsa"])

    ppi = pd.DataFrame(index=ppi_levels.index)
    ppi.index.name = "date"
    ppi["ppi_fd_mom"] = mom(ppi_levels["ppi_fd_sa"])
    ppi["ppi_fd_yoy"] = yoy(ppi_levels["ppi_fd_nsa"])
    ppi["ppi_goods_mom"] = mom(ppi_levels["ppi_goods_sa"])
    ppi["ppi_services_mom"] = mom(ppi_levels["ppi_services_sa"])
    ppi["ppi_energy_mom"] = mom(ppi_levels["ppi_energy_sa"])
    ppi["ppi_foods_mom"] = mom(ppi_levels["ppi_foods_sa"])
    ppi["ppi_core_goods_mom"] = mom(ppi_levels["ppi_core_goods_sa"])
    ppi["ppi_x_mom"] = mom(ppi_levels["ppi_x_sa"])
    ppi["ppi_x_yoy"] = yoy(ppi_levels["ppi_x_nsa"])

    if SEP not in cpi.index or SEP not in ppi.index:
        raise RuntimeError("September 2026 is missing from the locked levels.")

    require(cpi, "headline_mom", SEP, "0.6")
    require(cpi, "headline_yoy", SEP, "3.7")
    require(cpi, "headline_mom", AUG, "0.4")
    require(cpi, "headline_yoy", AUG, "3.4")
    require(cpi, "core_mom", SEP, "0.3")
    require(cpi, "core_yoy", SEP, "2.6")
    require(cpi, "core_mom", AUG, "0.3")
    require(cpi, "core_yoy", AUG, "2.4")
    require(cpi, "energy_mom", SEP, "5.2")
    require(cpi, "energy_mom", AUG, "2.1")
    require(cpi, "energy_yoy", SEP, "20.4")
    require(cpi, "gasoline_mom", SEP, "9.1")
    require(cpi, "gasoline_nsa_mom", SEP, "6.5")
    require(cpi, "gasoline_yoy", SEP, "34.2")
    require(cpi, "food_mom", SEP, "0.0")
    require(cpi, "food_yoy", SEP, "2.5")
    require(cpi, "shelter_mom", SEP, "0.4")
    require(cpi, "shelter_mom", AUG, "0.3")
    require(cpi, "shelter_yoy", SEP, "3.2")
    require(ppi, "ppi_fd_mom", SEP, "1.3")
    require(ppi, "ppi_fd_yoy", SEP, "6.3")
    require(ppi, "ppi_fd_mom", AUG, "0.5")
    require(ppi, "ppi_fd_mom", JUL, "0.2")
    require(ppi, "ppi_goods_mom", SEP, "2.6")
    require(ppi, "ppi_services_mom", SEP, "0.8")
    require(ppi, "ppi_energy_mom", SEP, "10.8")
    require(ppi, "ppi_foods_mom", SEP, "1.2")
    require(ppi, "ppi_core_goods_mom", SEP, "0.3")
    require(ppi, "ppi_x_mom", SEP, "0.5")
    require(ppi, "ppi_x_mom", AUG, "0.3")
    require(ppi, "ppi_x_yoy", SEP, "5.0")

    joined = cpi[["headline_yoy", "core_yoy"]].join(
        ppi[["ppi_fd_yoy", "ppi_x_yoy"]],
        how="outer",
    )
    joined.index.name = "date"

    table6 = pd.read_csv(RAW_DIR / "bls_table6_september_2026.csv")
    labels = {
        "all_items": "All items",
        "food": "Food",
        "energy": "Energy",
        "gasoline": "Gasoline",
        "core": "Core",
    }
    table6["label"] = table6["component"].map(labels)
    gasoline = float(table6.loc[table6["component"] == "gasoline", "effect_pp"].iloc[0])
    headline = float(table6.loc[table6["component"] == "all_items", "percent_change"].iloc[0])
    if gasoline / headline <= 0.5:
        raise RuntimeError(
            "Table 6 gasoline effect is not more than half of the all-items change. "
            "Stop. Do not keep the contribution thesis."
        )
    plotted = table6[table6["plot"] == 1]
    effect_sum = float(plotted["effect_pp"].sum())
    table6["official_headline_mom"] = headline
    table6["plotted_effect_sum_pp"] = effect_sum

    # Directional cross-check only. The chart uses effect_pp, not this product.
    table6["approx_pp"] = table6["relative_importance"] * table6["percent_change"] / 100

    cpi.to_csv(CLEAN_DIR / "cpi_monthly.csv")
    ppi.to_csv(CLEAN_DIR / "ppi_monthly.csv")
    joined.to_csv(CLEAN_DIR / "ppi_cpi_monthly.csv")
    table6.to_csv(CLEAN_DIR / "contributions_september.csv", index=False)

    gap_frame = cpi_levels.loc["2021-01-01":SEP, ["headline_sa", "core_sa", "energy_sa"]]
    gap_months = [
        stamp.strftime("%Y-%m")
        for stamp, row in gap_frame.iterrows()
        if row.isna().any()
    ]
    print("BLS/FRED one-decimal checks: PASS")
    print(f"Headline, core, or energy gap months: {gap_months or 'none'}")
    print(f"Table 6 plotted effects sum to {effect_sum:.3f} pp vs headline {headline:.1f}%")
    print(f"Gasoline effect share of the 0.6 print: {100 * gasoline / headline:.1f}%")


if __name__ == "__main__":
    main()
