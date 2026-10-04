"""
04_compute_stats.py
===================
STEP 3 of the data pipeline (there is no 03).

What this script does
---------------------
Writes stats/summary_stats.json, the only number source the QMD prose and
metric cards are allowed to use. Keys must match index.qmd.

Latest versus previous month: after sorting by date, the last non-null
September 2026 row is the print this post is about. August is the prior month.
Rounding: headline CES totals are whole thousands. Percents keep one decimal.
Dollar earnings keep two decimals. Claims are stored in thousands.

Numbers come from the committed October 2, 2026 snapshot in data/raw, not from
a fresh FRED download. Previously published estimates, ADP, the payroll
confidence interval, the September JOLTS date, and a few household rounded
levels are pinned from the official releases and marked MANUAL.
"""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"

SEPTEMBER = pd.Timestamp("2026-09-01")
AUGUST = pd.Timestamp("2026-08-01")
JULY = pd.Timestamp("2026-07-01")
MAY_2025 = pd.Timestamp("2025-05-01")
DECEMBER_2025 = pd.Timestamp("2025-12-01")

# MANUAL: BLS Employment Situation, September 2026, released 10/2/2026.
# https://www.bls.gov/news.release/archives/empsit_10022026.htm
# The committed FRED snapshot already includes these revisions.
# The previously published July and August changes are only in the release text.
JULY_PREVIOUS_K = 21.0
AUGUST_PREVIOUS_K = 162.0
LOCKED_SEP_PAYROLL_K = 29.0
LOCKED_JULY_CURRENT_K = -10.0
LOCKED_AUGUST_CURRENT_K = 133.0
LOCKED_COMBINED_REVISION_K = -60.0
LOCKED_PRIOR_12M_AVG_K = 45.0
LOCKED_3M_AVG_K = 51.0
LOCKED_UNRATE = 4.2
LOCKED_UNEMPLOYED_M = 7.1
LOCKED_PARTICIPATION = 61.8
LOCKED_EMP_POP = 59.2
LOCKED_LONG_TERM_M = 1.9
LOCKED_LONG_TERM_SHARE = 27.1
LOCKED_PTE_M = 4.5
LOCKED_AHE = 37.81
LOCKED_AHE_MOM = 0.1
LOCKED_AHE_YOY = 3.0
LOCKED_AHE_PROD = 32.60
LOCKED_AHE_PROD_MOM = 0.2
LOCKED_HOURS = 34.4
LOCKED_HEALTHCARE_K = 17.0
LOCKED_HEALTHCARE_12M_K = 33.0
LOCKED_CONSTRUCTION_K = 11.0
LOCKED_MANUFACTURING_K = 9.0
LOCKED_FINANCIAL_K = -7.0
LOCKED_MANUFACTURING_SINCE_DEC_K = 72.0
LOCKED_FINANCIAL_SINCE_PEAK_K = -129.0
LOCKED_INSURANCE_SINCE_PEAK_K = -90.0
LOCKED_CLAIMS_K = 197.0
LOCKED_JOLTS_OPENINGS_M = 7.1
LOCKED_JOLTS_HIRES_M = 5.2
LOCKED_JOLTS_QUITS_M = 3.1
LOCKED_PRIVATE_K = 46.0
LOCKED_GOVERNMENT_K = -17.0
LOCKED_JOLTS_LAYOFFS_M = 1.6

# MANUAL: August first prints from the August Employment Situation.
# https://www.bls.gov/news.release/archives/empsit_09042026.htm
# Current vintage is this month's Table B-1 / FRED CES.
# Leisure +62,000 to +37,000. Food services +59,200 to +33,800.
# Local government education first print +41,900 in Table B-1.
AUGUST_LEISURE_PREVIOUS_K = 62.0
AUGUST_FOOD_PREVIOUS_K = 59.2
AUGUST_LOCAL_EDU_PREVIOUS_K = 41.9
LOCKED_AUGUST_LEISURE_CURRENT_K = 37.0
LOCKED_AUGUST_FOOD_CURRENT_K = 33.8
LOCKED_AUGUST_LOCAL_EDU_CURRENT_K = 49.3

# MANUAL: Summary table B, September over-the-month change, thousands.
# https://www.bls.gov/news.release/archives/empsit_10022026.htm
# These three series are not in 01_fetch. Pin the BLS table, then add them
# to sector_september.csv for the industry bar chart.
WHOLESALE_SEP_K = 5.0
RETAIL_SEP_K = 5.8
TRANSPORTATION_SEP_K = 7.6

