"""
04_compute_stats.py
===================
STEP 3 of the data pipeline.

Writes stats/summary_stats.json. The post reads every prose number from that
file. Rounding uses half-up. The latest claims week is the last non-missing
ICSA row. The latest payroll month is the last non-missing PAYEMS row.
Continued claims end one week earlier than initial claims. Keys match index.qmd.

Locks are the October 22, 2026 claims release and the October 2, 2026
Employment Situation. A mismatch stops the script. It does not overwrite a
lock with a different print.
"""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"

# MANUAL: October 22, 2026 Unemployment Insurance Weekly Claims Report.
# The previous week's advance was revised up by 1,000, from 199,000 to 200,000.
# https://www.dol.gov/ui/data.pdf
CLAIMS_PRIOR_WEEK_ADVANCE = 199000
CLAIMS_PRIOR_WEEK_REVISION = 1000

# MANUAL: approximate 90 percent confidence interval on the monthly payroll
# change, and the combined July and August revision, in thousands of jobs.
# https://www.bls.gov/news.release/archives/empsit_10022026.htm
PAYROLL_CI_K = 122
PAYROLL_REVISION_JUL_AUG_K = -60

# MANUAL: target range after the September 16, 2026 decision. Not the October meeting.
# https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm
FUNDS_RATE_LOW = 3.75
FUNDS_RATE_HIGH = 4.00


def round_half_up(value: float, digits: int = 0) -> float:
    quant = Decimal("1") if digits == 0 else Decimal("0." + "0" * (digits - 1) + "1")
    rounded = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    return float(rounded)


def us_date(stamp) -> str:
    stamp = pd.Timestamp(stamp)
    return f"{stamp.month}/{stamp.day}/{stamp.year}"


def require_equal(label: str, found, expected) -> None:
    if found != expected:
        raise RuntimeError(f"{label} is {found}, expected {expected}. Stop. Do not replace the lock.")


def value_on(frame: pd.DataFrame, column: str, stamp: str) -> float:
    key = pd.Timestamp(stamp)
    if key not in frame.index or pd.isna(frame.at[key, column]):
        raise RuntimeError(f"Missing {column} on {stamp}.")
    return float(frame.at[key, column])


