"""
02_clean_data.py
================
STEP 2 of the data pipeline.

What this script does
---------------------
Turns locked index levels into percent changes, and passes through the
official October CPI contribution effects from the transcribed BLS table.

Canonical rate definitions
--------------------------
Month-over-month percent, from a seasonally adjusted index unless noted:
    (this_month / previous_month - 1) * 100
    A missing month stays missing. This script does not interpolate and
    does not drop the empty month.

Year-over-year percent, from the not-seasonally-adjusted index for CPI
and PPI 12-month rates:
    (this_month / same_month_last_year - 1) * 100
    If the same month a year earlier is missing, the result is missing.
    October 2026 CPI has no official 12-month rate for that reason.

Three-month annualized pace, from a seasonally adjusted index:
    ((this_month / three_months_earlier) ** 4 - 1) * 100
    This is a pace, not a 12-month rate. It is missing when any lag in
    the three-month window is missing.

Contribution
------------
A BLS Table 6 "effect" is the category's contribution to the all-items
percent change, in percentage points. The share of the month is that
effect divided by the all-items change. It is not the category's own
percent change.

Charts plot these columns. They do not recompute the rates.
"""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"
OCT = pd.Timestamp("2026-10-01")
SEP = pd.Timestamp("2026-09-01")
AUG = pd.Timestamp("2026-08-01")
OCT_2025 = pd.Timestamp("2025-10-01")


def mom(series: pd.Series) -> pd.Series:
    """Month-over-month percent. See the module docstring."""
    return series.pct_change(fill_method=None) * 100


def yoy(series: pd.Series) -> pd.Series:
    """Year-over-year percent versus the same month a year earlier."""
    return series.pct_change(12, fill_method=None) * 100


def ann3(series: pd.Series) -> pd.Series:
    """Three-month pace, only when all four monthly levels are present."""
    complete = series.notna().rolling(4, min_periods=4).sum().eq(4)
    return (((series / series.shift(3)) ** 4 - 1) * 100).where(complete)


def round_half_up(value: float, places: str) -> Decimal:
    """Round half away from zero so 0.35 becomes 0.4 at one decimal."""
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def require(frame: pd.DataFrame, column: str, stamp: pd.Timestamp, expected: str) -> None:
    observed = round_half_up(float(frame.loc[stamp, column]), "0.1")
    if str(observed) != expected:
        raise RuntimeError(
            f"{column} on {stamp.date()} is {observed}, expected {expected}. "
            "The vintage does not match the locked print."
        )


def require_missing(frame: pd.DataFrame, column: str, stamp: pd.Timestamp) -> None:
    value = frame.loc[stamp, column]
    if pd.notna(value):
        raise RuntimeError(
            f"{column} on {stamp.date()} is {value}. "
            "The official October 12-month CPI rate must stay missing."
        )


def monthly_index(frame: pd.DataFrame) -> pd.DataFrame:
    """Put every month on the calendar, including months FRED left out."""
    frame = frame.copy()
    frame.index = pd.to_datetime(frame.index).to_period("M").to_timestamp()
    frame = frame.groupby(frame.index).last().sort_index()
    full = pd.date_range(frame.index.min(), frame.index.max(), freq="MS")
    frame = frame.reindex(full)
    frame.index.name = "date"
    return frame


