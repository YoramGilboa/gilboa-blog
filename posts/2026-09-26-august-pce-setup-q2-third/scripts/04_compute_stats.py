"""
04_compute_stats.py
===================
STEP 3 of the data pipeline (script 03 is not used).

What this script does
---------------------
Reads the cleaned rates and writes stats/summary_stats.json. The post
reads every number from that file. Nothing in index.qmd is typed by hand.

Rounding
--------
BEA's published monthly and quarterly prints are shown to one decimal.
This script rounds half up, so 3.75 becomes 3.8 and 0.165 becomes 0.17
only when a key asks for two decimals. The monthly 2 percent path is
stored at full precision; the prose formats it to two decimals.

Latest month
------------
The latest monthly row must be July 2026. The previous month is June.
The latest quarter must be 2026 Q2. August and the third estimate are
written as status strings, not as invented numbers.

Locked cross-checks
-------------------
Official July PCE prints and the Q2 second estimate are compared with
the rounded FRED rates. A miss stops the script. The advance-estimate
private-demand figure is not on current FRED (FRED keeps the latest
vintage), so it stays a transcribed BEA table value.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
RAW_DIR = POST_DIR / "data" / "raw"
STATS_DIR = POST_DIR / "stats"

JULY = pd.Timestamp("2026-07-01")
JUNE = pd.Timestamp("2026-06-01")
JULY_PRIOR_YEAR = pd.Timestamp("2025-07-01")
Q2 = pd.Timestamp("2026-04-01")
Q1 = pd.Timestamp("2026-01-01")

# Official prints this pipeline must reproduce. They are checks, not substitutes.
LOCKED_JULY = {
    "pce_headline_yoy": 3.7,
    "pce_headline_mom": 0.2,
    "pce_core_yoy": 3.3,
    "pce_core_mom": 0.2,
    "pi_mom": 0.4,
    "dpi_mom": 0.5,
    "pce_nominal_mom": 0.2,
    "saving_rate": 3.0,
}
LOCKED_GDP = {
    "gdp_q2": 1.5,
    "gdp_q1": 2.1,
    "pdfp_q2": 4.2,
}


def round1(value: float) -> float:
    """One decimal, half up, matching a BEA table rather than banker's rounding."""
    quantized = Decimal(str(round(float(value), 6))).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )
    return float(quantized)


def us_date(year: int, month: int, day: int) -> str:
    """US month/day string without a required leading zero, e.g. 9/30."""
    return f"{month}/{day}"


