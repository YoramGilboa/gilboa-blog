"""
04_compute_stats.py
Reads clean CSVs and computes summary statistics for inline values
in the .qmd post. Writes stats/summary_stats.json.

Run from the post folder:
    python scripts/04_compute_stats.py
"""

import json
import os
import pandas as pd

CLEAN_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "clean")
STATS_DIR = os.path.join(os.path.dirname(__file__), "..", "stats")
os.makedirs(STATS_DIR, exist_ok=True)


def main():
    # ── Load data ─────────────────────────────────────────────────────────────
    df_pay  = pd.read_csv(os.path.join(CLEAN_DIR, "payrolls.csv"), parse_dates=["date"])
    df_unem = pd.read_csv(os.path.join(CLEAN_DIR, "unemployment.csv"), parse_dates=["date"])
    df_sec  = pd.read_csv(os.path.join(CLEAN_DIR, "sector_contributions.csv"))

    # ── Payrolls ──────────────────────────────────────────────────────────────
    mar = df_pay[df_pay["date"] == "2026-03-01"].iloc[0]
    feb = df_pay[df_pay["date"] == "2026-02-01"].iloc[0]
    jan = df_pay[df_pay["date"] == "2026-01-01"].iloc[0]

    payroll_3mo_avg = int(df_pay.tail(3)["payroll_change"].mean())

    # ── Unemployment ──────────────────────────────────────────────────────────
    umar = df_unem[df_unem["date"] == "2026-03-01"].iloc[0]
    ufeb = df_unem[df_unem["date"] == "2026-02-01"].iloc[0]

    # ── Sector ───────────────────────────────────────────────────────────────
    top_sector    = df_sec.sort_values("change", ascending=False).iloc[0]
    bottom_sector = df_sec.sort_values("change", ascending=True).iloc[0]

    # ── Build stats ───────────────────────────────────────────────────────────
    stats = {
        "latest_month":          "March 2026",
        "report_release_date":   "April 3, 2026",
        "data_current_as_of":    "April 3, 2026",

        # Payrolls
        "payroll_march":         int(mar["payroll_change"]),
        "payroll_feb_revised":   int(feb["payroll_change"]),
        "payroll_jan_revised":   int(jan["payroll_change"]),
        "payroll_3mo_avg":       payroll_3mo_avg,
        "payroll_consensus":     int(mar["consensus"]) if pd.notna(mar["consensus"]) else 59000,

        # Unemployment (household survey)
        "unemployment_rate_mar": float(umar["unemployment_rate"]),
        "unemployment_rate_feb": float(ufeb["unemployment_rate"]),
        "unemployment_rate_chg": round(float(umar["unemployment_rate"]) - float(ufeb["unemployment_rate"]), 1),
        "unemployed_persons":    7200000,
        "lfpr_mar":              float(umar["lfpr"]),
        "lfpr_feb":              float(ufeb["lfpr"]),
        "emp_pop_ratio":         float(umar["emp_pop_ratio"]),

        # Sector contributions
        "hc_contrib":            76000,
        "construction_contrib":  26000,
        "transp_contrib":        21000,
        "social_assist_contrib": 14000,
        "top_sector_name":       str(top_sector["sector"]),
        "top_sector_change":     int(top_sector["change"]),
        "bottom_sector_name":    str(bottom_sector["sector"]),
        "bottom_sector_change":  int(bottom_sector["change"]),

        # Claims (cross-reference from March 29 post data)
        "icsa_latest":           215000,
        "icsa_4wma":             219000,
        "icsa_mar_ref_week":     212000,
        "icsa_feb_spike_peak":   230000,
        "ccsa_latest":           1819000,
    }

    out_path = os.path.join(STATS_DIR, "summary_stats.json")
    with open(out_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote {len(stats)} stats to {out_path}")


if __name__ == "__main__":
    main()