def load_levels(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, index_col="date", parse_dates=True)
    return monthly_index(frame)


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    cpi_levels = load_levels(RAW_DIR / "fred_cpi_monthly.csv")
    ppi_levels = load_levels(RAW_DIR / "fred_ppi_monthly.csv")
    pce_levels = load_levels(RAW_DIR / "fred_pce_monthly.csv")
    ahe_levels = load_levels(RAW_DIR / "fred_earnings_monthly.csv")
    prod_levels = pd.read_csv(RAW_DIR / "fred_productivity_quarterly.csv", index_col="date", parse_dates=True)
    prod_levels.index = pd.to_datetime(prod_levels.index).to_period("Q").to_timestamp()
    prod_levels = prod_levels.groupby(prod_levels.index).last().sort_index()
    prod_levels.index.name = "date"

    if pd.notna(cpi_levels.loc[OCT_2025, "headline_sa"]):
        raise RuntimeError("October 2025 headline CPI is present. The data gap was filled.")
    if pd.notna(cpi_levels.loc[OCT_2025, "core_sa"]):
        raise RuntimeError("October 2025 core CPI is present. The data gap was filled.")

    cpi = pd.DataFrame(index=cpi_levels.index)
    cpi["headline_sa"] = cpi_levels["headline_sa"]
    cpi["headline_nsa"] = cpi_levels["headline_nsa"]
    cpi["core_sa"] = cpi_levels["core_sa"]
    cpi["core_nsa"] = cpi_levels["core_nsa"]
    cpi["cpi_mom"] = mom(cpi_levels["headline_sa"])
    cpi["cpi_nsa_mom"] = mom(cpi_levels["headline_nsa"])
    cpi["cpi_yoy"] = yoy(cpi_levels["headline_nsa"])
    cpi["cpi_core_mom"] = mom(cpi_levels["core_sa"])
    cpi["cpi_core_yoy"] = yoy(cpi_levels["core_nsa"])
    cpi["cpi_food_mom"] = mom(cpi_levels["food_sa"])
    cpi["cpi_energy_mom"] = mom(cpi_levels["energy_sa"])
    cpi["cpi_shelter_mom"] = mom(cpi_levels["shelter_sa"])
    cpi["cpi_rent_mom"] = mom(cpi_levels["rent_sa"])
    cpi["cpi_oer_mom"] = mom(cpi_levels["oer_sa"])
    cpi["cpi_gasoline_mom"] = mom(cpi_levels["gasoline_sa"])
    cpi["cpi_gasoline_nsa_mom"] = mom(cpi_levels["gasoline_nsa"])
    cpi["cpi_ann3"] = ann3(cpi_levels["headline_sa"])
    cpi["cpi_core_ann3"] = ann3(cpi_levels["core_sa"])
    cpi.to_csv(CLEAN_DIR / "cpi_monthly.csv", lineterminator="\n")

    ppi = pd.DataFrame(index=ppi_levels.index)
    ppi["ppi_mom"] = mom(ppi_levels["ppi_fd_sa"])
    ppi["ppi_yoy"] = yoy(ppi_levels["ppi_fd_nsa"])
    ppi["ppi_core_mom"] = mom(ppi_levels["ppi_x_sa"])
    ppi["ppi_core_yoy"] = yoy(ppi_levels["ppi_x_nsa"])
    ppi["ppi_goods_mom"] = mom(ppi_levels["ppi_goods_sa"])
    ppi["ppi_goods_yoy"] = yoy(ppi_levels["ppi_goods_nsa"])
    ppi["ppi_services_mom"] = mom(ppi_levels["ppi_services_sa"])
    ppi["ppi_services_yoy"] = yoy(ppi_levels["ppi_services_nsa"])
    ppi["ppi_foods_mom"] = mom(ppi_levels["ppi_foods_sa"])
    ppi["ppi_energy_mom"] = mom(ppi_levels["ppi_energy_sa"])
    ppi["ppi_goods_ex_food_energy_mom"] = mom(ppi_levels["ppi_core_goods_sa"])
    ppi.to_csv(CLEAN_DIR / "ppi_monthly.csv", lineterminator="\n")

    pce = pd.DataFrame(index=pce_levels.index)
    pce["pce_mom"] = mom(pce_levels["pce"])
    pce["pce_yoy"] = yoy(pce_levels["pce"])
    pce["core_pce_mom"] = mom(pce_levels["core_pce"])
    pce["core_pce_yoy"] = yoy(pce_levels["core_pce"])
    pce.to_csv(CLEAN_DIR / "pce_monthly.csv", lineterminator="\n")

    earnings = pd.DataFrame(index=ahe_levels.index)
    earnings["ahe_level"] = ahe_levels["ahe"]
    earnings["ahe_mom"] = mom(ahe_levels["ahe"])
    earnings["ahe_yoy"] = yoy(ahe_levels["ahe"])
    earnings.to_csv(CLEAN_DIR / "earnings_monthly.csv", lineterminator="\n")

    prod = prod_levels.copy()
    prod.to_csv(CLEAN_DIR / "productivity_quarterly.csv", lineterminator="\n")

    table6 = pd.read_csv(RAW_DIR / "bls_table6_october_2026.csv")
    effects = table6.set_index("component")["effect_pp"]
    food = float(effects.loc["food"])
    energy = float(effects.loc["energy"])
    shelter = float(effects.loc["shelter"])
    core = float(effects.loc["core"])
    less_shelter = float(effects.loc["all_items_less_shelter"])
    core_ex_shelter = core - shelter
    published_sum = food + energy + core
    identity_sum = food + energy + shelter + core_ex_shelter
    if abs(identity_sum - published_sum) > 1e-9:
        raise RuntimeError("The core-excluding-shelter residual does not match the core effect.")
    if abs((shelter + less_shelter) - published_sum) > 1e-9:
        raise RuntimeError("Shelter plus all-items-less-shelter does not match food, energy, and core.")

    bars = pd.DataFrame(
        [
            {"component": "Food", "effect_pp": food, "order": 1},
            {"component": "Energy", "effect_pp": energy, "order": 2},
            {"component": "Shelter", "effect_pp": shelter, "order": 3},
            {"component": "Core excluding shelter", "effect_pp": core_ex_shelter, "order": 4},
        ]
    )
    bars.to_csv(CLEAN_DIR / "cpi_contributions.csv", index=False, lineterminator="\n")

    require(cpi, "cpi_mom", OCT, "0.4")
    require(cpi, "cpi_mom", SEP, "0.6")
    require(cpi, "cpi_core_mom", OCT, "0.3")
    require(cpi, "cpi_food_mom", OCT, "0.5")
    require(cpi, "cpi_energy_mom", OCT, "0.7")
    require(cpi, "cpi_energy_mom", SEP, "5.2")
    require(cpi, "cpi_shelter_mom", OCT, "0.3")
    require(cpi, "cpi_rent_mom", OCT, "0.2")
    require(cpi, "cpi_oer_mom", OCT, "0.3")
    require(cpi, "cpi_gasoline_mom", OCT, "1.0")
    require(cpi, "cpi_gasoline_nsa_mom", OCT, "-0.7")
    require(cpi, "cpi_nsa_mom", OCT, "0.2")
    require(cpi, "cpi_yoy", SEP, "3.7")
    require(cpi, "cpi_core_yoy", SEP, "2.6")
    require_missing(cpi, "cpi_yoy", OCT)
    require_missing(cpi, "cpi_core_yoy", OCT)

    require(ppi, "ppi_mom", OCT, "0.3")
    require(ppi, "ppi_mom", SEP, "1.4")
    require(ppi, "ppi_yoy", OCT, "6.5")
    require(ppi, "ppi_core_mom", OCT, "0.5")
    require(ppi, "ppi_core_yoy", OCT, "4.9")
    require(ppi, "ppi_goods_mom", OCT, "0.5")
    require(ppi, "ppi_goods_yoy", OCT, "10.2")
    require(ppi, "ppi_services_mom", OCT, "0.2")
    require(ppi, "ppi_foods_mom", OCT, "1.3")
    require(ppi, "ppi_energy_mom", OCT, "-0.1")
    require(ppi, "ppi_goods_ex_food_energy_mom", OCT, "0.5")

    require(pce, "pce_mom", SEP, "0.5")
    require(pce, "pce_yoy", SEP, "3.6")
    require(pce, "pce_yoy", AUG, "3.4")
    require(pce, "core_pce_mom", SEP, "0.3")
    require(pce, "core_pce_yoy", SEP, "3.1")
    require(pce, "core_pce_yoy", AUG, "3.0")
    require(earnings, "ahe_mom", OCT, "0.4")
    require(earnings, "ahe_yoy", OCT, "3.1")

    q3 = pd.Timestamp("2026-07-01")
    if float(prod.loc[q3, "prod_q_ann"]) != 3.6:
        raise RuntimeError("Q3 productivity is not 3.6.")
    if float(prod.loc[q3, "prod_yoy"]) != 2.1:
        raise RuntimeError("Four-quarter productivity is not 2.1.")
    if float(prod.loc[q3, "ulc_q_ann"]) != -0.7:
        raise RuntimeError("Q3 unit labor costs are not -0.7.")
    if float(prod.loc[q3, "ulc_yoy"]) != 2.4:
        raise RuntimeError("Four-quarter unit labor costs are not 2.4.")

    unrounded = float(cpi.loc[OCT, "cpi_mom"])
    gap_months = cpi.index[cpi["headline_sa"].isna()].strftime("%Y-%m").tolist()
    log = {
        "published_effect_sum": published_sum,
        "unrounded_cpi_mom": unrounded,
        "shelter_effect": shelter,
        "core_ex_shelter_effect": core_ex_shelter,
        "share_of_rounded_0_4": shelter / 0.4 * 100,
        "share_of_unrounded_month": shelter / unrounded * 100,
        "missing_headline_months": gap_months,
        "missing_core_three_month_windows": cpi.index[
            cpi["cpi_core_ann3"].isna() & (cpi.index >= OCT_2025)
        ].strftime("%Y-%m").tolist(),
    }
    (CLEAN_DIR / "contribution_check.json").write_text(
        json.dumps(log, indent=2) + "\n", encoding="utf-8"
    )
    print("Clean files written. Locked prints match.")
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
