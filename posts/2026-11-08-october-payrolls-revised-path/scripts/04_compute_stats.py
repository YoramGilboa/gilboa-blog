"""
04_compute_stats.py
===================
STEP 3 of the data pipeline (there is no 03).

What this script does
---------------------
Writes stats/summary_stats.json, the only number source the QMD prose and
metric cards are allowed to use. It also writes the two small chart files
that mix FRED changes with figures transcribed from the news release.

Latest versus previous month: after sorting by date, October 2026 is the
month this post is about. September is the prior month on this same vintage.

Rounding: payroll totals that BLS states as whole thousands stay whole
thousands. One-decimal table cells stay one decimal. Dollar earnings keep
two decimals. A percent the news release states at one decimal is stored
at one decimal after round-half-up.

The committed November vintages in data/raw are the FRED check. Previously
published August and September payroll changes, sector cells that are not
a clean FRED difference, diffusion indexes, and the funds-rate range are
pinned from the official releases and marked MANUAL.
"""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"

OCTOBER = pd.Timestamp("2026-10-01")
SEPTEMBER = pd.Timestamp("2026-09-01")
AUGUST = pd.Timestamp("2026-08-01")
JULY = pd.Timestamp("2026-07-01")
OCTOBER_2025 = pd.Timestamp("2025-10-01")

BLS_URL = "https://www.bls.gov/news.release/archives/empsit_11062026.htm"
JOLTS_URL = "https://www.bls.gov/news.release/archives/jolts_11032026.htm"
CLAIMS_URL = "https://www.dol.gov/ui/data.pdf"
FOMC_URL = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm"

# MANUAL: BLS Employment Situation, October 2026, released 11/6/2026.
# https://www.bls.gov/news.release/archives/empsit_11062026.htm
# The previously published August and September changes are the earlier vintage
# quoted in that release. They are not a FRED level difference on this file.
AUGUST_PREVIOUS_K = 133.0
SEPTEMBER_PREVIOUS_K = 29.0
LOCKED_OCT_PAYROLL_K = 165.0
LOCKED_AUGUST_CURRENT_K = 186.0
LOCKED_SEPTEMBER_CURRENT_K = 60.0
LOCKED_COMBINED_REVISION_K = 84.0
LOCKED_PRIVATE_K = 159.0
LOCKED_GOVERNMENT_K = 6.0
LOCKED_PRIOR_12M_AVG_K = 48.0
LOCKED_3M_AVG_K = 137.0
LOCKED_PRIOR_3M_AVG_K = 51.0
LOCKED_UNRATE = 4.1
LOCKED_UNRATE_SEP = 4.2
LOCKED_U6 = 7.9
LOCKED_U6_SEP = 7.6
LOCKED_PARTICIPATION = 61.9
LOCKED_PARTICIPATION_SEP = 61.8
LOCKED_EMRATIO = 59.3
LOCKED_EMRATIO_SEP = 59.2
LOCKED_LABOR_FORCE_CHG_K = 421.0
LOCKED_HOUSEHOLD_EMP_CHG_K = 463.0
LOCKED_UNEMPLOYED_NEWS_M = 7.1
LOCKED_PTE_CHG_K = 339.0
LOCKED_LONG_TERM_NEWS_M = 2.0
LOCKED_LONG_TERM_SHARE = 27.6
LOCKED_AHE = 38.00
LOCKED_AHE_SEP = 37.86
LOCKED_AHE_MOM_CENTS = 14.0
LOCKED_AHE_MOM = 0.4
LOCKED_AHE_YOY = 3.1
LOCKED_AHE_PROD = 32.75
LOCKED_AHE_PROD_CENTS = 12.0
LOCKED_AHE_PROD_MOM = 0.4
LOCKED_HOURS = 34.4
LOCKED_HOURS_PROD = 33.8
LOCKED_HOURS_PROD_CHANGE = -0.1
LOCKED_WEEKLY_EARNINGS = 1307.20
LOCKED_PROFESSIONAL_K = 70.0
LOCKED_PROFESSIONAL_12M_K = 15.0
LOCKED_PROFESSIONAL_PST_K = 33.0
LOCKED_PROFESSIONAL_ADMIN_K = 28.0
LOCKED_PROFESSIONAL_MGMT_K = 9.0
LOCKED_PROFESSIONAL_SINCE_K = 269.0
LOCKED_HEALTHCARE_NEWS_K = 42.0
LOCKED_HEALTHCARE_12M_K = 31.0
LOCKED_HOSPITALS_K = 16.0
LOCKED_HOME_HEALTH_K = 11.0
LOCKED_OUTPATIENT_K = 5.0
LOCKED_MANUFACTURING_K = 19.0
LOCKED_MANUFACTURING_SINCE_K = 101.0
LOCKED_CONSTRUCTION_K = -3.0
LOCKED_INFORMATION_K = -1.0
LOCKED_FINANCIAL_K = 7.0

