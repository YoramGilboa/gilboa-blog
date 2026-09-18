"""
04_compute_stats.py
-------------------
Step 3 of the pipeline: write every number the post reads in prose or cards.

FRED-derived values come from the cleaned CSVs. Official SEP prints, the vote,
and the futures snapshot are marked # MANUAL: with a primary source URL.

Prose-facing dates are US month/day (for example 9/16). Do not invent dates
in index.qmd.

Run after 02_clean_data.py, from the post folder:
    python scripts/04_compute_stats.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"


def month_label(ts: pd.Timestamp) -> str:
    return ts.strftime("%B %Y")


def month_day(ts: pd.Timestamp) -> str:
    return f"{ts.month}/{ts.day}"


def latest_non_null(frame: pd.DataFrame, column: str):
    series = frame[column].dropna()
    if series.empty:
        raise RuntimeError(f"No observations for {column}")
    return series.iloc[-1], series.index[-1]


def main() -> None:
    STATS_DIR.mkdir(parents=True, exist_ok=True)

    infl = pd.read_csv(CLEAN_DIR / "inflation.csv", index_col="date", parse_dates=True)
    labor = pd.read_csv(CLEAN_DIR / "labor.csv", index_col="date", parse_dates=True)
    rates_d = pd.read_csv(CLEAN_DIR / "rates_daily.csv", index_col="date", parse_dates=True)
    market = pd.read_csv(CLEAN_DIR / "market_path.csv", parse_dates=["date"])
    dots = pd.read_csv(CLEAN_DIR / "sep_dots_2026.csv")

    cpi_yoy, cpi_date = latest_non_null(infl, "headline_cpi_yoy")
    core_cpi_yoy, _ = latest_non_null(infl, "core_cpi_yoy")
    cpi_mom, _ = latest_non_null(infl, "headline_cpi_mom")
    core_cpi_mom, _ = latest_non_null(infl, "core_cpi_mom")
    pce_yoy, pce_date = latest_non_null(infl, "headline_pce_yoy")
    core_pce_yoy, _ = latest_non_null(infl, "core_pce_yoy")
    unrate, labor_date = latest_non_null(labor, "unrate")
    payroll_k, _ = latest_non_null(labor, "payroll_change_k")

    target_low, target_date = latest_non_null(rates_d, "dfedtarl")
    target_high, _ = latest_non_null(rates_d, "dfedtaru")
    effr, effr_date = latest_non_null(rates_d, "dff")
    dgs2, _ = latest_non_null(rates_d, "dgs2")
    dgs10, _ = latest_non_null(rates_d, "dgs10")
    target_mid = (float(target_low) + float(target_high)) / 2.0

    sept_dots = dots.loc[dots["meeting"] == "September 2026", "dot"]
    june_dots = dots.loc[dots["meeting"] == "June 2026", "dot"]
    hold_n = int((sept_dots == 3.875).sum())
    one_more_n = int((sept_dots == 4.125).sum())
    two_more_n = int((sept_dots == 4.375).sum())
    june_at_old_mid = int((june_dots == 3.625).sum())
    june_at_or_above_one_more = int((june_dots >= 4.125).sum())

    market_eoy = float(
        market.loc[market["label"] == "Dec FOMC (expected)", "implied_rate"].iloc[0]
    )
    sep_2026 = 4.1  # MANUAL: SEP Table 1, https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm
    wedge_bp = int(round((market_eoy - sep_2026) * 100))

    stats = {
        # Calendar
        "latest_month": month_label(cpi_date),
        "latest_month_short": f"{cpi_date.month}/{cpi_date.year}",
        "latest_cpi_month": month_label(cpi_date),
        "latest_pce_month": month_label(pce_date),
        "latest_labor_month": month_label(labor_date),
        "data_current_as_of": "9/17/2026",
        "decision_date_short": "9/16",
        "hike_effective_date": "9/17",
        "meeting_dates": "9/15 to 9/16",
        "next_meeting_dates": "10/27 to 10/28",
        "next_meeting_decision_date": "10/28",
        "next_sep_meeting_dates": "12/8 to 12/9",
        "next_pce_date": "9/30",
        "next_cpi_date": "10/14",
        "release_note": (
            "FOMC statement and SEP released 9/16/2026. "
            f"CPI through {month_label(cpi_date)}; PCE through {month_label(pce_date)}; "
            f"unemployment through {month_label(labor_date)}. "
            f"Daily effective funds rate last printed {month_day(effr_date)}."
        ),
        # Policy decision. MANUAL: https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm
        "target_lower": round(float(target_low), 2),
        "target_upper": round(float(target_high), 2),
        "target_range": f"{float(target_low):.2f} to {float(target_high):.2f}",
        "target_mid": round(target_mid, 3),
        "prior_target_lower": 3.50,
        "prior_target_upper": 3.75,
        "hike_bp": 25,
        "vote_for": 12,
        "vote_against": 0,
        "vote_split": "12-0",
        "iorb": 3.90,  # MANUAL: https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a1.htm
        "current_effr": round(float(effr), 2),
        "effr_as_of": month_day(effr_date),
        "dgs2": round(float(dgs2), 2),
        "dgs10": round(float(dgs10), 2),
        "spread_bps": int(round((float(dgs10) - float(dgs2)) * 100)),
        # September SEP medians. MANUAL: https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm
        "sep_funds_2026": 4.1,
        "sep_funds_2027": 4.1,
        "sep_funds_2028": 3.9,
        "sep_funds_2029": 3.6,
        "sep_funds_longer": 3.2,
        "sep_pce_2026": 3.7,
        "sep_pce_2027": 2.3,
        "sep_pce_2028": 2.1,
        "sep_corepce_2026": 3.4,
        "sep_corepce_2027": 2.5,
        "sep_gdp_2026": 2.3,
        "sep_gdp_2027": 2.4,
        "sep_unrate_2026": 4.1,
        "sep_unrate_2027": 4.1,
        "sep_unrate_longer": 4.2,
        "fed_inflation_goal": 2.0,
        # June SEP medians. MANUAL: https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260617.htm
        "jun_funds_2026": 3.8,
        "jun_funds_2027": 3.6,
        "jun_funds_2028": 3.4,
        "jun_funds_longer": 3.1,
        "jun_pce_2026": 3.6,
        "jun_corepce_2026": 3.3,
        "jun_gdp_2026": 2.2,
        "jun_unrate_2026": 4.3,
        "funds_shift_2026_bp": 30,
        "funds_shift_2027_bp": 50,
        "funds_shift_2028_bp": 50,
        "funds_shift_longer_bp": 10,
        "pce_shift_2026_pp": 0.1,
        "corepce_shift_2026_pp": 0.1,
        "gdp_shift_2026_pp": 0.1,
        "unrate_shift_2026_pp": -0.2,
        # 2026 dots
        "dots_total": int(len(sept_dots)),
        "dots_hold": hold_n,
        "dots_one_more": one_more_n,
        "dots_two_more": two_more_n,
        "dots_at_least_one_more": one_more_n + two_more_n,
        "dot_hold_level": 3.875,
        "dot_one_more_level": 4.125,
        "dot_two_more_level": 4.375,
        "one_more_range_upper": 4.25,
        "jun_target_mid": 3.625,
        "june_dots_at_old_mid": june_at_old_mid,
        "june_dots_at_or_above_one_more": june_at_or_above_one_more,
        # Market snapshot. MANUAL: https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm (SEP) and post-meeting fed funds futures recaps in data/raw/sources.json
        "market_oct_hike_pct": 50,
        "market_dec_hike_pct": 79,
        "market_oct_implied": 4.00,
        "market_implied_eoy2026": round(market_eoy, 2),
        "wedge_to_dots_bp": wedge_bp,
        "wedge_to_dots_abs_bp": abs(wedge_bp),
        # Realized macro
        "cpi_yoy": round(float(cpi_yoy), 1),
        "cpi_mom": round(float(cpi_mom), 1),
        "core_cpi_yoy": round(float(core_cpi_yoy), 1),
        "core_cpi_mom": round(float(core_cpi_mom), 1),
        "pce_yoy": round(float(pce_yoy), 1),
        "core_pce_yoy": round(float(core_pce_yoy), 1),
        "unrate": round(float(unrate), 1),
        "payroll_k": int(round(float(payroll_k))),
        "pce_gap_pp": round(float(pce_yoy) - 2.0, 1),
        "sep_pce_gap_pp": round(3.7 - 2.0, 1),
        "unrate_gap_vs_longer_pp": round(float(unrate) - 4.2, 1),
        "target_date": month_day(target_date),
    }

    if stats["dots_total"] != 18:
        raise RuntimeError(f"Expected 18 September dots, found {stats['dots_total']}")
    if stats["dots_one_more"] != 12:
        raise RuntimeError("September 2026 one-more-hike cluster must be 12")

    out = STATS_DIR / "summary_stats.json"
    out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"  wrote {out} ({len(stats)} keys)")


if __name__ == "__main__":
    main()
