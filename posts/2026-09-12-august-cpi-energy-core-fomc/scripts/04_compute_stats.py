"""
04_compute_stats.py
===================
STEP 3 of the data pipeline (there is no 03).

What this script does
---------------------
Writes stats/summary_stats.json, the only number source the QMD prose and
metric cards are allowed to use. Keys must match index.qmd.

Latest versus previous month: after sorting by date, the August 2026 row is
the print this post is about. July is the prior month. Rounding: CPI rates
keep one decimal to match BLS Table 1. Contribution approximations keep two
decimals. The funds target keeps two decimals.

Prose-facing calendar dates use US month/day with no required leading zeros
(9/11, 9/12/2026). Do not invent date strings in the QMD.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
RAW_DIR = POST_DIR / "data" / "raw"
STATS_DIR = POST_DIR / "stats"
AUGUST = pd.Timestamp("2026-08-01")
JULY = pd.Timestamp("2026-07-01")

# MANUAL: BLS and Fed calendars, cited in Methodology.
# https://www.bls.gov/schedule/news_release/cpi.htm
# https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
# https://www.bea.gov/news/schedule
CPI_RELEASE_DATE = "9/11/2026"
DATA_CURRENT_AS_OF = "9/12/2026"
NEXT_FOMC_DATES = "9/15 to 9/16"
NEXT_FOMC_DECISION_DATE = "9/16"
NEXT_PCE_DATE = "9/30"
NEXT_CPI_DATE = "10/14"
RELEASE_TIME = "8:30 a.m. ET"

# MANUAL: June 2026 SEP median year-end 2026 federal funds rate, percent.
# https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260617.htm
JUNE_SEP_2026_FUNDS_MEDIAN = 3.8

# MANUAL: July 2026 PCE y/y from the prior gilboa.blog PCE post / BEA.
# https://www.bea.gov/data/personal-consumption-expenditures-price-index
JULY_PCE_HEADLINE_YOY = 3.7
JULY_PCE_CORE_YOY = 3.3

# MANUAL: August 2026 nonfarm payroll change, thousands of jobs.
# https://www.bls.gov/news.release/empsit.nr0.htm
AUGUST_PAYROLL_K = 162.0


def r1(value: float) -> float:
    return round(float(value), 1)


def r2(value: float) -> float:
    return round(float(value), 2)


def us_month_year(ts: pd.Timestamp) -> str:
    return f"{ts.month}/{ts.year}"


def main() -> None:
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    history = pd.read_csv(CLEAN_DIR / "cpi_history.csv", index_col="date", parse_dates=True)
    history = history.sort_index()
    contributions = pd.read_csv(CLEAN_DIR / "august_contributions.csv").set_index("component")
    release = pd.read_csv(CLEAN_DIR / "bls_release_table.csv").set_index("component")
    policy = pd.read_csv(RAW_DIR / "fred_policy_daily.csv", index_col="date", parse_dates=True)

    august = history.loc[AUGUST]
    july = history.loc[JULY]
    headline_mom = r1(release.loc["all_items", "august_mom_sa"])
    gasoline_contrib_raw = float(contributions["gasoline_contrib_pp"].iloc[0])
    gasoline_contrib = r2(gasoline_contrib_raw)
    contrib_total = r2(contributions["contribution_pp"].sum())
    payroll_k = round(float(AUGUST_PAYROLL_K))

    gap_months = [
        us_month_year(stamp)
        for stamp, row in history.loc["2021-01-01":AUGUST, ["headline_sa", "core_sa"]].iterrows()
        if row.isna().any()
    ]

    stats = {
        "latest_month": "August 2026",
        "latest_month_short": "Aug 2026",
        "previous_month": "July 2026",
        "data_current_as_of": DATA_CURRENT_AS_OF,
        "cpi_release_date": CPI_RELEASE_DATE,
        "next_fomc_dates": NEXT_FOMC_DATES,
        "next_fomc_decision_date": NEXT_FOMC_DECISION_DATE,
        "next_pce_date": NEXT_PCE_DATE,
        "next_cpi_date": NEXT_CPI_DATE,
        "release_time": RELEASE_TIME,
        "inflation_reference": 2.0,
        "headline_mom": headline_mom,
        "headline_yoy": r1(release.loc["all_items", "august_yoy_nsa"]),
        "headline_july_mom": r1(release.loc["all_items", "july_mom_sa"]),
        "headline_july_yoy": r1(july["headline_yoy"]),
        "headline_mom_accel_pp": r1(
            release.loc["all_items", "august_mom_sa"] - release.loc["all_items", "july_mom_sa"]
        ),
        "headline_ann3": r1(august["headline_ann3"]),
        "headline_ann6": r1(august["headline_ann6"]),
        "core_mom": r1(release.loc["core", "august_mom_sa"]),
        "core_yoy": r1(release.loc["core", "august_yoy_nsa"]),
        "core_july_mom": r1(release.loc["core", "july_mom_sa"]),
        "core_july_yoy": r1(july["core_yoy"]),
        "core_mom_accel_pp": r1(
            release.loc["core", "august_mom_sa"] - release.loc["core", "july_mom_sa"]
        ),
        "core_ann3": r1(august["core_ann3"]),
        "core_ann6": r1(august["core_ann6"]),
        "food_mom": r1(release.loc["food", "august_mom_sa"]),
        "food_yoy": r1(release.loc["food", "august_yoy_nsa"]),
        "energy_mom": r1(release.loc["energy", "august_mom_sa"]),
        "energy_july_mom": r1(release.loc["energy", "july_mom_sa"]),
        "energy_yoy": r1(release.loc["energy", "august_yoy_nsa"]),
        "gasoline_mom": r1(release.loc["gasoline", "august_mom_sa"]),
        "gasoline_july_mom": r1(release.loc["gasoline", "july_mom_sa"]),
        "gasoline_yoy": r1(release.loc["gasoline", "august_yoy_nsa"]),
        "core_goods_mom": r1(release.loc["core_goods", "august_mom_sa"]),
        "core_goods_yoy": r1(release.loc["core_goods", "august_yoy_nsa"]),
        "services_less_energy_mom": r1(release.loc["services_less_energy", "august_mom_sa"]),
        "services_less_energy_yoy": r1(release.loc["services_less_energy", "august_yoy_nsa"]),
        "services_less_shelter_mom": r1(august["services_less_shelter_mom"]),
        "services_less_shelter_yoy": r1(august["services_less_shelter_yoy"]),
        "services_less_shelter_ann3": r1(august["services_less_shelter_ann3"]),
        "shelter_mom": r1(release.loc["shelter", "august_mom_sa"]),
        "shelter_july_mom": r1(release.loc["shelter", "july_mom_sa"]),
        "shelter_yoy": r1(release.loc["shelter", "august_yoy_nsa"]),
        "shelter_ann3": r1(august["shelter_ann3"]),
        "rent_mom": r1(release.loc["rent", "august_mom_sa"]),
        "rent_yoy": r1(release.loc["rent", "august_yoy_nsa"]),
        "oer_mom": r1(release.loc["oer", "august_mom_sa"]),
        "oer_yoy": r1(release.loc["oer", "august_yoy_nsa"]),
        "contrib_energy_pp": r2(contributions.loc["Energy", "contribution_pp"]),
        "contrib_food_pp": r2(contributions.loc["Food", "contribution_pp"]),
        "contrib_shelter_pp": r2(contributions.loc["Shelter", "contribution_pp"]),
        "contrib_core_goods_pp": r2(contributions.loc["Core goods", "contribution_pp"]),
        "contrib_other_services_pp": r2(contributions.loc["Other services", "contribution_pp"]),
        "contrib_gasoline_pp": gasoline_contrib,
        "contrib_approx_total_pp": contrib_total,
        "contrib_gap_pp": r2(headline_mom - contrib_total),
        "gasoline_share_of_headline_pct": r1(100.0 * gasoline_contrib_raw / headline_mom),
        "fed_target_lower": r2(policy["fed_target_lower"].dropna().iloc[-1]),
        "fed_target_upper": r2(policy["fed_target_upper"].dropna().iloc[-1]),
        "june_sep_2026_funds_median": JUNE_SEP_2026_FUNDS_MEDIAN,
        "july_pce_headline_yoy": JULY_PCE_HEADLINE_YOY,
        "july_pce_core_yoy": JULY_PCE_CORE_YOY,
        "august_payroll_k": float(payroll_k),
        "august_payroll": f"{payroll_k * 1000:,.0f}",
        "fred_gap_months": ", ".join(gap_months) if gap_months else "none",
        "bls_release_url": "https://www.bls.gov/news.release/cpi.nr0.htm",
        "bls_table1_url": "https://www.bls.gov/news.release/cpi.t01.htm",
        "fred_url": "https://fred.stlouisfed.org/",
        "fomc_calendar_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "june_sep_url": "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260617.htm",
        "bea_schedule_url": "https://www.bea.gov/news/schedule",
        "release_note": (
            f"BLS CPI for August 2026 was released {CPI_RELEASE_DATE}. "
            f"FRED histories were current through August 2026 when checked {DATA_CURRENT_AS_OF}."
        ),
    }

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    (STATS_DIR / "summary_stats.json").write_text(
        json.dumps(stats, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(stats)} stats to {STATS_DIR / 'summary_stats.json'}")
    print(
        "August CPI: "
        f"headline {stats['headline_mom']:+.1f}% m/m, {stats['headline_yoy']:.1f}% y/y; "
        f"core {stats['core_mom']:+.1f}% m/m, {stats['core_yoy']:.1f}% y/y"
    )
    print(f"FRED headline/core gap months: {stats['fred_gap_months']}")


if __name__ == "__main__":
    main()
