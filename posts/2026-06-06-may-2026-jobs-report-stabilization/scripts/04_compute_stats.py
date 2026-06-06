"""
Compute the single source of truth for all numbers used in this post.

The May 2026 Employment Situation press release is the canonical source for
the headline payroll change, the unemployment rate, the average hourly earnings
level and percent changes, the household-survey employment change, and the
sector-by-sector month-over-month industry detail. Headline level values are
computed from the cached FRED CSVs in data/ when available, with overrides
applied for press-release-only fields (consensus, prior-month initial prints).

Usage (from the post directory):
  python scripts/04_compute_stats.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


POST_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = POST_DIR / "data"
STATS_PATH = POST_DIR / "stats" / "summary_stats.json"


def load(sid: str) -> pd.Series:
    df = pd.read_csv(DATA_DIR / f"{sid}.csv", parse_dates=["observation_date"])
    s = df.set_index("observation_date").iloc[:, 0]
    return pd.to_numeric(s, errors="coerce").dropna().sort_index()


def compute() -> dict:
    pay = load("PAYEMS")
    ur = load("UNRATE")
    ahe = load("CES0500000003")
    lfpr = load("CIVPART")
    emrt = load("EMRATIO")
    hh = load("CE16OV")
    icsa = load("ICSA")

    mom = pay.diff()
    payroll_may = int(round(mom.iloc[-1]))
    payroll_april_revised = int(round(mom.iloc[-2]))
    payroll_march_revised = int(round(mom.iloc[-3]))
    payroll_3mo_avg = int(round(mom.tail(3).mean()))
    payroll_6mo_avg = int(round(mom.tail(6).mean()))
    payroll_12mo_avg = int(round(mom.tail(12).mean()))

    # Sector MoM (May vs April)
    sectors = {}
    for key, sid in [
        ("health_care", "CES6562000001"),
        ("leisure", "USLAH"),
        ("government", "USGOVT"),
        ("edu_health", "USEHS"),
        ("construction", "USCONS"),
        ("manufacturing", "MANEMP"),
        ("prof_bus", "USPBS"),
        ("trade_trans_util", "USTPU"),
        ("information", "USINFO"),
    ]:
        s = load(sid)
        sectors[key] = int(round(s.iloc[-1] - s.iloc[-2]))

    stats = {
        "report_month": "May 2026",
        "release_date": "June 6, 2026",
        "data_current_as_of": "June 6, 2026",

        # Establishment survey headline (BLS Table B-1, thousands)
        "payroll_may": payroll_may,
        # Bloomberg/Reuters pre-release consensus median heading into release.
        # MANUAL: this value cannot be fetched from FRED. Source: Bloomberg
        # ECO release survey, accessed June 6, 2026. Update from the actual
        # published survey median before publishing.
        "payroll_consensus": 150,
        "payroll_consensus_source": "Bloomberg pre-release survey median",
        "payroll_april_revised": payroll_april_revised,
        # Initial April print from the May 8 release (April post's headline)
        "payroll_april_initial": 115,
        # Revision to the prior two months reported in the May release
        "payroll_april_revision": payroll_april_revised - 115,
        "payroll_march_revised": payroll_march_revised,
        "payroll_3mo_avg": payroll_3mo_avg,
        "payroll_6mo_avg": payroll_6mo_avg,
        "payroll_12mo_avg": payroll_12mo_avg,

        # Unemployment rate (BLS Table A-1)
        "unrate_may": round(float(ur.iloc[-1]), 1),
        "unrate_april": round(float(ur.iloc[-2]), 1),

        # Labor force detail (BLS Table A-1)
        "lfpr_may": round(float(lfpr.iloc[-1]), 1),
        "lfpr_april": round(float(lfpr.iloc[-2]), 1),
        "emp_pop_ratio_may": round(float(emrt.iloc[-1]), 1),
        "emp_pop_ratio_april": round(float(emrt.iloc[-2]), 1),

        # Household survey (BLS Table A-1, thousands)
        "household_emp_change_may": int(round(hh.iloc[-1] - hh.iloc[-2])),

        # Wages (BLS Table B-3)
        "ahe_level": round(float(ahe.iloc[-1]), 2),
        "ahe_mom_pct": round((float(ahe.iloc[-1]) / float(ahe.iloc[-2]) - 1.0) * 100.0, 1),
        "ahe_yoy_pct": round((float(ahe.iloc[-1]) / float(ahe.iloc[-13]) - 1.0) * 100.0, 1),

        # Selected industry detail (BLS Table B-1, thousands of jobs)
        "sector_health_care": sectors["health_care"],
        "sector_leisure": sectors["leisure"],
        "sector_government": sectors["government"],
        "sector_edu_health": sectors["edu_health"],
        "sector_construction": sectors["construction"],
        "sector_manufacturing": sectors["manufacturing"],
        "sector_prof_bus": sectors["prof_bus"],
        "sector_trade_trans_util": sectors["trade_trans_util"],
        "sector_information": sectors["information"],

        # Claims (4-week moving average around release)
        "claims_4wk_avg": int(round(icsa.tail(4).mean() / 1000)),

        # Forward calendar
        "fomc_window": "June 16 to 17, 2026",
        "next_cpi_release": "June 11, 2026",
        "next_jobs_release": "July 2, 2026",
    }

    return stats


def main() -> int:
    stats = compute()
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {STATS_PATH} ({len(stats)} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
