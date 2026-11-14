"""
04_compute_stats.py
===================
STEP 3 of the data pipeline. There is no script 03.

What this script does
---------------------
Writes stats/summary_stats.json, the only file the post may quote.
Rates are rounded half away from zero to one decimal, except Table 6
effects, which stay at the published three decimals.

latest_month is the CPI and PPI month, October 2026.
The previous CPI month is September 2026.
PCE stops at September 2026 because October PCE is not published.
Productivity is the third quarter of 2026.

cpi_yoy and cpi_core_yoy are null. BLS did not publish those October
12-month rates. shelter_share_of_month is also null: 0.108 / 0.4 is
27 percent, which is not the release's "over thirty percent." The two
explicit shares are stored beside it. Prose must not treat the null as zero.
"""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
RAW_DIR = POST_DIR / "data" / "raw"
STATS_DIR = POST_DIR / "stats"
OCT = pd.Timestamp("2026-10-01")
SEP = pd.Timestamp("2026-09-01")
AUG = pd.Timestamp("2026-08-01")
Q3 = pd.Timestamp("2026-07-01")


def one_decimal(value: float) -> float:
    """Round half away from zero to one decimal place."""
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def three_decimals(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def at(frame: pd.DataFrame, column: str, stamp: pd.Timestamp) -> float:
    value = frame.loc[stamp, column]
    if pd.isna(value):
        raise RuntimeError(f"{column} is missing on {stamp.date()}.")
    return one_decimal(float(value))


def main() -> None:
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    cpi = pd.read_csv(CLEAN_DIR / "cpi_monthly.csv", index_col="date", parse_dates=True)
    ppi = pd.read_csv(CLEAN_DIR / "ppi_monthly.csv", index_col="date", parse_dates=True)
    pce = pd.read_csv(CLEAN_DIR / "pce_monthly.csv", index_col="date", parse_dates=True)
    earnings = pd.read_csv(CLEAN_DIR / "earnings_monthly.csv", index_col="date", parse_dates=True)
    prod = pd.read_csv(CLEAN_DIR / "productivity_quarterly.csv", index_col="date", parse_dates=True)
    funds = pd.read_csv(RAW_DIR / "fred_funds_monthly.csv", index_col="date", parse_dates=True)
    manual = json.loads((RAW_DIR / "manual_prints.json").read_text(encoding="utf-8"))
    check = json.loads((CLEAN_DIR / "contribution_check.json").read_text(encoding="utf-8"))
    table6 = pd.read_csv(RAW_DIR / "bls_table6_october_2026.csv").set_index("component")

    oct_yoy = cpi.loc[OCT, "cpi_yoy"]
    oct_core_yoy = cpi.loc[OCT, "cpi_core_yoy"]
    if pd.notna(oct_yoy) or pd.notna(oct_core_yoy):
        raise RuntimeError("October CPI 12-month rates must be null.")

    stats = {
        "gap_month": "October 2025",
        "following_gap_month": "November 2025",
        "april_rent_month": "April 2026",
        "latest_month": "October 2026",
        "latest_month_short": "October 2026",
        "data_current_as_of": "11/13/2026",
        "cpi_release_date": "11/10/2026",
        "ppi_release_date": "11/13/2026",
        "productivity_release_date": "11/5/2026",
        "pce_release_date": "10/29/2026",
        "ahe_release_date": "11/6/2026",
        "cpi_yoy_published": False,
        "october_pce_status": "not yet released",
        "october_retail_sales_status": "not yet released",
        "retail_sales_date": "11/17/2026",
        "minutes_date": "11/18/2026",
        "next_pce_date": "11/25/2026",
        "gdp_second_date": "11/25/2026",
        "fomc_start_date": "12/8/2026",
        "fomc_end_date": "12/9/2026",
        "productivity_revised_date": "12/8/2026",
        "next_cpi_date": "12/10/2026",
        "cpi_mom": at(cpi, "cpi_mom", OCT),
        "cpi_sep_mom": at(cpi, "cpi_mom", SEP),
        "cpi_core_mom": at(cpi, "cpi_core_mom", OCT),
        "cpi_shelter_mom": at(cpi, "cpi_shelter_mom", OCT),
        "cpi_oer_mom": at(cpi, "cpi_oer_mom", OCT),
        "cpi_rent_mom": at(cpi, "cpi_rent_mom", OCT),
        "cpi_food_mom": at(cpi, "cpi_food_mom", OCT),
        "cpi_food_home_mom": one_decimal(float(table6.loc["food_at_home", "percent_change"])),
        "cpi_food_away_mom": one_decimal(float(table6.loc["food_away", "percent_change"])),
        "cpi_energy_mom": at(cpi, "cpi_energy_mom", OCT),
        "cpi_energy_sep_mom": at(cpi, "cpi_energy_mom", SEP),
        "cpi_gasoline_mom": at(cpi, "cpi_gasoline_mom", OCT),
        "cpi_gasoline_nsa_mom": at(cpi, "cpi_gasoline_nsa_mom", OCT),
        "cpi_nsa_mom": at(cpi, "cpi_nsa_mom", OCT),
        "cpi_yoy": None,
        "cpi_core_yoy": None,
        "cpi_sep_yoy": at(cpi, "cpi_yoy", SEP),
        "cpi_core_sep_yoy": at(cpi, "cpi_core_yoy", SEP),
        "cpi_ann3": at(cpi, "cpi_ann3", OCT),
        "cpi_core_ann3": at(cpi, "cpi_core_ann3", OCT),
        "shelter_effect": three_decimals(check["shelter_effect"]),
        "food_effect": three_decimals(float(table6.loc["food", "effect_pp"])),
        "energy_effect": three_decimals(float(table6.loc["energy", "effect_pp"])),
        "core_ex_shelter_effect": three_decimals(check["core_ex_shelter_effect"]),
        "shelter_share_of_month": None,
        "shelter_share_of_rounded_month": one_decimal(check["share_of_rounded_0_4"]),
        "shelter_share_of_unrounded_month": one_decimal(check["share_of_unrounded_month"]),
        "cpi_mom_unrounded": three_decimals(check["unrounded_cpi_mom"]),
        "effects_sum": three_decimals(check["published_effect_sum"]),
        "ppi_mom": at(ppi, "ppi_mom", OCT),
        "ppi_sep_mom": at(ppi, "ppi_mom", SEP),
        "ppi_sep_mom_previously_published": one_decimal(manual["ppi_sep_mom_previously_published"]),
        "ppi_yoy": at(ppi, "ppi_yoy", OCT),
        "ppi_core_mom": at(ppi, "ppi_core_mom", OCT),
        "ppi_core_yoy": at(ppi, "ppi_core_yoy", OCT),
        "ppi_goods_mom": at(ppi, "ppi_goods_mom", OCT),
        "ppi_goods_yoy": at(ppi, "ppi_goods_yoy", OCT),
        "ppi_services_mom": at(ppi, "ppi_services_mom", OCT),
        "ppi_services_yoy": at(ppi, "ppi_services_yoy", OCT),
        "ppi_foods_mom": at(ppi, "ppi_foods_mom", OCT),
        "ppi_energy_mom": at(ppi, "ppi_energy_mom", OCT),
        "ppi_goods_ex_food_energy_mom": at(ppi, "ppi_goods_ex_food_energy_mom", OCT),
        "prod_q_ann": float(prod.loc[Q3, "prod_q_ann"]),
        "prod_yoy": float(prod.loc[Q3, "prod_yoy"]),
        "output_q_ann": one_decimal(manual["output_q_ann"]),
        "hours_q_ann": one_decimal(manual["hours_q_ann"]),
        "ulc_q_ann": float(prod.loc[Q3, "ulc_q_ann"]),
        "ulc_yoy": float(prod.loc[Q3, "ulc_yoy"]),
        "hourly_comp_q_ann": one_decimal(manual["hourly_comp_q_ann"]),
        "hourly_comp_yoy": one_decimal(manual["hourly_comp_yoy"]),
        "real_comp_q_ann": one_decimal(manual["real_comp_q_ann"]),
        "pce_mom": at(pce, "pce_mom", SEP),
        "pce_yoy": at(pce, "pce_yoy", SEP),
        "core_pce_mom": at(pce, "core_pce_mom", SEP),
        "core_pce_yoy": at(pce, "core_pce_yoy", SEP),
        "core_pce_yoy_prior": at(pce, "core_pce_yoy", AUG),
        "ahe_mom": at(earnings, "ahe_mom", OCT),
        "ahe_yoy": at(earnings, "ahe_yoy", OCT),
        "ahe_level": float(earnings.loc[OCT, "ahe_level"]),
        "funds_lower": float(funds["funds_lower"].dropna().iloc[-1]),
        "funds_upper": float(funds["funds_upper"].dropna().iloc[-1]),
        "sep_end_2026_median": one_decimal(manual["sep_end_2026_median"]),
        "fed_target": 2.0,
        "release_note": "CPI released 11/10/2026. PPI released 11/13/2026. October PCE is not yet released.",
    }

    planned = """
    latest_month latest_month_short data_current_as_of cpi_release_date ppi_release_date
    productivity_release_date pce_release_date ahe_release_date cpi_yoy_published october_pce_status
    retail_sales_date minutes_date next_pce_date gdp_second_date fomc_start_date fomc_end_date
    productivity_revised_date next_cpi_date cpi_mom cpi_sep_mom cpi_core_mom cpi_shelter_mom
    cpi_oer_mom cpi_rent_mom cpi_food_mom cpi_food_home_mom cpi_food_away_mom cpi_energy_mom
    cpi_energy_sep_mom cpi_gasoline_mom cpi_gasoline_nsa_mom cpi_nsa_mom cpi_yoy cpi_core_yoy
    cpi_sep_yoy cpi_core_sep_yoy cpi_ann3 cpi_core_ann3 shelter_effect food_effect energy_effect
    core_ex_shelter_effect shelter_share_of_month ppi_mom ppi_sep_mom ppi_sep_mom_previously_published
    ppi_yoy ppi_core_mom ppi_core_yoy ppi_goods_mom ppi_goods_yoy ppi_services_mom ppi_foods_mom
    ppi_energy_mom ppi_goods_ex_food_energy_mom prod_q_ann prod_yoy output_q_ann hours_q_ann
    ulc_q_ann ulc_yoy hourly_comp_q_ann hourly_comp_yoy real_comp_q_ann pce_mom pce_yoy
    core_pce_mom core_pce_yoy core_pce_yoy_prior ahe_mom ahe_yoy ahe_level funds_lower funds_upper
    sep_end_2026_median
    """.split()
    missing = [key for key in planned if key not in stats]
    if missing:
        raise RuntimeError(f"Missing stats keys: {missing}")

    (STATS_DIR / "summary_stats.json").write_text(
        json.dumps(stats, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(stats)} stats keys. Planned keys present: {len(planned)}.")


if __name__ == "__main__":
    main()
