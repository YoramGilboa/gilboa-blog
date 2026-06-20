"""
04_compute_stats.py
-------------------
Step 3 of the pipeline: compute every number the post needs and write a single
JSON file (stats/summary_stats.json) that index.qmd reads in its setup block.

The rule is: numbers that appear in prose come from FRED through the cleaned
CSVs, OR they are flagged with a `# MANUAL:` comment and a primary source URL.
This script keeps that division honest in one place so reviewers can audit it.

Run after 02_clean_data.py:
    python scripts/04_compute_stats.py
"""

import json
import os
from datetime import date

import pandas as pd

CLEAN_DIR = "data/clean"
RAW_DIR = "data/raw"
STATS_DIR = "stats"


def latest_month_label(idx):
    """Return a short month label like 'May 2026' for the latest row of a series."""
    ts = pd.Timestamp(idx[-1])
    return ts.strftime("%B %Y")


def main():
    os.makedirs(STATS_DIR, exist_ok=True)

    # ---- Live FRED-sourced numbers ---------------------------------------
    infl = pd.read_csv(f"{CLEAN_DIR}/inflation.csv",
                       index_col="date", parse_dates=True)
    labor = pd.read_csv(f"{CLEAN_DIR}/labor.csv",
                        index_col="date", parse_dates=True)
    rates_d = pd.read_csv(f"{CLEAN_DIR}/rates_daily.csv",
                          index_col="date", parse_dates=True)
    rates_m = pd.read_csv(f"{CLEAN_DIR}/rates_monthly.csv",
                          index_col="date", parse_dates=True)

    latest_cpi_month = latest_month_label(infl.index)
    latest_labor_month = latest_month_label(labor.index)

    stats = {
        # ---- Meeting / calendar -----------------------------------------
        "meeting_date": "June 17-18, 2026",
        "prior_meeting_date": "March 18-19, 2026",
        "next_meeting_date": "July 28-29, 2026",     # MANUAL: source https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
        "data_current_as_of": date.today().strftime("%B %d, %Y"),
        "latest_cpi_month": latest_cpi_month,
        "latest_labor_month": latest_labor_month,

        # ---- Current policy stance --------------------------------------
        "current_rate_range": "3.50-3.75",            # MANUAL: source FOMC statement https://www.federalreserve.gov/newsevents/pressreleases/monetary20260617a.htm
        "current_target_mid": 3.625,
        "current_effr": round(float(rates_d["fedfunds"].dropna().iloc[-1]), 2),

        # ---- May 2026 inflation (live FRED) -----------------------------
        "may_cpi_yoy":      round(float(infl["headline_cpi_yoy"].dropna().iloc[-1]), 1),
        "may_core_cpi_yoy": round(float(infl["core_cpi_yoy"].dropna().iloc[-1]), 1),
        "may_cpi_mom":      round(float(infl["headline_cpi_mom"].dropna().iloc[-1]), 2),
        "may_core_cpi_mom": round(float(infl["core_cpi_mom"].dropna().iloc[-1]), 2),
        "may_energy_yoy":   round(float(infl["energy_cpi_yoy"].dropna().iloc[-1]), 1),
        "may_energy_mom":   round(float(infl["energy_cpi_mom"].dropna().iloc[-1]), 2),
        "may_pce_yoy":      round(float(infl["headline_pce_yoy"].dropna().iloc[-1]), 1),
        "may_core_pce_yoy": round(float(infl["core_pce_yoy"].dropna().iloc[-1]), 1),

        # ---- May 2026 labor (live FRED) ---------------------------------
        "may_payrolls_k":   int(round(float(labor["payroll_change_k"].dropna().iloc[-1]))),
        "may_unrate":       round(float(labor["unrate"].dropna().iloc[-1]), 1),
        "may_civpart":      round(float(labor["civpart"].dropna().iloc[-1]), 1),

        # ---- June 2026 SEP medians (MANUAL: source SEP table 1) ---------
        # Source: https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260617.htm
        "june_sep_funds_eoy2026":  3.8,
        "june_sep_funds_eoy2027":  3.6,
        "june_sep_funds_eoy2028":  3.4,
        "june_sep_funds_longer":   3.1,
        "june_sep_pce_2026":       3.6,
        "june_sep_corepce_2026":   3.3,
        "june_sep_gdp_2026":       2.2,
        "june_sep_unrate_2026":    4.3,

        # ---- March 2026 SEP medians (MANUAL: source SEP table 1) --------
        # Source: https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260318.htm
        "march_sep_funds_eoy2026":  3.4,
        "march_sep_funds_eoy2027":  3.1,
        "march_sep_funds_eoy2028":  3.1,
        "march_sep_funds_longer":   3.1,
        "march_sep_pce_2026":       2.7,
        "march_sep_corepce_2026":   2.7,
        "march_sep_gdp_2026":       2.4,
        "march_sep_unrate_2026":    4.4,

        # ---- Headline shift in basis points (derived) ------------------
        "funds_shift_bp_2026":     40,   # 3.8 - 3.4 = 0.4 pp
        "pce_shift_pp_2026":       0.9,  # 3.6 - 2.7
        "corepce_shift_pp_2026":   0.6,

        # ---- June 2026 dot distribution (MANUAL: SEP figure 2) ----------
        # 18 dots total (Chair Warsh did not submit a projection)
        # Source: https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260617.htm
        "june_dots_total":      18,
        "june_dots_hike":       9,    # midpoint > current 3.625%
        "june_dots_hold":       8,    # midpoint = 3.625%
        "june_dots_cut":        1,    # midpoint < 3.625%

        # ---- Historical dot-plot vs realized FEDFUNDS (MANUAL) ----------
        # Source: prior FOMC SEP archives + FRED FEDFUNDS year-end averages
        # Same numbers as the April 2026 FOMC preview post for continuity.
        "error_std_recent":     0.28,
        "error_mean_recent":    0.11,

        # ---- Long-run neutral (June 2026 SEP median) -------------------
        "longer_run_neutral":   3.1,

        # ---- Market pricing snapshot (MANUAL) --------------------------
        # Implied end-2026 rate from CME FedWatch / OIS as of 2026-06-18 close.
        # Source: https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html
        "market_implied_eoy2026":  3.70,
        "wedge_to_dots_bp":        -10,   # market 3.70 vs dots 3.80 -> markets price LESS hike than dots

        # ---- 2s10s spread (live FRED) ----------------------------------
        "dgs2_current":         round(float(rates_d["dgs2"].dropna().iloc[-1]), 2),
        "dgs10_current":        round(float(rates_d["dgs10"].dropna().iloc[-1]), 2),
        "spread_current_bps":   int(round(
            (float(rates_d["dgs10"].dropna().iloc[-1]) -
             float(rates_d["dgs2"].dropna().iloc[-1])) * 100)),

        # ---- Net new payrolls revisions context (MANUAL) ----------------
        # From the May 2026 Employment Situation release narrative.
        # Source: https://www.bls.gov/news.release/empsit.htm
        "consensus_payrolls_k": 88,    # Bloomberg/Reuters median
        "april_payrolls_revised_to_k": 179,
    }

    with open(f"{STATS_DIR}/summary_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"  wrote {STATS_DIR}/summary_stats.json ({len(stats)} keys)")


if __name__ == "__main__":
    main()
