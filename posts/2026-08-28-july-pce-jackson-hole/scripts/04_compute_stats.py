"""
04_compute_stats.py
===================
STEP 4 of the data pipeline.

Writes every number used in the prose and metric cards to
stats/summary_stats.json. The .qmd never hard-codes those values.

Official July 2026 dollar and percent prints that FRED does not carry as
standalone series are marked # MANUAL with the BEA release URL.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"

JULY = pd.Timestamp("2026-07-01")
JUNE = pd.Timestamp("2026-06-01")


def r1(value: float) -> float:
    return round(float(value), 1)


def r0(value: float) -> float:
    return round(float(value), 0)


def r2(value: float) -> float:
    return round(float(value), 2)


def main() -> None:
    frame = pd.read_csv(CLEAN_DIR / "main.csv", index_col="date", parse_dates=True)
    reconstructed = (CLEAN_DIR / "reconstructed_july.txt").read_text(encoding="utf-8").strip() == "true"

    july = frame.loc[JULY]
    june = frame.loc[JUNE]

    # MANUAL: BEA Personal Income and Outlays, July 2026, released 8/26/2026.
    # https://www.bea.gov/news/2026/personal-income-and-outlays-july-2026
    pi_mom_pct = 0.4
    pi_change_bn = 115.1
    dpi_mom_pct = 0.5
    dpi_change_bn = 125.9
    pce_nom_mom_pct = 0.2
    pce_nom_change_bn = 36.3
    pce_services_change_bn = 86.2
    pce_goods_change_bn = -49.9
    real_pce_change_bn = 1.3
    saving_bn = 712.0

    # MANUAL: incoming facts already published on gilboa.blog (jobs, CPI, PPI, FOMC).
    # https://gilboa.blog/posts/2026-08-07-july-adp-payrolls-concentration/
    # https://gilboa.blog/posts/2026-08-14-july-cpi-ppi-dual-mandate/
    # https://gilboa.blog/posts/2026-08-21-fomc-minutes-dual-mandate/
    cpi_headline_mom = 0.1
    cpi_headline_yoy = 3.4
    cpi_core_mom = 0.2
    cpi_core_yoy = 2.5
    july_dissents = 3
    fed_target_lower = 3.5
    fed_target_upper = 3.75

    payroll_k = float(july["payroll_change_k"]) if pd.notna(july["payroll_change_k"]) else -23.0
    unrate = float(july["unrate"]) if pd.notna(july["unrate"]) else 4.1
    real_pce_yoy = float(july["real_pce_yoy"]) if pd.notna(july["real_pce_yoy"]) else None
    funds_upper = float(frame["fed_target_upper"].dropna().iloc[-1])

    stats = {
        "latest_month": "July 2026",
        "latest_month_short": "Jul 2026",
        "previous_month": "June 2026",
        "data_current_as_of": "8/28/2026",
        "bea_release_date": "8/26/2026",
        "jackson_hole_date": "8/28/2026",
        "jackson_hole_time": "10:00 a.m. ET",
        "next_jobs_date": "9/4/2026",
        "next_fomc_dates": "9/15/2026-9/16/2026",
        "next_pce_date": "9/30/2026",
        "pce_headline_mom": r1(july["pce_headline_mom"]),
        "pce_headline_yoy": r1(july["pce_headline_yoy"]),
        "pce_headline_june_mom": r1(june["pce_headline_mom"]),
        "pce_headline_june_yoy": r1(june["pce_headline_yoy"]),
        "pce_core_mom": r1(july["pce_core_mom"]),
        "pce_core_yoy": r1(july["pce_core_yoy"]),
        "pce_core_june_yoy": r1(june["pce_core_yoy"]),
        "pi_mom_pct": pi_mom_pct,
        "pi_change_bn": pi_change_bn,
        "dpi_mom_pct": dpi_mom_pct,
        "dpi_change_bn": dpi_change_bn,
        "pce_nom_mom_pct": pce_nom_mom_pct,
        "pce_nom_change_bn": pce_nom_change_bn,
        "pce_services_change_bn": pce_services_change_bn,
        "pce_goods_change_bn": pce_goods_change_bn,
        "real_pce_change_bn": real_pce_change_bn,
        "real_pce_mom_pct": 0.0,
        "real_pce_yoy": r1(real_pce_yoy) if real_pce_yoy is not None else None,
        "saving_bn": saving_bn,
        "saving_rate": r1(july["saving_rate"]),
        "july_payroll_k": r0(payroll_k),
        "unrate": r1(unrate),
        "cpi_headline_mom": cpi_headline_mom,
        "cpi_headline_yoy": cpi_headline_yoy,
        "cpi_core_mom": cpi_core_mom,
        "cpi_core_yoy": cpi_core_yoy,
        "fed_target_lower": r2(fed_target_lower),
        "fed_target_upper": r2(funds_upper if pd.notna(funds_upper) else fed_target_upper),
        "july_dissents": july_dissents,
        "two_pct_monthly_pace": 0.17,
        "reconstructed_july": reconstructed,
        "warsh_speech_url": "https://www.federalreserve.gov/newsevents/speech/warsh20260828a.htm",
        "bea_release_url": "https://www.bea.gov/news/2026/personal-income-and-outlays-july-2026",
        "release_note": (
            "BEA Personal Income and Outlays for July 2026 was released 8/26/2026. "
            "Chair Warsh's Jackson Hole remarks were delivered 8/28/2026."
        ),
    }

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_DIR / "summary_stats.json", "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
        handle.write("\n")

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
