"""
Step 3 of 3: write every prose and metric-card value to summary_stats.json.

index.qmd reads only this file for numbers. If a figure is not here, it must
not appear as a hard-coded value in the post.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"


def r1(value: float) -> float:
    return round(float(value), 1)


def r0(value: float) -> float:
    return round(float(value), 0)


def r2(value: float) -> float:
    return round(float(value), 2)


def md(value) -> str:
    """Paragraph date: 8/19, not 08/19/2026."""
    stamp = pd.Timestamp(value)
    return f"{stamp.month}/{stamp.day}"


def mdyy(value) -> str:
    """Paragraph date with short year when the year is needed: 8/21/26."""
    stamp = pd.Timestamp(value)
    return f"{stamp.month}/{stamp.day}/{stamp.strftime('%y')}"


def main() -> None:
    inflation = pd.read_csv(CLEAN_DIR / "inflation.csv", index_col="date", parse_dates=True)
    labor = pd.read_csv(CLEAN_DIR / "labor.csv", index_col="date", parse_dates=True)
    activity = pd.read_csv(CLEAN_DIR / "activity.csv", index_col="date", parse_dates=True)
    rates = pd.read_csv(CLEAN_DIR / "rates_daily.csv", index_col="date", parse_dates=True)
    fedwatch = pd.read_csv(CLEAN_DIR / "fedwatch.csv")

    cpi_date = inflation["cpi_headline_release_yoy"].dropna().index[-1]
    cpi_prev = inflation.loc[:cpi_date, "cpi_headline_release_yoy"].dropna().index[-2]
    pce_date = inflation["pce_core_yoy"].dropna().index[-1]
    labor_date = labor["payroll_change_k"].dropna().index[-1]
    activity_date = activity["retail_sales_mom"].dropna().index[-1]
    starts_date = activity["housing_starts"].dropna().index[-1]
    latest_cpi = inflation.loc[cpi_date]
    previous_cpi = inflation.loc[cpi_prev]
    latest_pce = inflation.loc[pce_date]
    latest_labor = labor.loc[labor_date]
    latest_activity = activity.loc[activity_date]
    latest_starts = activity.loc[starts_date]

    # MANUAL: July 2026 Employment Situation first prints and revisions.
    # FRED PAYEMS is the current vintage, so first-print history is documented
    # here from the BLS release rather than inferred from the revised series.
    # https://www.bls.gov/news.release/empsit.htm
    bls_may_initial_k = 129.0
    bls_june_initial_k = 57.0
    bls_may_revised_k = 63.0
    bls_june_revised_k = 20.0
    bls_two_month_revision_k = -103.0

    before = fedwatch.loc[fedwatch["snapshot"] == "before_soft_data"].iloc[0]
    after_data = fedwatch.loc[fedwatch["snapshot"] == "after_soft_data"].iloc[0]
    after_minutes = fedwatch.loc[fedwatch["snapshot"] == "after_minutes"].iloc[0]

    # 10-year around the minutes: last value on or before each event date.
    def yield_on_or_before(stamp: str) -> float:
        window = rates.loc[:stamp, "dgs10"].dropna()
        if window.empty:
            raise RuntimeError(f"No 10-year yield on or before {stamp}")
        return float(window.iloc[-1])

    dgs10_latest_date = rates["dgs10"].dropna().index[-1]
    dgs10_latest = float(rates.loc[dgs10_latest_date, "dgs10"])
    dgs10_before_jobs = yield_on_or_before("2026-08-06")
    dgs10_after_cpi = yield_on_or_before("2026-08-12")
    dgs10_after_minutes = yield_on_or_before("2026-08-19")

    fed_lower = float(rates["fed_target_lower"].dropna().iloc[-1])
    fed_upper = float(rates["fed_target_upper"].dropna().iloc[-1])

    stats = {
        "latest_month": cpi_date.strftime("%B %Y"),
        "latest_month_short": cpi_date.strftime("%b %Y"),
        "pce_latest_month": pce_date.strftime("%B %Y"),
        "data_current_as_of": mdyy("2026-08-21"),
        "minutes_release_date": md("2026-08-19"),
        "fomc_meeting_dates": f"{md('2026-07-28')}-{md('2026-07-29')}",
        "fomc_decision_date": md("2026-07-29"),
        "jobs_release_date": md("2026-08-07"),
        "cpi_release_date": md("2026-08-12"),
        "retail_release_date": md("2026-08-14"),
        "housing_release_date": md("2026-08-18"),
        "next_pce_date": md("2026-08-26"),
        "next_jobs_date": md("2026-09-04"),
        "next_cpi_date": md("2026-09-11"),
        "next_fomc_start": md("2026-09-15"),
        "next_fomc_end": md("2026-09-16"),
        "next_fomc_range": f"{md('2026-09-15')}-{md('2026-09-16')}",
        "jackson_hole_timing": "late August",
        "fedwatch_before_md": md("2026-08-06"),
        "fedwatch_after_data_md": md("2026-08-17"),
        "fedwatch_after_minutes_md": md("2026-08-21"),
        "cpi_headline_mom": r1(latest_cpi["cpi_headline_mom"]),
        "cpi_headline_yoy": r1(latest_cpi["cpi_headline_release_yoy"]),
        "cpi_headline_prev_yoy": r1(previous_cpi["cpi_headline_release_yoy"]),
        "cpi_core_mom": r1(latest_cpi["cpi_core_mom"]),
        "cpi_core_yoy": r1(latest_cpi["cpi_core_release_yoy"]),
        "cpi_core_prev_yoy": r1(previous_cpi["cpi_core_release_yoy"]),
        "cpi_energy_mom": r1(latest_cpi["cpi_energy_mom"]),
        "cpi_energy_yoy": r1(latest_cpi["cpi_energy_yoy"]),
        "cpi_food_mom": r1(latest_cpi["cpi_food_mom"]),
        "cpi_shelter_mom": r1(latest_cpi["cpi_shelter_mom"]),
        "cpi_shelter_yoy": r1(latest_cpi["cpi_shelter_yoy"]),
        "cpi_core_goods_mom": r1(latest_cpi["cpi_core_goods_mom"]),
        "pce_headline_yoy": r1(latest_pce["pce_headline_yoy"]),
        "pce_core_yoy": r1(latest_pce["pce_core_yoy"]),
        "contrib_energy_mom_pp": r2(latest_cpi["contrib_energy_mom_pp"]),
        "contrib_food_mom_pp": r2(latest_cpi["contrib_food_mom_pp"]),
        "contrib_core_goods_mom_pp": r2(latest_cpi["contrib_core_goods_mom_pp"]),
        "contrib_shelter_mom_pp": r2(latest_cpi["contrib_shelter_mom_pp"]),
        "contrib_other_services_mom_pp": r2(latest_cpi["contrib_other_services_mom_pp"]),
        "july_payroll_k": r0(latest_labor["payroll_change_k"]),
        "payroll_three_month_avg_k": r0(latest_labor["payroll_three_month_avg_k"]),
        "unrate": r1(latest_labor["unrate"]),
        "civpart": r1(latest_labor["civpart"]),
        "bls_may_initial_k": bls_may_initial_k,
        "bls_june_initial_k": bls_june_initial_k,
        "bls_may_revised_k": bls_may_revised_k,
        "bls_june_revised_k": bls_june_revised_k,
        "bls_two_month_revision_k": bls_two_month_revision_k,
        "retail_sales_mom": r1(latest_activity["retail_sales_mom"]),
        "retail_sales_yoy": r1(latest_activity["retail_sales_yoy"]),
        "housing_starts_k": r0(latest_starts["housing_starts"]),
        "housing_starts_mom": r1(latest_starts["housing_starts_mom"]),
        "fed_target_lower": r2(fed_lower),
        "fed_target_upper": r2(fed_upper),
        "vote_for": 9,
        "vote_against": 3,
        "vote_against_word": "three",
        "vote_against_cap": "Three",
        "vote_split": "9-3",
        "dissent_hike_bp": 25,
        "fedwatch_hike_before": r1(before["sept_hike_prob"]),
        "fedwatch_hold_before": r1(before["sept_hold_prob"]),
        "fedwatch_hike_after_data": r1(after_data["sept_hike_prob"]),
        "fedwatch_hold_after_data": r1(after_data["sept_hold_prob"]),
        "fedwatch_hike_after_minutes": r1(after_minutes["sept_hike_prob"]),
        "fedwatch_hold_after_minutes": r1(after_minutes["sept_hold_prob"]),
        "dgs10_latest": r2(dgs10_latest),
        "dgs10_latest_date": md(dgs10_latest_date),
        "dgs10_before_jobs": r2(dgs10_before_jobs),
        "dgs10_after_cpi": r2(dgs10_after_cpi),
        "dgs10_after_minutes": r2(dgs10_after_minutes),
        "minutes_many_quote": (
            "Many participants assessed that policy tightening would likely "
            "be necessary if inflation did not decline."
        ),
        # MANUAL: Staff figures cited in the July minutes (information set
        # as of the meeting, before the later June PCE revision/publication).
        # https://www.federalreserve.gov/monetarypolicy/fomcminutes20260729.htm
        "minutes_staff_pce_may_yoy": 4.1,
        "minutes_staff_core_pce_may_yoy": 3.4,
    }

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_DIR / "summary_stats.json", "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