# MANUAL: Summary table B, October over-the-month change.
# https://www.bls.gov/news.release/archives/empsit_11062026.htm
# Transportation, wholesale, retail, utilities, and mining are pinned from
# that table. Health care in the news release is 42,000. The FRED health-care
# series differs by a few tenths and is checked, not substituted.
TRANSPORT_TABLE_K = 24.8
TRANSPORT_NEWS_K = 25.0
COURIERS_K = 17.0
AIR_TRANSPORT_K = 4.0
WHOLESALE_K = -9.1
RETAIL_K = 6.0
UTILITIES_K = 0.1
MINING_K = -1.0
TEMP_HELP_K = 18.6
DIFFUSION_PRIVATE_OCT = 57.6
DIFFUSION_PRIVATE_SEP = 54.2
DIFFUSION_MFG_OCT = 62.5
DIFFUSION_MFG_SEP = 51.4

# MANUAL: JOLTS, September 2026, released 11/3/2026.
# https://www.bls.gov/news.release/archives/jolts_11032026.htm
LOCKED_OPENINGS_K = 7523.0
LOCKED_OPENINGS_PRIOR_K = 7190.0
LOCKED_OPENINGS_RATE = 4.5
LOCKED_OPENINGS_RATE_PREV = 4.3
LOCKED_HIRES_K = 5402.0
LOCKED_QUITS_K = 3365.0
LOCKED_QUITS_RATE = 2.1
LOCKED_QUITS_RATE_PREV = 1.9
LOCKED_LAYOFFS_K = 1641.0
LOCKED_LAYOFFS_RATE = 1.0

# MANUAL: DOL Unemployment Insurance Weekly Claims, released 11/5/2026.
# https://www.dol.gov/ui/data.pdf
LOCKED_CLAIMS_K = 189000.0
LOCKED_CLAIMS_PRIOR_K = 195000.0
LOCKED_CLAIMS_4WK = 194750.0
LOCKED_CLAIMS_SURVEY_WEEK_K = 195000.0
LOCKED_CONTINUED_K = 1718000.0
LOCKED_CONTINUED_CHG_K = 23000.0
LOCKED_IURSA = 1.1

# MANUAL: FOMC statement, October 28, 2026.
# https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm
# The Committee maintained the target range. This post does not predict December.
FUNDS_TARGET_RANGE = "3.75 to 4.00 percent"

# MANUAL: Summary table B, October 2026 column. Sibling sectors only.
# https://www.bls.gov/news.release/empsit.b.htm
# Private education and health is the parent. Health care (42) is inside it
# and is not also a bar. Other services is its own row.
EDUC_HEALTH_K = 53.0
OTHER_SERVICES_K = 6.0

# MANUAL: October 2, 2026 Employment Situation. July's published change.
# The November 6 snapshot's July change is checked against this and must match.
# https://www.bls.gov/news.release/archives/empsit_10022026.htm
JULY_OCT2_K = -10.0

# MANUAL: Employment Situation technical note, October 2026.
# https://www.bls.gov/news.release/empsit.tn.htm
# "on the order of plus or minus 122,000" for the monthly payroll change.
# The household intervals below are BLS's example at an unemployment rate
# around 6 percent, not a custom interval for the 4.1 percent rate.
PAYROLL_CI_K = 122.0
HOUSEHOLD_RATE_CI_PP = 0.3
HOUSEHOLD_LEVEL_CI_K = 425.0

# MANUAL: BLS JOLTS latest numbers, September 2026.
# https://www.bls.gov/jlt/
# "Latest Hires Rate: 3.4%(p) in Sep 2026"
HIRES_RATE = 3.4

# MANUAL: news release, production and nonsupervisory workweek.
# Down 0.1 hour to 33.8, so the prior week is 33.9 hours.
PROD_HOURS_PRIOR = 33.9