# MANUAL: BLS news release / Table A-1, Black unemployment.
# https://www.bls.gov/news.release/archives/empsit_10022026.htm
# The only major group BLS said increased. Not in 01_fetch.
LOCKED_BLACK_UNRATE = 7.0

# MANUAL: ADP National Employment Report, September 2026, released 9/30/2026.
# https://mediacenter.adp.com/2026-09-30-ADP-National-Employment-Report-Private-Sector-Employment-Increased-by-90,000-Jobs-in-September
# Private-sector payroll processor count. Not the BLS establishment survey.
ADP_PRIVATE_SEP_K = 90.0
ADP_AS_OF = "9/30/2026"

# MANUAL: BLS technical note, September 2026 Employment Situation.
# https://www.bls.gov/news.release/archives/empsit_10022026.htm
# The approximate 90 percent confidence interval for the monthly change in
# total nonfarm employment is plus or minus 122,000. It describes that
# monthly estimate. It is not a test of the August-to-September difference.
PAYROLL_CI_K = 122.0

# MANUAL: BLS release calendar and Fed calendar.
# https://www.bls.gov/schedule/news_release/empsit.htm
# https://www.bls.gov/schedule/2026/11_sched.htm
# https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
# September JOLTS is Tuesday, November 3, 2026, 10:00 a.m. ET.
BLS_RELEASE_DATE = "10/2/2026"
NEXT_MINUTES_DATE = "10/7"
NEXT_CLAIMS_DATE = "10/8"
NEXT_CPI_DATE = "10/14"
NEXT_FOMC_DATE = "10/28"
NEXT_JOLTS_DATE = "11/3"
NEXT_JOBS_DATE = "11/6"
PRIOR_JOBS_POST_DATE = "9/4"

CLAIMS_AS_OF = pd.Timestamp("2026-09-26")
JOLTS_AS_OF = pd.Timestamp("2026-08-01")


def round0(value: float) -> float:
    """Nearest thousand jobs. Matches the BLS release integers."""
    return float(round(float(value)))


def round1(value: float) -> float:
    quantized = Decimal(str(round(float(value), 6))).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )
    return float(quantized)


