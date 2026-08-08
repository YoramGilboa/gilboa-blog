"""Compute the prose and metric-card values for the July payrolls post."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"
STATS_DIR.mkdir(parents=True, exist_ok=True)


def latest_value(frame: pd.DataFrame, column: str) -> float:
    return float(frame[column].dropna().iloc[-1])


def main() -> None:
    labor = pd.read_csv(CLEAN_DIR / "labor_monthly.csv", parse_dates=["date"]).set_index("date")
    adp = pd.read_csv(CLEAN_DIR / "adp_national.csv", parse_dates=["date"]).set_index("date")
    industries = pd.read_csv(CLEAN_DIR / "adp_industry.csv", parse_dates=["date"])
    pay = pd.read_csv(CLEAN_DIR / "adp_pay_mobility.csv", parse_dates=["date"])
    claims = pd.read_csv(CLEAN_DIR / "claims_weekly.csv", parse_dates=["date"])

    july = pd.Timestamp("2026-07-01")
    may = pd.Timestamp("2026-05-01")
    latest_industries = industries[industries["date"].eq(july)].set_index("category")
    latest_pay = pay[pay["date"].eq(july)].set_index("worker_type")
    changer_pay = pay[pay["worker_type"].eq("Job Changer")].sort_values("date")
    prior_changer_peak_date = changer_pay[
        (changer_pay["date"] < july)
        & (changer_pay["median_pay_change_pct"] >= latest_pay.loc["Job Changer", "median_pay_change_pct"])
    ]["date"].max()

    private_three_month = float(labor.loc[july, "USPRIV"] - labor.loc[may - pd.offsets.MonthBegin(), "USPRIV"])
    edu_health_three_month = float(
        labor.loc[july, "USEHS"] - labor.loc[may - pd.offsets.MonthBegin(), "USEHS"]
    )
    health_social_three_month = float(
        labor.loc[july, "CES6562000001"]
        - labor.loc[may - pd.offsets.MonthBegin(), "CES6562000001"]
    )

    stats = {
        "data_current_as_of": "08/08/2026",
        "adp_release_date": "08/05/2026",
        "bls_release_date": "08/07/2026",
        "adp_july_k": latest_value(adp, "monthly_change_k"),
        "adp_june_k": float(adp.loc["2026-06-01", "monthly_change_k"]),
        "adp_three_month_avg_k": float(adp["monthly_change_k"].tail(3).mean()),
        "adp_edu_health_july_k": float(
            latest_industries.loc["Education and health services", "monthly_change_k"]
        ),
        "adp_edu_health_share_pct": float(
            latest_industries.loc["Education and health services", "monthly_change_k"]
            / latest_value(adp, "monthly_change_k")
            * 100
        ),
        "bls_july_total_k": float(labor["PAYEMS"].diff().loc[july]),
        "bls_july_private_k": float(labor["USPRIV"].diff().loc[july]),
        "bls_june_revised_k": float(labor["PAYEMS"].diff().loc["2026-06-01"]),
        "bls_may_revised_k": float(labor["PAYEMS"].diff().loc["2026-05-01"]),
        "bls_edu_health_july_k": float(labor["USEHS"].diff().loc[july]),
        "bls_health_social_july_k": float(labor["CES6562000001"].diff().loc[july]),
        "bls_social_assistance_july_k": float(labor["CES6562400001"].diff().loc[july]),
        "private_three_month_k": private_three_month,
        "edu_health_three_month_k": edu_health_three_month,
        "health_social_three_month_k": health_social_three_month,
        "edu_health_three_month_share_pct": edu_health_three_month / private_three_month * 100,
        "unemployment_july_pct": float(labor.loc[july, "UNRATE"]),
        "participation_july_pct": float(labor.loc[july, "CIVPART"]),
        "participation_january_pct": float(labor.loc["2026-01-01", "CIVPART"]),
        "participation_change_since_january_pp": float(
            labor.loc[july, "CIVPART"] - labor.loc["2026-01-01", "CIVPART"]
        ),
        "claims_latest_k": latest_value(claims, "initial_claims") / 1000,
        "claims_four_week_k": latest_value(claims, "claims_4wk_avg") / 1000,
        "claims_latest_date": claims["date"].iloc[-1].strftime("%m/%d/%Y"),
        "stayer_pay_pct": float(latest_pay.loc["Job Stayer", "median_pay_change_pct"]),
        "switcher_pay_pct": float(latest_pay.loc["Job Changer", "median_pay_change_pct"]),
        "switcher_prior_peak_month": prior_changer_peak_date.strftime("%B %Y"),
        "switcher_premium_pp": float(
            latest_pay.loc["Job Changer", "median_pay_change_pct"]
            - latest_pay.loc["Job Stayer", "median_pay_change_pct"]
        ),
        "average_hourly_earnings_yoy_pct": float(
            (labor.loc[july, "CES0500000003"] / labor.loc["2025-07-01", "CES0500000003"] - 1)
            * 100
        ),
        "fed_target_lower_pct": 3.5,
        "fed_target_upper_pct": 3.75,
        "fomc_vote_for": 9,
        "fomc_vote_against": 3,
        "next_cpi_date": "08/12/2026",
        "next_jobs_date": "09/04/2026",
        "next_fomc_dates": "09/15/2026-09/16/2026",
        "benchmark_revision_date": "08/28/2026",
        # MANUAL: Dow Jones consensus reported by CNBC on 08/05/2026.
        # Source: https://www.cnbc.com/2026/08/05/private-companies-added-just-44000-workers-in-july-below-expectations-adp-reports.html
        "adp_consensus_k": 75.0,
        # MANUAL: Initial May and June estimates and combined revision from the 08/07/2026 BLS release.
        # Source: https://www.bls.gov/news.release/empsit.nr0.htm
        "bls_may_initial_k": 129.0,
        "bls_june_initial_k": 57.0,
        "bls_two_month_revision_k": -103.0,
    }

    output = STATS_DIR / "summary_stats.json"
    output.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(stats)} summary statistics to {output}.")


if __name__ == "__main__":
    main()