def main() -> None:
    monthly = pd.read_csv(CLEAN_DIR / "pce_monthly.csv", index_col="date", parse_dates=True)
    quarterly = pd.read_csv(CLEAN_DIR / "gdp_quarterly.csv", index_col="date", parse_dates=True)
    manual = json.loads((RAW_DIR / "manual_priors.json").read_text(encoding="utf-8"))

    if JULY not in monthly.index or JUNE not in monthly.index:
        raise RuntimeError("June or July 2026 is missing from the cleaned monthly file.")
    if Q2 not in quarterly.index or Q1 not in quarterly.index:
        raise RuntimeError("2026 Q1 or Q2 is missing from the cleaned quarterly file.")

    july = monthly.loc[JULY]
    june = monthly.loc[JUNE]
    q2 = quarterly.loc[Q2]
    q1 = quarterly.loc[Q1]

    post_day = date(2026, 9, 26)
    hike_day = date(2026, 9, 17)
    release_day = date(2026, 9, 30)

    # (1.02 ** (1/12) - 1) * 100 is the monthly pace that compounds to 2% a year.
    two_pct_monthly = ((1.02 ** (1 / 12)) - 1) * 100

    stats = {
        "latest_month": "July 2026",
        "latest_month_short": "Jul 2026",
        "previous_month": "June 2026",
        "data_current_as_of": "9/25/2026",
        "history_through_month": "July 2026",
        "pce_release_date": "8/26",
        "gdp_second_release_date": "8/26",
        "next_bea_date": us_date(2026, 9, 30),
        "next_bea_time": "8:30 a.m. ET",
        "post_date": us_date(2026, 9, 26),
        "hike_effective_date": us_date(2026, 9, 17),
        "fomc_statement_date": us_date(2026, 9, 16),
        "fomc_meeting_dates": "9/15 to 9/16",
        "fomc_vline": "2026-09-17",
        "days_since_hike": (post_day - hike_day).days,
        "days_until_release": (release_day - post_day).days,
        "pce_headline_yoy": round1(july["pce_price_yoy"]),
        "pce_headline_mom": round1(july["pce_price_mom"]),
        "pce_core_yoy": round1(july["core_price_yoy"]),
        "pce_core_mom": round1(july["core_price_mom"]),
        "pce_core_ann3": round1(july["core_price_ann3"]),
        "pce_headline_ann3": round1(july["pce_price_ann3"]),
        "pce_headline_prior_yoy": round1(june["pce_price_yoy"]),
        "pce_core_prior_yoy": round1(june["core_price_yoy"]),
        "pce_headline_prior_mom": round1(june["pce_price_mom"]),
        "pce_core_prior_mom": round1(june["core_price_mom"]),
        "pce_headline_mom_year_ago": round1(monthly.loc[JULY_PRIOR_YEAR, "pce_price_mom"]),
        "pce_core_mom_year_ago": round1(monthly.loc[JULY_PRIOR_YEAR, "core_price_mom"]),
        "pi_mom": round1(july["personal_income_mom"]),
        "dpi_mom": round1(july["disposable_pi_mom"]),
        "pce_nominal_mom": round1(july["nominal_pce_mom"]),
        "real_pce_mom": round1(july["real_pce_mom"]),
        "real_pce_yoy": round1(july["real_pce_yoy"]),
        "saving_rate": round1(july["saving_rate"]),
        "saving_rate_prior": round1(june["saving_rate"]),
        "two_pct_monthly": two_pct_monthly,
        "fed_inflation_goal": 2.0,
        "gdp_q2": round1(q2["gdp_saar"]),
        "gdp_q1": round1(q1["gdp_saar"]),
        "pdfp_q2": round1(q2["pdfp_saar"]),
        "pdfp_q1": round1(q1["pdfp_saar"]),
        "pdfp_q2_advance": manual["pdfp_q2_advance"],
        "gdp_q2_advance": manual["gdp_q2_advance"],
        "target_range": manual["target_range"],
        "hike_bp": manual["hike_bp"],
        "sep_funds_2026": manual["sep_funds_2026"],
        "dots_one_more": manual["dots_one_more"],
        "dots_total": manual["dots_total"],
        "cpi_headline_mom": manual["cpi_headline_mom"],
        "cpi_core_mom": manual["cpi_core_mom"],
        "cpi_gasoline_mom": manual["cpi_gasoline_mom"],
        "cpi_month": "August 2026",
        "payroll_aug_k": manual["payroll_aug_k"],
        "test_core_soft_mom": 0.2,
        "test_core_sticky_mom": 0.3,
        "august_pce_status": "TBD, BEA 9/30",
        "q2_third_status": "TBD, BEA 9/30",
        "august_pce_headline_mom": None,
        "august_pce_headline_yoy": None,
        "august_pce_core_mom": None,
        "august_pce_core_yoy": None,
        "august_real_pce_mom": None,
        "august_saving_rate": None,
        "q2_third_gdp": None,
        "q2_third_pdfp": None,
        "revision_window": manual["revision_window"],
        "annual_update_scope": manual["annual_update_scope"],
        "reference_year": manual["reference_year"],
        "jobs_date": us_date(2026, 10, 2),
        "jobs_time": "8:30 a.m. ET",
        "minutes_date": us_date(2026, 10, 7),
        "minutes_time": "2:00 p.m. ET",
        "cpi_next_date": us_date(2026, 10, 14),
        "jolts_date": us_date(2026, 9, 29),
    }
    stats["pdfp_minus_gdp_pp"] = round1(stats["pdfp_q2"] - stats["gdp_q2"])
    stats["release_note"] = (
        "BEA Personal Income and Outlays for July 2026 and the Q2 GDP second "
        "estimate were released 8/26/2026. August PCE, the Q2 third estimate, "
        "and the 2026 annual update are scheduled for 9/30/2026 at 8:30 a.m. ET. "
        "No August PCE or third-estimate figures are in this file."
    )

    mismatches = []
    for key, expected in LOCKED_JULY.items():
        if stats[key] != expected:
            mismatches.append(f"{key}: computed {stats[key]} vs official {expected}")
    for key, expected in LOCKED_GDP.items():
        if stats[key] != expected:
            mismatches.append(f"{key}: computed {stats[key]} vs official {expected}")
    if abs(float(july["real_pce_mom"])) >= 0.1:
        mismatches.append(
            f"real_pce_mom raw {float(july['real_pce_mom']):.3f} is not essentially flat"
        )
    if mismatches:
        raise RuntimeError("Locked prints do not match FRED:\n" + "\n".join(mismatches))

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    (STATS_DIR / "summary_stats.json").write_text(
        json.dumps(stats, indent=2) + "\n",
        encoding="utf-8",
    )

    log_lines = [
        "Pipeline: 01_fetch_data.py -> 02_clean_data.py -> 04_compute_stats.py",
        "Monthly history kept through July 2026. Later months dropped, not filled.",
        "Quarterly history kept through 2026 Q2 (FRED date 2026-04-01).",
        "August PCE and the Q2 third estimate are status strings only.",
        "Locked July PCE prints and the Q2 second estimate matched rounded FRED rates.",
        f"July core y/y {stats['pce_core_yoy']}, headline y/y {stats['pce_headline_yoy']}.",
        f"July real PCE m/m {stats['real_pce_mom']}, saving rate {stats['saving_rate']}.",
        f"Q2 GDP {stats['gdp_q2']}, PDFP {stats['pdfp_q2']} (advance PDFP {stats['pdfp_q2_advance']}).",
        "Prose-only series: personal income, disposable income, nominal PCE, August CPI, payrolls, FOMC.",
        "Figure 5 omitted: BEA published the revision window, not revision sizes.",
        (CLEAN_DIR / "history_cutoff.txt").read_text(encoding="utf-8").strip(),
    ]
    (POST_DIR / "data_pipeline_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print("summary_stats.json written. Locked prints matched.")


if __name__ == "__main__":
    main()