def round2(value: float) -> float:
    quantized = Decimal(str(round(float(value), 6))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return float(quantized)


def us_month_year(ts: pd.Timestamp) -> str:
    """Prose-facing month/year with no leading zeros, e.g. 12/2025."""
    return f"{ts.month}/{ts.year}"


def us_date(ts: pd.Timestamp) -> str:
    """Prose-facing month/day/year with no leading zeros, e.g. 9/26/2026."""
    return f"{ts.month}/{ts.day}/{ts.year}"


def require_close(name: str, got: float, expected: float, tol: float) -> None:
    if abs(float(got) - float(expected)) > tol:
        raise RuntimeError(
            f"Locked check failed for {name}: got {got}, expected {expected} "
            f"(tolerance {tol})"
        )


def millions_from_thousands(value: float, decimals: int = 1) -> float:
    scaled = float(value) / 1000.0
    return round1(scaled) if decimals == 1 else round2(scaled)


def require_value(frame: pd.DataFrame, column: str, stamp: pd.Timestamp, label: str) -> float:
    """Return one required observation. Missing data raises; it is not filled."""
    if column not in frame.columns:
        raise RuntimeError(
            f"Refusing to substitute a locked value for {label}: column {column} is missing"
        )
    stamp = pd.Timestamp(stamp)
    if stamp not in frame.index:
        raise RuntimeError(
            f"Refusing to substitute a locked value for {label}: "
            f"no observation at {stamp.strftime('%Y-%m-%d')}"
        )
    value = frame.loc[stamp, column]
    if isinstance(value, pd.Series):
        value = value.iloc[0]
    if pd.isna(value):
        raise RuntimeError(
            f"Refusing to substitute a locked value for {label}: "
            f"observation at {stamp.strftime('%Y-%m-%d')} is missing"
        )
    return float(value)


def require_level_change(
    frame: pd.DataFrame,
    column: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    label: str,
) -> float:
    end_value = require_value(frame, column, end, label)
    start_value = require_value(frame, column, start, label)
    return round0(end_value - start_value)


def check_missing_data_raises() -> None:
    """A missing peak observation must raise, not return the locked decline."""
    empty = pd.DataFrame({"financial": []})
    try:
        require_level_change(empty, "financial", MAY_2025, SEPTEMBER, "financial_since_peak_k")
    except RuntimeError as exc:
        if "Refusing to substitute" not in str(exc):
            raise
    else:
        raise RuntimeError("Missing-data check failed: empty financial series returned a value")

    no_insurance = pd.DataFrame(
        {"financial": [100.0, 90.0]},
        index=[MAY_2025, SEPTEMBER],
    )
    try:
        require_level_change(
            no_insurance,
            "insurance_carriers",
            MAY_2025,
            SEPTEMBER,
            "insurance_since_peak_k",
        )
    except RuntimeError as exc:
        if "Refusing to substitute" not in str(exc):
            raise
    else:
        raise RuntimeError("Missing-data check failed: absent insurance column returned a value")

    nulls = pd.DataFrame(
        {"insurance_carriers": [pd.NA, pd.NA]},
        index=[MAY_2025, SEPTEMBER],
    )
    try:
        require_level_change(
            nulls,
            "insurance_carriers",
            MAY_2025,
            SEPTEMBER,
            "insurance_since_peak_k",
        )
    except RuntimeError as exc:
        if "Refusing to substitute" not in str(exc):
            raise
    else:
        raise RuntimeError("Missing-data check failed: null insurance observations returned a value")

    print("Missing-data check passed: absent financial and insurance observations raise.")


def main() -> None:
    check_missing_data_raises()
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    labor = pd.read_csv(CLEAN_DIR / "labor_monthly.csv", index_col="date", parse_dates=True)
    labor = labor.sort_index()
    claims = pd.read_csv(CLEAN_DIR / "claims_weekly.csv", index_col="date", parse_dates=True)
    claims = claims.sort_index()
    sector = pd.read_csv(CLEAN_DIR / "sector_september.csv")

    if SEPTEMBER not in labor.index:
        raise RuntimeError("labor_monthly.csv has no September 2026 row")

    sep = labor.loc[SEPTEMBER]
    aug = labor.loc[AUGUST]
    jul = labor.loc[JULY]

    payroll = round0(sep["payems_chg"])
    july_current = round0(jul["payems_chg"])
    august_current = round0(aug["payems_chg"])
    july_revision = round0(july_current - JULY_PREVIOUS_K)
    august_revision = round0(august_current - AUGUST_PREVIOUS_K)
    combined_revision = round0(july_revision + august_revision)

    require_close("payroll_sep_k", payroll, LOCKED_SEP_PAYROLL_K, 0.6)
    require_close("july_current_k", july_current, LOCKED_JULY_CURRENT_K, 0.6)
    require_close("august_current_k", august_current, LOCKED_AUGUST_CURRENT_K, 0.6)
    require_close("combined_revision_k", combined_revision, LOCKED_COMBINED_REVISION_K, 0.6)

    prior_12 = labor.loc[:AUGUST, "payems_chg"].dropna().tail(12)
    payroll_3m = round0(labor.loc[SEPTEMBER, "payroll_3m_avg"])
    health_12 = labor.loc[:AUGUST, "healthcare_chg"].dropna().tail(12)

    healthcare = round0(sep["healthcare_chg"])
    construction = round0(sep["construction_chg"])
    manufacturing = round0(sep["manufacturing_chg"])
    financial = round0(sep["financial_chg"])
    require_close("healthcare_sep_k", healthcare, LOCKED_HEALTHCARE_K, 1.0)
    require_close("construction_sep_k", construction, LOCKED_CONSTRUCTION_K, 1.0)
    require_close("manufacturing_sep_k", manufacturing, LOCKED_MANUFACTURING_K, 1.0)
    require_close("financial_sep_k", financial, LOCKED_FINANCIAL_K, 1.0)

    unrate = round1(sep["unrate"])
    participation = round1(sep["civpart"])
    emp_pop = round1(sep["emratio"])
    require_close("unrate_sep", unrate, LOCKED_UNRATE, 0.06)
    require_close("participation_sep", participation, LOCKED_PARTICIPATION, 0.06)
    require_close("emp_pop_sep", emp_pop, LOCKED_EMP_POP, 0.06)

    ahe_level = round2(sep["ahe"])
    ahe_mom = round1(sep["ahe_mom"])
    ahe_yoy = round1(sep["ahe_yoy"])
    require_close("ahe_level", ahe_level, LOCKED_AHE, 0.015)
    require_close("ahe_mom_pct", ahe_mom, LOCKED_AHE_MOM, 0.06)
    require_close("ahe_yoy_pct", ahe_yoy, LOCKED_AHE_YOY, 0.06)

    ahe_prod_level = round2(sep["ahe_prod"])
    ahe_prod_mom = round1(sep["ahe_prod_mom"])
    require_close("ahe_prod_level", ahe_prod_level, LOCKED_AHE_PROD, 0.015)
    require_close("ahe_prod_mom_pct", ahe_prod_mom, LOCKED_AHE_PROD_MOM, 0.06)

    hours_level = round1(sep["hours"])
    require_close("hours_level", hours_level, LOCKED_HOURS, 0.06)

    private = round0(sep["uspriv_chg"])
    government = round0(sep["usgovt_chg"])
    require_close("private_sep_k", private, LOCKED_PRIVATE_K, 1.0)
    require_close("government_sep_k", government, LOCKED_GOVERNMENT_K, 1.0)

    unemployed_m = millions_from_thousands(sep["unemployed"])
    require_close("unemployed_level_m", unemployed_m, LOCKED_UNEMPLOYED_M, 0.06)
    pte_m = millions_from_thousands(sep["pte_economic"])
    require_close("pte_economic_m", pte_m, LOCKED_PTE_M, 0.06)
    long_term_m = millions_from_thousands(sep["long_term_unemployed"])
    require_close("long_term_unemployed_m", long_term_m, LOCKED_LONG_TERM_M, 0.06)
    long_term_share_raw = round1(
        100.0 * float(sep["long_term_unemployed"]) / float(sep["unemployed"])
    )
    require_close(
        "long_term_unemployed_share_pct",
        long_term_share_raw,
        LOCKED_LONG_TERM_SHARE,
        0.3,
    )
    long_term_share = LOCKED_LONG_TERM_SHARE

    manufacturing_since_dec = round0(
        labor.loc[SEPTEMBER, "manufacturing"] - labor.loc[DECEMBER_2025, "manufacturing"]
    )
    require_close(
        "manufacturing_since_dec_k",
        manufacturing_since_dec,
        LOCKED_MANUFACTURING_SINCE_DEC_K,
        2.0,
    )

    financial_since_peak = require_level_change(
        labor, "financial", MAY_2025, SEPTEMBER, "financial_since_peak_k"
    )
    require_close(
        "financial_since_peak_k",
        financial_since_peak,
        LOCKED_FINANCIAL_SINCE_PEAK_K,
        5.0,
    )
    insurance_since_peak = require_level_change(
        labor, "insurance_carriers", MAY_2025, SEPTEMBER, "insurance_since_peak_k"
    )
    require_close(
        "insurance_since_peak_k",
        insurance_since_peak,
        LOCKED_INSURANCE_SINCE_PEAK_K,
        8.0,
    )

    claims_level = require_value(claims, "initial_claims", CLAIMS_AS_OF, "claims_latest_k")
    claims_avg = require_value(claims, "claims_4wk_avg", CLAIMS_AS_OF, "claims_4wk_avg_k")
    claims_k = round0(claims_level / 1000.0)
    require_close("claims_latest_k", claims_k, LOCKED_CLAIMS_K, 1.5)

    jolts_openings = require_value(labor, "jolts_openings", JOLTS_AS_OF, "jolts_openings_m")
    jolts_hires = require_value(labor, "jolts_hires", JOLTS_AS_OF, "jolts_hires_m")
    jolts_quits = require_value(labor, "jolts_quits", JOLTS_AS_OF, "jolts_quits_m")
    jolts_layoffs = require_value(labor, "jolts_layoffs", JOLTS_AS_OF, "jolts_layoffs_m")
    jolts_openings_m = round1(jolts_openings / 1000.0)
    jolts_hires_m = round1(jolts_hires / 1000.0)
    jolts_quits_m = round1(jolts_quits / 1000.0)
    jolts_layoffs_m = round1(jolts_layoffs / 1000.0)
    require_close("jolts_openings_m", jolts_openings_m, LOCKED_JOLTS_OPENINGS_M, 0.15)
    require_close("jolts_hires_m", jolts_hires_m, LOCKED_JOLTS_HIRES_M, 0.15)
    require_close("jolts_quits_m", jolts_quits_m, LOCKED_JOLTS_QUITS_M, 0.15)
    require_close("jolts_layoffs_m", jolts_layoffs_m, LOCKED_JOLTS_LAYOFFS_M, 0.06)

    ahe_yoy_aug = round1(aug["ahe_yoy"])
    healthcare_12m = round0(health_12.mean())
    require_close("healthcare_12m_avg_k", healthcare_12m, LOCKED_HEALTHCARE_12M_K, 2.0)

    # Prefer the BLS stated 12-month and 3-month averages when FRED is close.
    prior_12_mean = round0(prior_12.mean())
    if abs(prior_12_mean - LOCKED_PRIOR_12M_AVG_K) <= 2:
        prior_12_used = LOCKED_PRIOR_12M_AVG_K
    else:
        prior_12_used = prior_12_mean
    if abs(payroll_3m - LOCKED_3M_AVG_K) <= 1:
        payroll_3m_used = LOCKED_3M_AVG_K
    else:
        payroll_3m_used = payroll_3m

    revisions = pd.DataFrame(
        {
            "month": ["July", "August", "September"],
            "month_date": ["2026-07-01", "2026-08-01", "2026-09-01"],
            "first_print_k": [JULY_PREVIOUS_K, AUGUST_PREVIOUS_K, payroll],
            "current_k": [july_current, august_current, payroll],
        }
    )
    revisions.to_csv(CLEAN_DIR / "revisions.csv", index=False)

    august_leisure_current = round0(aug["leisure_chg"])
    august_food_current = round1(aug["food_services_chg"])
    august_local_edu_current = round1(aug["local_education_chg"])
    require_close(
        "august_leisure_current_k",
        august_leisure_current,
        LOCKED_AUGUST_LEISURE_CURRENT_K,
        0.6,
    )
    require_close(
        "august_food_current_k",
        august_food_current,
        LOCKED_AUGUST_FOOD_CURRENT_K,
        0.06,
    )
    require_close(
        "august_local_edu_current_k",
        august_local_edu_current,
        LOCKED_AUGUST_LOCAL_EDU_CURRENT_K,
        0.06,
    )
    august_two_sector_current = round1(
        august_food_current + august_local_edu_current
    )
    august_two_sector_share = round1(
        100.0 * august_two_sector_current / august_current
    )
    august_two_sector_previous = round1(
        AUGUST_FOOD_PREVIOUS_K + AUGUST_LOCAL_EDU_PREVIOUS_K
    )
    august_two_sector_previous_share = round1(
        100.0 * august_two_sector_previous / AUGUST_PREVIOUS_K
    )

    drop_industries = {
        "All other",
        "Wholesale trade",
        "Retail trade",
        "Transportation and warehousing",
    }
    sector = sector[~sector["industry"].isin(drop_industries)].copy()
    extra_sector = pd.DataFrame(
        [
            ("Wholesale trade", WHOLESALE_SEP_K),
            ("Retail trade", RETAIL_SEP_K),
            ("Transportation and warehousing", TRANSPORTATION_SEP_K),
        ],
        columns=["industry", "change_k"],
    )
    sector = pd.concat([sector, extra_sector], ignore_index=True)
    sector.to_csv(CLEAN_DIR / "sector_september.csv", index=False)

    stats = {
        "latest_month": "September 2026",
        "latest_month_short": "Sep 2026",
        "data_current_as_of": BLS_RELEASE_DATE,
        "release_note": (
            "The September Employment Situation is preliminary and will be revised."
        ),
        "bls_release_date": BLS_RELEASE_DATE,
        "payroll_sep_k": payroll,
        "private_sep_k": private,
        "government_sep_k": government,
        "july_previous_k": JULY_PREVIOUS_K,
        "july_current_k": july_current,
        "july_revision_k": july_revision,
        "august_previous_k": AUGUST_PREVIOUS_K,
        "august_current_k": august_current,
        "august_revision_k": august_revision,
        "combined_revision_k": combined_revision,
        "prior_12m_avg_k": prior_12_used,
        "payroll_3m_avg_k": payroll_3m_used,
        "healthcare_sep_k": healthcare,
        "healthcare_12m_avg_k": healthcare_12m,
        "construction_sep_k": construction,
        "manufacturing_sep_k": manufacturing,
        "manufacturing_since_dec_k": manufacturing_since_dec,
        "manufacturing_low_month": us_month_year(DECEMBER_2025),
        "financial_sep_k": financial,
        "information_sep_k": round0(sep["information_chg"]),
        "professional_sep_k": round0(sep["professional_chg"]),
        "leisure_sep_k": round0(sep["leisure_chg"]),
        "food_services_sep_k": round1(sep["food_services_chg"]),
        "local_education_sep_k": round1(sep["local_education_chg"]),
        "temp_help_sep_k": round1(sep["temp_help_chg"]),
        "wholesale_sep_k": WHOLESALE_SEP_K,
        "retail_sep_k": RETAIL_SEP_K,
        "transportation_sep_k": TRANSPORTATION_SEP_K,
        "august_leisure_previous_k": AUGUST_LEISURE_PREVIOUS_K,
        "august_leisure_current_k": august_leisure_current,
        "august_food_previous_k": AUGUST_FOOD_PREVIOUS_K,
        "august_food_current_k": august_food_current,
        "august_local_edu_previous_k": AUGUST_LOCAL_EDU_PREVIOUS_K,
        "august_local_edu_current_k": august_local_edu_current,
        "august_two_sector_current_k": august_two_sector_current,
        "august_two_sector_share_pct": august_two_sector_share,
        "august_two_sector_previous_share_pct": august_two_sector_previous_share,
        "unrate_sep": unrate,
        "unrate_aug": round1(aug["unrate"]),
        "unrate_band_low": 4.1,
        "unrate_band_high": 4.3,
        "unemployed_level_m": unemployed_m,
        "participation_sep": participation,
        "participation_aug": round1(aug["civpart"]),
        "emp_pop_sep": emp_pop,
        "emp_pop_aug": round1(aug["emratio"]),
        "long_term_unemployed_m": long_term_m,
        "long_term_unemployed_share_pct": long_term_share,
        "pte_economic_m": pte_m,
        "labor_force_chg_k": round0(sep["labor_force_chg"]),
        "employed_chg_k": round0(sep["employed_chg"]),
        "ahe_level": ahe_level,
        "ahe_mom_pct": ahe_mom,
        "ahe_yoy_pct": ahe_yoy,
        "ahe_mom_cents": round0((float(sep["ahe"]) - float(aug["ahe"])) * 100.0),
        "ahe_yoy_aug_pct": ahe_yoy_aug,
        "ahe_prod_level": ahe_prod_level,
        "ahe_prod_mom_pct": ahe_prod_mom,
        "ahe_prod_mom_cents": round0(
            (float(sep["ahe_prod"]) - float(aug["ahe_prod"])) * 100.0
        ),
        "hours_level": hours_level,
        "hours_prev": round1(aug["hours"]),
        "claims_latest_k": claims_k,
        "claims_4wk_avg_k": round0(claims_avg / 1000.0),
        "claims_as_of": us_date(CLAIMS_AS_OF),
        "jolts_openings_m": jolts_openings_m,
        "jolts_hires_m": jolts_hires_m,
        "jolts_quits_m": jolts_quits_m,
        "jolts_layoffs_k": round0(jolts_layoffs),
        "jolts_layoffs_m": jolts_layoffs_m,
        "jolts_month": us_month_year(JOLTS_AS_OF),
        "payroll_ci_k": PAYROLL_CI_K,
        "next_jolts_date": NEXT_JOLTS_DATE,
        "black_unrate_sep": LOCKED_BLACK_UNRATE,
        "adp_private_sep_k": ADP_PRIVATE_SEP_K,
        "adp_as_of": ADP_AS_OF,
        "financial_since_peak_k": financial_since_peak,
        "insurance_since_peak_k": insurance_since_peak,
        "financial_peak_month": us_month_year(MAY_2025),
        "next_minutes_date": NEXT_MINUTES_DATE,
        "next_claims_date": NEXT_CLAIMS_DATE,
        "next_cpi_date": NEXT_CPI_DATE,
        "next_fomc_date": NEXT_FOMC_DATE,
        "next_jobs_date": NEXT_JOBS_DATE,
        "prior_jobs_post_date": PRIOR_JOBS_POST_DATE,
        "sector_industries": sector["industry"].tolist(),
    }

    (STATS_DIR / "summary_stats.json").write_text(
        json.dumps(stats, indent=2) + "\n", encoding="utf-8"
    )
    print("Wrote", STATS_DIR / "summary_stats.json")
    print("Wrote", CLEAN_DIR / "revisions.csv")
    print("September payrolls (thousands):", payroll)
    print("Combined revision (thousands):", combined_revision)
    print("AHE y/y:", ahe_yoy)


if __name__ == "__main__":
    main()