def half_up(value: float, places: int) -> float:
    quant = Decimal("1") if places == 0 else Decimal("0." + ("0" * (places - 1)) + "1")
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def require_close(name: str, found: float, expected: float, tolerance: float = 0.05) -> None:
    if abs(found - expected) > tolerance:
        raise RuntimeError(
            f"{name} is {found} on the committed snapshot, expected {expected}. "
            "The news release wins. Stop and reconcile before writing stats."
        )


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, lineterminator="\n")


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    labor = pd.read_csv(CLEAN_DIR / "labor_monthly.csv", index_col="date", parse_dates=True)
    claims = pd.read_csv(CLEAN_DIR / "claims_weekly.csv", index_col="date", parse_dates=True)

    oct = labor.loc[OCTOBER]
    sep = labor.loc[SEPTEMBER]
    aug = labor.loc[AUGUST]
    require_close("October payrolls", float(oct["payems_chg"]), LOCKED_OCT_PAYROLL_K)
    require_close("August payrolls", float(aug["payems_chg"]), LOCKED_AUGUST_CURRENT_K)
    require_close("September payrolls", float(sep["payems_chg"]), LOCKED_SEPTEMBER_CURRENT_K)
    require_close("October private", float(oct["uspriv_chg"]), LOCKED_PRIVATE_K)
    require_close("October government", float(oct["usgovt_chg"]), LOCKED_GOVERNMENT_K)
    require_close("unemployment", float(oct["unrate"]), LOCKED_UNRATE)
    require_close("September unemployment", float(sep["unrate"]), LOCKED_UNRATE_SEP)
    require_close("U-6", float(oct["u6rate"]), LOCKED_U6)
    require_close("September U-6", float(sep["u6rate"]), LOCKED_U6_SEP)
    require_close("participation", float(oct["civpart"]), LOCKED_PARTICIPATION)
    require_close("employment-population", float(oct["emratio"]), LOCKED_EMRATIO)
    require_close("AHE level", float(oct["ahe"]), LOCKED_AHE)
    require_close("September AHE", float(sep["ahe"]), LOCKED_AHE_SEP)
    require_close("professional", float(oct["professional_chg"]), LOCKED_PROFESSIONAL_K)
    require_close("manufacturing", float(oct["manufacturing_chg"]), LOCKED_MANUFACTURING_K)
    require_close("construction", float(oct["construction_chg"]), LOCKED_CONSTRUCTION_K)
    require_close("information", float(oct["information_chg"]), LOCKED_INFORMATION_K)
    require_close("financial", float(oct["financial_chg"]), LOCKED_FINANCIAL_K)
    require_close("temporary help", float(oct["temp_help_chg"]), TEMP_HELP_K, tolerance=0.15)
    require_close("labor force", float(oct["labor_force_chg"]), LOCKED_LABOR_FORCE_CHG_K)
    require_close("household employment", float(oct["employed_chg"]), LOCKED_HOUSEHOLD_EMP_CHG_K)
    require_close("openings", float(sep["jolts_openings"]), LOCKED_OPENINGS_K)
    require_close("August openings", float(aug["jolts_openings"]), LOCKED_OPENINGS_PRIOR_K)
    require_close("openings rate", float(sep["jolts_openings_rate"]), LOCKED_OPENINGS_RATE)
    require_close("quits rate", float(sep["jolts_quits_rate"]), LOCKED_QUITS_RATE)
    require_close("hires", float(sep["jolts_hires"]), LOCKED_HIRES_K)
    require_close("quits", float(sep["jolts_quits"]), LOCKED_QUITS_K)
    require_close("layoffs", float(sep["jolts_layoffs"]), LOCKED_LAYOFFS_K, tolerance=0.5)

    ahe_mom = half_up(float(oct["ahe_mom"]), 1)
    ahe_yoy = half_up(float(oct["ahe_yoy"]), 1)
    require_close("AHE month percent", ahe_mom, LOCKED_AHE_MOM)
    require_close("AHE year percent", ahe_yoy, LOCKED_AHE_YOY)
    healthcare_fred = float(oct["healthcare_chg"])
    if not 41.4 <= healthcare_fred <= 41.8:
        raise RuntimeError(
            f"Health-care FRED change is {healthcare_fred}, expected about 41.6. "
            "The news release says 42,000. Reconcile before substituting."
        )

    week_oct_31 = pd.Timestamp("2026-10-31")
    week_oct_24 = pd.Timestamp("2026-10-24")
    week_oct_17 = pd.Timestamp("2026-10-17")
    require_close("initial claims", float(claims.loc[week_oct_31, "initial_claims"]), LOCKED_CLAIMS_K, tolerance=0.5)
    require_close("prior-week claims", float(claims.loc[week_oct_24, "initial_claims"]), LOCKED_CLAIMS_PRIOR_K, tolerance=0.5)
    require_close("survey-week claims", float(claims.loc[week_oct_17, "initial_claims"]), LOCKED_CLAIMS_SURVEY_WEEK_K, tolerance=0.5)
    require_close("four-week claims", float(claims.loc[week_oct_31, "claims_4wk"]), LOCKED_CLAIMS_4WK, tolerance=0.5)
    require_close("continued claims", float(claims.loc[week_oct_24, "continued_claims"]), LOCKED_CONTINUED_K, tolerance=0.5)
    require_close("insured rate", float(claims.loc[week_oct_24, "insured_rate"]), LOCKED_IURSA)

    payroll_changes = pd.DataFrame(
        [
            {"month": "2026-08-01", "previous_k": AUGUST_PREVIOUS_K, "current_k": LOCKED_AUGUST_CURRENT_K},
            {"month": "2026-09-01", "previous_k": SEPTEMBER_PREVIOUS_K, "current_k": LOCKED_SEPTEMBER_CURRENT_K},
            {"month": "2026-10-01", "previous_k": None, "current_k": LOCKED_OCT_PAYROLL_K},
        ]
    )
    write_csv(payroll_changes, CLEAN_DIR / "payroll_changes.csv")

    # Sibling sectors only. Health care is inside private education and health,
    # and temporary help is inside professional and business services.
    # https://www.bls.gov/news.release/empsit.b.htm
    july = labor.loc[pd.Timestamp("2026-07-01")]
    require_close("July payrolls on this snapshot", float(july["payems_chg"]), JULY_OCT2_K)
    sectors = pd.DataFrame(
        [
            ("Prof. & business", LOCKED_PROFESSIONAL_K),
            ("Education & health", EDUC_HEALTH_K),
            ("Transportation", TRANSPORT_TABLE_K),
            ("Manufacturing", LOCKED_MANUFACTURING_K),
            ("Financial", LOCKED_FINANCIAL_K),
            ("Retail", RETAIL_K),
            ("Other services", OTHER_SERVICES_K),
            ("Government", LOCKED_GOVERNMENT_K),
            ("Utilities", UTILITIES_K),
            ("Information", LOCKED_INFORMATION_K),
            ("Mining", MINING_K),
            ("Construction", LOCKED_CONSTRUCTION_K),
            ("Wholesale", WHOLESALE_K),
            ("Leisure", float(oct["leisure_chg"])),
        ],
        columns=["industry", "change_k"],
    )
    sector_sum = float(sectors["change_k"].sum())
    if abs(sector_sum - LOCKED_OCT_PAYROLL_K) > 0.3:
        raise RuntimeError(
            f"Sector bars sum to {sector_sum}, expected about {LOCKED_OCT_PAYROLL_K}. "
            "Do not ship a chart that misses the total."
        )
    write_csv(sectors, CLEAN_DIR / "sector_changes.csv")

    household = labor.loc[:, ["unrate", "u6rate", "pte_economic"]].copy()
    household.index.name = "date"
    write_csv(household, CLEAN_DIR / "household.csv")

    leisure_k = half_up(float(oct["leisure_chg"]), 1)
    two_leading_k = LOCKED_PROFESSIONAL_K + LOCKED_HEALTHCARE_NEWS_K
    two_leading_share = half_up(100.0 * two_leading_k / LOCKED_OCT_PAYROLL_K, 1)
    # October 2 window: July -10, August 133, September 29. Sum 152.
    old_sum_k = JULY_OCT2_K + AUGUST_PREVIOUS_K + SEPTEMBER_PREVIOUS_K
    old_avg_exact = old_sum_k / 3.0
    revision_avg_exact = LOCKED_COMBINED_REVISION_K / 3.0
    window_sum_k = LOCKED_OCT_PAYROLL_K - JULY_OCT2_K
    window_avg_exact = window_sum_k / 3.0
    new_sum_k = LOCKED_AUGUST_CURRENT_K + LOCKED_SEPTEMBER_CURRENT_K + LOCKED_OCT_PAYROLL_K
    new_avg_exact = new_sum_k / 3.0
    if abs((old_avg_exact + revision_avg_exact + window_avg_exact) - new_avg_exact) > 1e-9:
        raise RuntimeError("Three-month bridge does not add up before rounding.")
    # Product of published averages, not a same-worker weekly paycheck.
    prod_weekly_prior = LOCKED_AHE_PROD - (LOCKED_AHE_PROD_CENTS / 100.0)
    # 32.75 minus 0.12 dollars is 32.63, matching the September FRED level.
    require_close("production wage prior month", prod_weekly_prior, float(sep["ahe_prod"]))
    prod_weekly_sep = prod_weekly_prior * PROD_HOURS_PRIOR
    prod_weekly_oct = LOCKED_AHE_PROD * LOCKED_HOURS_PROD
    prod_weekly_pct_exact = (prod_weekly_oct / prod_weekly_sep - 1.0) * 100.0
    prod_weekly_pct = half_up(prod_weekly_pct_exact, 2)
    all_weekly_sep = LOCKED_AHE_SEP * LOCKED_HOURS
    all_weekly_oct = LOCKED_AHE * LOCKED_HOURS
    all_weekly_pct = half_up((all_weekly_oct / all_weekly_sep - 1.0) * 100.0, 1)
    jan2024 = labor.loc[pd.Timestamp("2024-01-01")]
    ahe_yoy_jan2024 = half_up(float(jan2024["ahe_yoy"]), 1)
    payroll_ci_low = LOCKED_OCT_PAYROLL_K - PAYROLL_CI_K
    payroll_ci_high = LOCKED_OCT_PAYROLL_K + PAYROLL_CI_K
    stats = {
        "latest_month": "October 2026",
        "latest_month_short": "Oct 2026",
        "data_current_as_of": "11/6/2026",
        "release_note": "The October Employment Situation is preliminary and will be revised. JOLTS figures are the September release. Claims are the November 5 release.",
        "bls_release_date": "11/6/2026",
        "jolts_release_date": "11/3/2026",
        "claims_release_date": "11/5/2026",
        "payroll_oct_k": LOCKED_OCT_PAYROLL_K,
        "private_oct_k": LOCKED_PRIVATE_K,
        "government_oct_k": LOCKED_GOVERNMENT_K,
        "august_previous_k": AUGUST_PREVIOUS_K,
        "august_current_k": LOCKED_AUGUST_CURRENT_K,
        "august_revision_k": LOCKED_AUGUST_CURRENT_K - AUGUST_PREVIOUS_K,
        "september_previous_k": SEPTEMBER_PREVIOUS_K,
        "september_current_k": LOCKED_SEPTEMBER_CURRENT_K,
        "september_revision_k": LOCKED_SEPTEMBER_CURRENT_K - SEPTEMBER_PREVIOUS_K,
        "combined_revision_k": LOCKED_COMBINED_REVISION_K,
        "payroll_3m_avg_k": LOCKED_3M_AVG_K,
        "prior_3m_avg_k": LOCKED_PRIOR_3M_AVG_K,
        "prior_12m_avg_k": LOCKED_PRIOR_12M_AVG_K,
        "july_leaving_k": JULY_OCT2_K,
        "bridge_old_sum_k": old_sum_k,
        "bridge_old_avg_exact_k": old_avg_exact,
        "bridge_old_avg_k": half_up(old_avg_exact, 0),
        "bridge_revision_avg_k": revision_avg_exact,
        "bridge_window_sum_k": window_sum_k,
        "bridge_window_avg_exact_k": window_avg_exact,
        "bridge_window_avg_k": half_up(window_avg_exact, 0),
        "bridge_new_sum_k": new_sum_k,
        "bridge_new_avg_exact_k": new_avg_exact,
        "educ_health_oct_k": EDUC_HEALTH_K,
        "other_services_oct_k": OTHER_SERVICES_K,
        "sector_sum_k": sector_sum,
        "sector_gap_k": half_up(LOCKED_OCT_PAYROLL_K - sector_sum, 1),
        "two_leading_k": two_leading_k,
        "two_leading_share_pct": two_leading_share,
        "professional_oct_k": LOCKED_PROFESSIONAL_K,
        "professional_12m_avg_k": LOCKED_PROFESSIONAL_12M_K,
        "professional_pst_k": LOCKED_PROFESSIONAL_PST_K,
        "professional_admin_k": LOCKED_PROFESSIONAL_ADMIN_K,
        "professional_mgmt_k": LOCKED_PROFESSIONAL_MGMT_K,
        "professional_since_oct2025_k": LOCKED_PROFESSIONAL_SINCE_K,
        "professional_low_month": "October 2025",
        "manufacturing_low_month": "December 2025",
        "september_professional_current_k": half_up(float(sep["professional_chg"]), 1),
        "healthcare_oct_k": LOCKED_HEALTHCARE_NEWS_K,
        "healthcare_12m_avg_k": LOCKED_HEALTHCARE_12M_K,
        "hospitals_oct_k": LOCKED_HOSPITALS_K,
        "home_health_oct_k": LOCKED_HOME_HEALTH_K,
        "outpatient_oct_k": LOCKED_OUTPATIENT_K,
        "transportation_oct_k": TRANSPORT_NEWS_K,
        "transportation_table_k": TRANSPORT_TABLE_K,
        "couriers_oct_k": COURIERS_K,
        "air_transport_oct_k": AIR_TRANSPORT_K,
        "manufacturing_oct_k": LOCKED_MANUFACTURING_K,
        "manufacturing_since_dec2025_k": LOCKED_MANUFACTURING_SINCE_K,
        "construction_oct_k": LOCKED_CONSTRUCTION_K,
        "retail_oct_k": RETAIL_K,
        "wholesale_oct_k": WHOLESALE_K,
        "information_oct_k": LOCKED_INFORMATION_K,
        "financial_oct_k": LOCKED_FINANCIAL_K,
        "leisure_oct_k": leisure_k,
        "government_bar_k": LOCKED_GOVERNMENT_K,
        "utilities_oct_k": UTILITIES_K,
        "mining_oct_k": MINING_K,
        "temp_help_oct_k": TEMP_HELP_K,
        "diffusion_private_oct": DIFFUSION_PRIVATE_OCT,
        "diffusion_private_sep": DIFFUSION_PRIVATE_SEP,
        "diffusion_manufacturing_oct": DIFFUSION_MFG_OCT,
        "diffusion_manufacturing_sep": DIFFUSION_MFG_SEP,
        "unrate_oct": LOCKED_UNRATE,
        "unrate_sep": LOCKED_UNRATE_SEP,
        "unemployed_news_m": LOCKED_UNEMPLOYED_NEWS_M,
        "labor_force_chg_k": LOCKED_LABOR_FORCE_CHG_K,
        "participation_oct": LOCKED_PARTICIPATION,
        "participation_sep": LOCKED_PARTICIPATION_SEP,
        "household_employed_chg_k": LOCKED_HOUSEHOLD_EMP_CHG_K,
        "emratio_oct": LOCKED_EMRATIO,
        "emratio_sep": LOCKED_EMRATIO_SEP,
        "pte_oct_k": float(oct["pte_economic"]),
        "pte_news_m": 4.8,
        "pte_chg_k": LOCKED_PTE_CHG_K,
        "u6_oct": LOCKED_U6,
        "u6_sep": LOCKED_U6_SEP,
        "long_term_unemployed_news_m": LOCKED_LONG_TERM_NEWS_M,
        "long_term_share_pct": LOCKED_LONG_TERM_SHARE,
        "ahe_level": LOCKED_AHE,
        "ahe_sep_level": LOCKED_AHE_SEP,
        "ahe_mom_cents": LOCKED_AHE_MOM_CENTS,
        "ahe_mom_pct": LOCKED_AHE_MOM,
        "ahe_yoy_pct": LOCKED_AHE_YOY,
        "ahe_prod_level": LOCKED_AHE_PROD,
        "ahe_prod_mom_cents": LOCKED_AHE_PROD_CENTS,
        "ahe_prod_mom_pct": LOCKED_AHE_PROD_MOM,
        "hours_level": LOCKED_HOURS,
        "hours_prod_level": LOCKED_HOURS_PROD,
        "hours_prod_change": LOCKED_HOURS_PROD_CHANGE,
        "weekly_earnings_level": LOCKED_WEEKLY_EARNINGS,
        "jolts_month": "September 2026",
        "jolts_openings_m": half_up(LOCKED_OPENINGS_K / 1000.0, 3),
        "jolts_openings_change_k": LOCKED_OPENINGS_K - LOCKED_OPENINGS_PRIOR_K,
        "jolts_openings_rate": LOCKED_OPENINGS_RATE,
        "jolts_openings_rate_prev": LOCKED_OPENINGS_RATE_PREV,
        "jolts_hires_m": half_up(LOCKED_HIRES_K / 1000.0, 3),
        "jolts_hires_rate": HIRES_RATE,
        "jolts_quits_m": half_up(LOCKED_QUITS_K / 1000.0, 3),
        "jolts_quits_rate": LOCKED_QUITS_RATE,
        "jolts_quits_rate_prev": LOCKED_QUITS_RATE_PREV,
        "jolts_layoffs_m": half_up(LOCKED_LAYOFFS_K / 1000.0, 3),
        "jolts_layoffs_rate": LOCKED_LAYOFFS_RATE,
        "claims_latest_k": LOCKED_CLAIMS_K,
        "claims_latest_week": "10/31/2026",
        "claims_prior_week_k": LOCKED_CLAIMS_PRIOR_K,
        "claims_4wk_avg_k": LOCKED_CLAIMS_4WK,
        "claims_survey_week_k": LOCKED_CLAIMS_SURVEY_WEEK_K,
        "claims_survey_week": "10/17/2026",
        "continued_claims_k": LOCKED_CONTINUED_K,
        "continued_claims_week": "10/24/2026",
        "continued_claims_chg_k": LOCKED_CONTINUED_CHG_K,
        "iursa": LOCKED_IURSA,
        "payroll_ci_k": PAYROLL_CI_K,
        "payroll_ci_low_k": payroll_ci_low,
        "payroll_ci_high_k": payroll_ci_high,
        "household_rate_ci_pp": HOUSEHOLD_RATE_CI_PP,
        "household_level_ci_k": HOUSEHOLD_LEVEL_CI_K,
        "prod_hours_prior": PROD_HOURS_PRIOR,
        "prod_weekly_sep": round(prod_weekly_sep, 2),
        "prod_weekly_oct": round(prod_weekly_oct, 2),
        "prod_weekly_pct_exact": prod_weekly_pct_exact,
        "prod_weekly_pct": prod_weekly_pct,
        "all_weekly_sep": round(all_weekly_sep, 2),
        "all_weekly_oct": round(all_weekly_oct, 2),
        "all_weekly_pct": all_weekly_pct,
        "ahe_yoy_jan2024_pct": ahe_yoy_jan2024,
        "funds_target_range": FUNDS_TARGET_RANGE,
        "fomc_statement_date": "10/28/2026",
        "next_cpi_date": "11/10/2026",
        "next_ppi_date": "11/13/2026",
        "next_claims_date": "11/12/2026",
        "next_minutes_date": "11/18/2026",
        "next_jobs_date": "12/4/2026",
        "next_fomc_date": "12/9/2026",
        "sources": {
            "bls": BLS_URL,
            "jolts": JOLTS_URL,
            "claims": CLAIMS_URL,
            "fomc": FOMC_URL,
        },
    }

    combined = stats["august_revision_k"] + stats["september_revision_k"]
    if combined != LOCKED_COMBINED_REVISION_K:
        raise RuntimeError(f"Combined revision is {combined}, expected {LOCKED_COMBINED_REVISION_K}.")
    three = (LOCKED_AUGUST_CURRENT_K + LOCKED_SEPTEMBER_CURRENT_K + LOCKED_OCT_PAYROLL_K) / 3
    if three != LOCKED_3M_AVG_K:
        raise RuntimeError(f"Three-month average is {three}, expected {LOCKED_3M_AVG_K}.")
    if pd.notna(labor.loc[OCTOBER_2025, "unrate"]):
        raise RuntimeError("October 2025 unemployment is present. The release says that month was not collected.")

    out = STATS_DIR / "summary_stats.json"
    out.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print("Wrote", CLEAN_DIR / "payroll_changes.csv")
    print("Wrote", CLEAN_DIR / "sector_changes.csv")
    print("Wrote", out)
    print("Health-care FRED change (thousands):", round(healthcare_fred, 1), "news print: 42")
    print("Leisure change (thousands):", leisure_k)


if __name__ == "__main__":
    main()
