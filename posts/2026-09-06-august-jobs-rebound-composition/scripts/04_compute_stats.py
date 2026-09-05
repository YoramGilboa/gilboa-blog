"""
04_compute_stats.py
===================
STEP 3 of the data pipeline (there is no 03).

What this script does
---------------------
Writes stats/summary_stats.json, the only number source the QMD prose and
metric cards are allowed to use. Keys must match index.qmd.

Latest versus previous month: after sorting by date, the last non-null
August 2026 row is the print this post is about. July is the prior month.
Rounding: job changes are stored in thousands with one decimal when the
source series has a decimal; headline CES totals are whole thousands.
Percents keep one decimal. Dollar earnings keep two decimals.

First-print revisions are not in FRED (FRED stores the current vintage).
Those two starting prints are pinned from the BLS release text.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"

AUGUST = pd.Timestamp("2026-08-01")
JULY = pd.Timestamp("2026-07-01")
JUNE = pd.Timestamp("2026-06-01")
JANUARY = pd.Timestamp("2026-01-01")
DECEMBER_2025 = pd.Timestamp("2025-12-01")

# MANUAL: BLS Employment Situation, August 2026, released 9/4/2026.
# https://www.bls.gov/news.release/empsit.nr0.htm
# FRED PAYEMS is the current vintage, so it already includes these revisions.
# The first prints are only in the release text.
JUNE_INITIAL_K = 20.0
JULY_INITIAL_K = -23.0

# MANUAL: BLS release calendar and Fed calendar, cited in the post methodology.
# https://www.bls.gov/schedule/news_release/cpi.htm
# https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
NEXT_CPI_DATE = "9/11"
NEXT_FOMC_DATE = "9/16"
NEXT_JOBS_DATE = "10/2"
BLS_RELEASE_DATE = "9/4/2026"


def round0(value: float) -> float:
    """Nearest thousand jobs. Matches the BLS release integers."""
    return float(round(float(value)))


def round1(value: float) -> float:
    return round(float(value), 1)


def round2(value: float) -> float:
    return round(float(value), 2)


def us_month_year(ts: pd.Timestamp) -> str:
    """Prose-facing month/year with no leading zeros, e.g. 7/2026."""
    return f"{ts.month}/{ts.year}"


def us_date(ts: pd.Timestamp) -> str:
    """Prose-facing month/day/year with no leading zeros, e.g. 8/29/2026."""
    return f"{ts.month}/{ts.day}/{ts.year}"


def main() -> None:
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    labor = pd.read_csv(CLEAN_DIR / "labor_monthly.csv", index_col="date", parse_dates=True)
    labor = labor.sort_index()
    claims = pd.read_csv(CLEAN_DIR / "claims_weekly.csv", index_col="date", parse_dates=True)
    claims = claims.sort_index()

    if AUGUST not in labor.index:
        raise RuntimeError("labor_monthly.csv has no August 2026 row")

    aug = labor.loc[AUGUST]
    jul = labor.loc[JULY]
    jan = labor.loc[JANUARY]

    prior_12 = labor.loc[:JULY, "payems_chg"].dropna().tail(12)
    food_12 = labor.loc[:JULY, "food_services_chg"].dropna().tail(12)
    health_12 = labor.loc[:JULY, "healthcare_chg"].dropna().tail(12)
    info_12 = labor.loc[:JULY, "information_chg"].dropna().tail(12)

    june_revised = round0(labor.loc[JUNE, "payems_chg"])
    july_revised = round0(labor.loc[JULY, "payems_chg"])
    june_revision = round0(june_revised - JUNE_INITIAL_K)
    july_revision = round0(july_revised - JULY_INITIAL_K)

    food = round0(aug["food_services_chg"])
    local_edu = round0(aug["local_education_chg"])
    construction = round0(aug["construction_chg"])
    manufacturing = round0(aug["manufacturing_chg"])
    healthcare = round0(aug["healthcare_chg"])
    information = round0(aug["information_chg"])
    two_sector = food + local_edu
    two_sector_jul = round0(jul["food_services_chg"]) + round0(jul["local_education_chg"])
    rest_aug = round0(aug["payems_chg"] - (aug["food_services_chg"] + aug["local_education_chg"]))
    rest_jul = round0(jul["payems_chg"] - (jul["food_services_chg"] + jul["local_education_chg"]))
    payroll = round0(aug["payems_chg"])
    listed = food + local_edu + construction + manufacturing + healthcare + information
    leisure = round0(aug["leisure_chg"])
    food_share_of_leisure_pct = round1(100.0 * food / leisure) if leisure else None

    jolts_openings = labor["jolts_openings"].dropna()
    jolts_quits = labor["jolts_quits_rate"].dropna()
    claims_latest = claims["initial_claims"].dropna()

    stats = {
        "latest_month": "August 2026",
        "latest_month_short": "Aug 2026",
        "data_current_as_of": BLS_RELEASE_DATE,
        "release_note": (
            "The August Employment Situation is preliminary and will be revised."
        ),
        "bls_release_date": BLS_RELEASE_DATE,
        "payroll_aug_k": payroll,
        "private_aug_k": round0(aug["uspriv_chg"]),
        "government_aug_k": round0(aug["usgovt_chg"]),
        "food_services_aug_k": food,
        "food_services_12m_avg_k": round0(food_12.mean()),
        "local_education_aug_k": local_edu,
        "manufacturing_aug_k": manufacturing,
        "manufacturing_since_dec_k": round0(
            labor.loc[AUGUST, "manufacturing"] - labor.loc[DECEMBER_2025, "manufacturing"]
        ),
        "manufacturing_low_month": us_month_year(DECEMBER_2025),
        "construction_aug_k": construction,
        "healthcare_aug_k": healthcare,
        "healthcare_12m_avg_k": round0(health_12.mean()),
        "information_aug_k": information,
        "information_12m_avg_k": round0(info_12.mean()),
        "leisure_aug_k": leisure,
        "food_share_of_leisure_pct": food_share_of_leisure_pct,
        "local_education_jul_k": round0(jul["local_education_chg"]),
        "two_sector_sum_k": two_sector,
        "two_sector_jul_k": two_sector_jul,
        "two_sector_share_pct": round1(100.0 * two_sector / payroll),
        "rest_aug_k": rest_aug,
        "rest_jul_k": rest_jul,
        "all_other_aug_k": round0(payroll - listed),
        "july_initial_k": JULY_INITIAL_K,
        "july_revised_k": july_revised,
        "july_revision_k": july_revision,
        "june_initial_k": JUNE_INITIAL_K,
        "june_revised_k": june_revised,
        "june_revision_k": june_revision,
        "combined_revision_k": round0(june_revision + july_revision),
        "prior_12m_avg_k": round0(prior_12.mean()),
        "payroll_3m_avg_k": round0(aug["payroll_3m_avg"]),
        "unrate_aug": round1(aug["unrate"]),
        "unrate_jul": round1(jul["unrate"]),
        "u6_aug": round1(aug["u6rate"]),
        "u6_jul": round1(jul["u6rate"]),
        "participation_aug": round1(aug["civpart"]),
        "participation_jul": round1(jul["civpart"]),
        "participation_jan": round1(jan["civpart"]),
        "participation_change_since_jan_pp": round1(aug["civpart"] - jan["civpart"]),
        "emp_pop_aug": round1(aug["emratio"]),
        "emp_pop_jul": round1(jul["emratio"]),
        "labor_force_chg_k": round0(aug["labor_force_chg"]),
        "employed_chg_k": round0(aug["employed_chg"]),
        "unemployed_chg_k": round0(aug["unemployed_chg"]),
        "nilf_chg_k": round0(aug["nilf_chg"]),
        "unemployed_level_k": round0(aug["unemployed"]),
        "unemployed_level_m": round1(aug["unemployed"] / 1000.0),
        "pte_economic_k": round0(aug["pte_economic"]),
        "pte_economic_m": round1(aug["pte_economic"] / 1000.0),
        "pte_economic_chg_k": round0(aug["pte_economic_chg"]),
        "ahe_level": round2(aug["ahe"]),
        "ahe_mom_pct": round1(aug["ahe_mom"]),
        "ahe_yoy_pct": round1(aug["ahe_yoy"]),
        "ahe_mom_cents": round0((aug["ahe"] - jul["ahe"]) * 100.0),
        "ahe_prod_level": round2(aug["ahe_prod"]),
        "ahe_prod_mom_pct": round1(aug["ahe_prod_mom"]),
        "ahe_prod_mom_cents": round0((aug["ahe_prod"] - jul["ahe_prod"]) * 100.0),
        "hours_level": round1(aug["hours"]),
        "hours_prev": round1(jul["hours"]),
        "hours_chg": round1(aug["hours"] - jul["hours"]),
        "jolts_openings_k": round0(jolts_openings.iloc[-1]),
        "jolts_openings_m": round1(jolts_openings.iloc[-1] / 1000.0),
        "jolts_openings_month": us_month_year(jolts_openings.index[-1]),
        "jolts_quits_rate": round1(jolts_quits.iloc[-1]),
        "claims_latest_k": round(float(claims_latest.iloc[-1]) / 1000.0, 0),
        "claims_as_of": us_date(claims_latest.index[-1]),
        "next_cpi_date": NEXT_CPI_DATE,
        "next_fomc_date": NEXT_FOMC_DATE,
        "next_jobs_date": NEXT_JOBS_DATE,
    }

    out = STATS_DIR / "summary_stats.json"
    out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print("Wrote", out)
    print("payroll_aug_k", stats["payroll_aug_k"])
    print("two_sector_share_pct", stats["two_sector_share_pct"])
    print("unrate_aug", stats["unrate_aug"])
    print("ahe_yoy_pct", stats["ahe_yoy_pct"])


if __name__ == "__main__":
    main()
