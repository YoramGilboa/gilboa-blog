"""
04_compute_stats.py
-------------------
Build the compact JSON file used for inline numbers, KPI tiles, and chart
annotations in index.qmd.

Q1 2026 GDP headline values are sourced from the BEA second estimate
("preliminary") release dated May 29, 2026. Advance estimate values are
from the April 30, 2026 release. Component contributions are from
BEA NIPA Table 1.1.2. Historical context values are computed from clean CSVs.

Run from the post folder after 02_clean_data.py:
    python scripts/04_compute_stats.py
"""

import json
import os

import numpy as np
import pandas as pd


GDP_PATH = "data/clean/gdp_quarterly.csv"
MONTHLY_PATH = "data/clean/monthly_indicators.csv"
EXPANSION_PATH = "data/clean/expansion_indexed.csv"
OUT_PATH = "stats/summary_stats.json"


def r1(val):
    """Round numeric values to one decimal place for display."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return round(float(val), 1)


def main():
    df_q = pd.read_csv(GDP_PATH, index_col="date", parse_dates=True)
    df_m = pd.read_csv(MONTHLY_PATH, index_col="date", parse_dates=True)
    df_exp = pd.read_csv(EXPANSION_PATH)

    q1 = df_q.loc["2026-01-01"]
    q4 = df_q.loc["2025-10-01"]
    latest_m = df_m.iloc[-1]
    prev_m = df_m.iloc[-2]

    # COVID expansion data
    covid_exp = df_exp[df_exp["expansion"] == "covid"]
    gfc_exp = df_exp[df_exp["expansion"] == "gfc"]

    stats = {
        # ── Dates and metadata ──
        "latest_quarter": "Q1 2026",
        "latest_quarter_label": "January-March 2026",
        "release_type": "Second estimate (preliminary)",
        "release_date": "May 29, 2026",
        "advance_release_date": "April 30, 2026",
        "data_current_as_of": "Q1 2026 GDP second estimate (BEA release: May 29, 2026)",
        "source_url": "https://www.bea.gov/news/2026/gross-domestic-product-first-quarter-2026-second-estimate",

        # ── Headline GDP growth (%, SAAR) ──
        # BEA second estimate (preliminary)
        "gdp_growth_revised": 1.6,
        # BEA advance estimate
        "gdp_growth_advance": 2.0,
        "gdp_revision": -0.4,
        "gdp_prev_quarter": r1(q4["gdp_growth"]),
        "gdp_prev_quarter_label": "Q4 2025",

        # ── Component contributions to GDP growth (pp) ──
        # BEA NIPA Table 1.1.2, second estimate
        "pce_contribution": 0.6,
        "gpdi_contribution": 1.5,
        "govt_contribution": 0.3,
        "netex_contribution": -0.8,

        # BEA advance estimate contributions
        "pce_contribution_advance": 1.1,
        "gpdi_contribution_advance": 1.2,
        "govt_contribution_advance": 0.3,
        "netex_contribution_advance": -0.6,

        # ── Consumer spending (%, SAAR) ──
        "pce_growth": r1(q1["pce_growth"]),
        "pce_growth_prev": r1(q4["pce_growth"]),
        "pce_durable_growth": r1(q1["pce_durable_growth"]),
        "pce_nondurable_growth": r1(q1["pce_nondurable_growth"]),
        "pce_services_growth": r1(q1["pce_services_growth"]),

        # ── Business investment (%, SAAR) ──
        "equipment_growth": r1(q1["equipment_growth"]),
        "equipment_growth_prev": r1(q4["equipment_growth"]),
        "pnfi_growth": r1(q1["pnfi_growth"]),
        "pnfi_growth_prev": r1(q4["pnfi_growth"]),

        # ── GPDI sub-components (hardcoded from BEA release) ──
        "residential_growth": -2.3,
        "inventory_change_q1": -40.2,
        "inventory_change_q4": -46.2,
        "inventory_contribution": -0.2,

        # ── Real disposable income (hardcoded from BEA/BLS) ──
        "real_dpi_mom_latest": -0.5,
        "real_dpi_q1_ann": -1.8,

        # ── Inflation ──
        "gdp_deflator_q1": r1(q1["gdp_deflator_growth"]),
        "gdp_deflator_advance": 2.5,
        "gdp_deflator_prev": r1(q4["gdp_deflator_growth"]),
        "core_pce_yoy_latest": r1(latest_m["core_pce_yoy"]),
        "core_pce_yoy_prev": r1(prev_m["core_pce_yoy"]),
        "pce_yoy_latest": r1(latest_m["pce_yoy"]),
        "latest_inflation_month": latest_m.name.strftime("%B %Y"),

        # ── Labor market ──
        "unemployment_latest": r1(latest_m["unrate"]),
        "unemployment_prev": r1(prev_m["unrate"]),
        "unemployment_month": latest_m.name.strftime("%B %Y"),
        "payroll_change_latest": int(latest_m["payroll_change"]),
        "payroll_3m_avg": int(latest_m["payroll_3m_avg"]),
        "consumer_sentiment_latest": r1(latest_m["consumer_sentiment"]),
        "consumer_sentiment_prev": r1(prev_m["consumer_sentiment"]),

        # ── Expansion comparison ──
        "current_expansion_quarters": int(covid_exp["quarters_since_trough"].max()),
        "current_expansion_growth": r1(covid_exp["gdp_indexed"].iloc[-1] - 100),
        "gfc_same_quarter_growth": r1(
            gfc_exp.loc[
                gfc_exp["quarters_since_trough"] == int(covid_exp["quarters_since_trough"].max()),
                "gdp_indexed"
            ].values[0] - 100
        ) if len(gfc_exp[gfc_exp["quarters_since_trough"] == int(covid_exp["quarters_since_trough"].max())]) > 0 else None,

        # ── Fed / market context ──
        "fed_rate_range": "4.25-4.50",
        "fed_next_meeting": "June 17-18, 2026",

        # ── Forward calendar ──
        "third_estimate_date": "June 25, 2026",
        "may_jobs_date": "June 6, 2026",
        "may_cpi_date": "June 11, 2026",
    }

    os.makedirs("stats", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Saved {len(stats)} stats to {OUT_PATH}\n")
    print("Key figures:")
    for key in [
        "gdp_growth_revised", "gdp_growth_advance", "gdp_revision",
        "pce_contribution", "gpdi_contribution", "equipment_growth",
        "core_pce_yoy_latest", "unemployment_latest",
    ]:
        val = stats[key]
        if isinstance(val, (int, float)):
            print(f"  {key:30s}: {val:+.1f}")
        else:
            print(f"  {key:30s}: {val}")


if __name__ == "__main__":
    main()