def main() -> None:
    claims = pd.read_csv(CLEAN_DIR / "claims_weekly.csv", index_col="date", parse_dates=True).sort_index()
    payrolls = pd.read_csv(CLEAN_DIR / "payrolls_monthly.csv", index_col="date", parse_dates=True).sort_index()
    household = pd.read_csv(CLEAN_DIR / "household_monthly.csv", index_col="date", parse_dates=True).sort_index()
    earnings = pd.read_csv(CLEAN_DIR / "earnings_monthly.csv", index_col="date", parse_dates=True).sort_index()

    icsa = claims["initial_claims"].dropna()
    claims_latest = int(round_half_up(value_on(claims, "initial_claims", "2026-10-17")))
    claims_prior = int(round_half_up(value_on(claims, "initial_claims", "2026-10-10")))
    claims_4wk = int(round_half_up(value_on(claims, "claims_4wk_avg", "2026-10-17")))
    claims_4wk_prior = int(round_half_up(value_on(claims, "claims_4wk_avg", "2026-10-10")))
    require_equal("claims_latest", claims_latest, 194000)
    require_equal("claims_prior_week", claims_prior, 200000)
    require_equal("claims_wow_change", claims_latest - claims_prior, -6000)
    require_equal("claims_4wk_avg", claims_4wk, 197750)
    require_equal("claims_4wk_wow_change", claims_4wk - claims_4wk_prior, -1000)

    continuing_latest = int(round_half_up(value_on(claims, "continuing_claims", "2026-10-10")))
    continuing_prior = int(round_half_up(value_on(claims, "continuing_claims", "2026-10-03")))
    continuing_4wk = int(round_half_up(value_on(claims, "continuing_4wk_avg", "2026-10-10")))
    require_equal("continuing_claims_latest", continuing_latest, 1728000)
    require_equal("continuing_claims_prior", continuing_prior, 1703000)
    require_equal("continuing_claims_wow_change", continuing_latest - continuing_prior, 25000)
    require_equal("continuing_claims_4wk_avg", continuing_4wk, 1711000)

    continuing_2026 = claims.loc["2026", "continuing_claims"].dropna()
    max_stamp = continuing_2026.idxmax()
    min_stamp = continuing_2026.idxmin()
    continuing_max = int(round_half_up(continuing_2026.max()))
    continuing_min = int(round_half_up(continuing_2026.min()))
    continuing_aug29 = int(round_half_up(value_on(claims, "continuing_claims", "2026-08-29")))
    require_equal("continuing_claims_2026_max", continuing_max, 1875000)
    require_equal("continuing_2026_max_week", us_date(max_stamp), "1/3/2026")
    require_equal("continuing_claims_2026_min", continuing_min, 1699000)
    require_equal("continuing_2026_min_week", us_date(min_stamp), "9/19/2026")
    require_equal("continuing_claims_aug29", continuing_aug29, 1765000)

    insured_latest = round_half_up(value_on(claims, "insured_rate", "2026-10-10"), 1)
    insured_prior = round_half_up(value_on(claims, "insured_rate", "2026-10-03"), 1)
    require_equal("insured_rate_latest", insured_latest, 1.1)
    require_equal("insured_rate_prior", insured_prior, 1.1)

    record_stamp = icsa.idxmin()
    record_low = int(round_half_up(icsa.min()))
    low_1969_series = icsa.loc["1969"]
    low_1969_stamp = low_1969_series.idxmin()
    low_1969 = int(round_half_up(low_1969_series.min()))
    since_1970 = icsa.loc["1970-01-01":]
    trough_stamp = since_1970.idxmin()
    trough = int(round_half_up(since_1970.min()))
    require_equal("record_low_claims", record_low, 162000)
    require_equal("record_low_week_end", us_date(record_stamp), "11/30/1968")
    require_equal("low_1969_claims", low_1969, 177000)
    require_equal("low_1969_week_end", us_date(low_1969_stamp), "4/26/1969")
    require_equal("trough_since_1970_claims", trough, 189000)
    require_equal("trough_since_1970_week_end", us_date(trough_stamp), "7/18/2026")
    week_2022_claims = int(round_half_up(value_on(claims, "initial_claims", "2022-09-24")))
    week_2026_04_claims = int(round_half_up(value_on(claims, "initial_claims", "2026-04-25")))
    require_equal("week_2022_claims", week_2022_claims, 190000)
    require_equal("week_2026_04_claims", week_2026_04_claims, 190000)

    at_or_below_full = int((icsa <= claims_latest).sum())
    at_or_below_1970 = int((since_1970 <= claims_latest).sum())
    under_200 = int((since_1970 < 200000).sum())
    require_equal("weeks_at_or_below_latest_full_sample", at_or_below_full, 62)
    require_equal("weeks_at_or_below_latest_since_1970", at_or_below_1970, 4)
    require_equal("weeks_under_200k_since_1970", under_200, 16)
    require_equal("sample_weeks", int(icsa.shape[0]), 3120)
    require_equal("series_start", us_date(icsa.index[0]), "1/7/1967")

    pay_change = value_on(payrolls, "payems_change", "2026-09-01")
    pay_3m = round_half_up(value_on(payrolls, "payems_change_3m", "2026-09-01"), 0)
    require_equal("payroll_change_k", int(pay_change), 29)
    require_equal("payroll_3m_avg_k", int(pay_3m), 51)

    unrate_latest = round_half_up(value_on(household, "unrate", "2026-09-01"), 1)
    unrate_prior = round_half_up(value_on(household, "unrate", "2026-08-01"), 1)
    civpart_latest = round_half_up(value_on(household, "civpart", "2026-09-01"), 1)
    civpart_prior = round_half_up(value_on(household, "civpart", "2026-08-01"), 1)
    require_equal("unrate_latest", unrate_latest, 4.2)
    require_equal("unrate_prior", unrate_prior, 4.1)
    require_equal("civpart_latest", civpart_latest, 61.8)
    require_equal("civpart_prior", civpart_prior, 61.6)

    ahe_yoy = round_half_up(value_on(earnings, "ahe_yoy", "2026-09-01"), 1)
    require_equal("ahe_yoy_pct", ahe_yoy, 3.0)

    # Expansion comparison. A month counts as recession when USREC is 1.
    # The next 12 months after a recession ends are set aside too. September
    # itself is excluded from the "earlier months" counts. This is not a
    # recession classification of September.
    recessions = pd.read_csv(CLEAN_DIR / "recessions.csv", index_col="date", parse_dates=True).sort_index()
    history = payrolls.join(recessions, how="left").dropna(subset=["payems_change"])
    post_recession_months = 12
    recession_flag = history["usrec"].fillna(0).eq(1)
    after_recession: list[bool] = []
    months_left = 0
    for is_recession in recession_flag:
        if bool(is_recession):
            months_left = post_recession_months
            after_recession.append(False)
        elif months_left > 0:
            after_recession.append(True)
            months_left -= 1
        else:
            after_recession.append(False)
    expansion = history.loc[~recession_flag.to_numpy() & ~pd.Series(after_recession, index=history.index).to_numpy()]
    earlier = expansion.loc[expansion.index < "2026-09-01"]
    september_change = float(history.loc["2026-09-01", "payems_change"])
    september_3m = float(history.loc["2026-09-01", "payems_change_3m"])
    earlier_3m = earlier.loc[earlier["payems_change_3m"].notna(), "payems_change_3m"]
    expansion_months_prior = int(earlier.shape[0])
    expansion_months_change_le_latest = int((earlier["payems_change"] <= september_change).sum())
    expansion_months_3m_prior = int(earlier_3m.shape[0])
    expansion_months_3m_le_latest = int((earlier_3m <= september_3m).sum())
    expansion_change_median_k = int(round_half_up(float(earlier["payems_change"].median()), 0))
    require_equal("expansion_months_prior", expansion_months_prior, 534)
    require_equal("expansion_months_change_le_latest", expansion_months_change_le_latest, 50)
    require_equal("expansion_months_3m_prior", expansion_months_3m_prior, 532)
    require_equal("expansion_months_3m_le_latest", expansion_months_3m_le_latest, 33)
    require_equal("expansion_change_median_k", expansion_change_median_k, 205)
    require_equal("september_not_recession", bool(recession_flag.loc["2026-09-01"]), False)

    stats = {
        "latest_month": "September 2026",
        "data_current_as_of": "10/22/2026",
        "release_note": (
            "Initial claims are the October 22, 2026 Department of Labor release. "
            "Payrolls, unemployment, participation, and earnings are the October 2, 2026 Employment Situation."
        ),
        "claims_release_date": "10/22/2026",
        "claims_week_end": "10/17/2026",
        "claims_prior_week_end": "10/10/2026",
        "continuing_week_end": "10/10/2026",
        "continuing_prior_week_end": "10/3/2026",
        "payroll_release_date": "10/2/2026",
        "payroll_month": "September 2026",
        "survey_week_end": "10/17/2026",
        "survey_week_includes_date": "10/12/2026",
        "october_jobs_date": "11/6/2026",
        "jolts_release_date": "11/3/2026",
        "fomc_meeting_start": "10/27/2026",
        "fomc_decision_date": "10/28/2026",
        "gdp_pce_date": "10/29/2026",
        "next_claims_date": "10/29/2026",
        "series_start": "1/7/1967",
        "record_low_week_end": "11/30/1968",
        "low_1969_week_end": "4/26/1969",
        "trough_since_1970_week_end": "7/18/2026",
        "week_2022_end": "9/24/2022",
        "week_2026_04_end": "4/25/2026",
        "continuing_2026_max_week_end": "1/3/2026",
        "continuing_2026_min_week_end": "9/19/2026",
        "continuing_aug29_week_end": "8/29/2026",
        "funds_rate_decision_date": "9/16/2026",
        "claims_latest": claims_latest,
        "claims_prior_week": claims_prior,
        "claims_prior_week_advance": CLAIMS_PRIOR_WEEK_ADVANCE,
        "claims_prior_week_revision": CLAIMS_PRIOR_WEEK_REVISION,
        "claims_wow_change": claims_latest - claims_prior,
        "claims_4wk_avg": claims_4wk,
        "claims_4wk_wow_change": claims_4wk - claims_4wk_prior,
        "continuing_claims_latest": continuing_latest,
        "continuing_claims_prior": continuing_prior,
        "continuing_claims_wow_change": continuing_latest - continuing_prior,
        "continuing_claims_4wk_avg": continuing_4wk,
        "continuing_claims_2026_max": continuing_max,
        "continuing_claims_2026_min": continuing_min,
        "continuing_claims_aug29": continuing_aug29,
        "insured_rate_latest": insured_latest,
        "insured_rate_prior": insured_prior,
        "record_low_claims": record_low,
        "low_1969_claims": low_1969,
        "trough_since_1970_claims": trough,
        "week_2022_claims": week_2022_claims,
        "week_2026_04_claims": week_2026_04_claims,
        "weeks_at_or_below_latest_since_1970": at_or_below_1970,
        "weeks_at_or_below_latest_full_sample": at_or_below_full,
        "weeks_under_200k_since_1970": under_200,
        "sample_weeks": int(icsa.shape[0]),
        "payroll_change_k": int(pay_change),
        "payroll_3m_avg_k": int(pay_3m),
        "payroll_ci_k": PAYROLL_CI_K,
        "payroll_revision_jul_aug_k": PAYROLL_REVISION_JUL_AUG_K,
        "unrate_latest": unrate_latest,
        "unrate_prior": unrate_prior,
        "civpart_latest": civpart_latest,
        "civpart_prior": civpart_prior,
        "ahe_yoy_pct": ahe_yoy,
        "funds_rate_low": FUNDS_RATE_LOW,
        "funds_rate_high": FUNDS_RATE_HIGH,
        "post_recession_months": post_recession_months,
        "expansion_sample_month": "February 1967",
        "expansion_months_prior": expansion_months_prior,
        "expansion_months_change_le_latest": expansion_months_change_le_latest,
        "expansion_months_3m_prior": expansion_months_3m_prior,
        "expansion_months_3m_le_latest": expansion_months_3m_le_latest,
        "expansion_change_median_k": expansion_change_median_k,
    }

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    out = STATS_DIR / "summary_stats.json"
    out.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print("Wrote", out)
    print(f"claims_latest={claims_latest} payroll_change_k={int(pay_change)} continuing={continuing_latest}")


if __name__ == "__main__":
    main()
