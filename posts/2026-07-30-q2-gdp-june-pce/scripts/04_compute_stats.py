"""
04_compute_stats.py
===================
STEP 3 of 3 in the data pipeline.

What this script does (beginner version)
----------------------------------------
Builds stats/summary_stats.json - a single dictionary of every number the
blog post prints in prose or metric cards.

Why JSON exists
---------------
The Quarto post (index.qmd) must not hard-code release figures like "1.5%".
Instead it writes expressions such as:
    `{python} fmt(stats['gdp_growth_q2'])`
When BEA revises a number, you re-run this script (and maybe 01/02), re-render,
and every place that uses that key updates automatically.

Where numbers come from
-----------------------
1. Clean CSVs from 02_clean_data.py (especially May PCE y/y from FRED history).
2. MANUAL values typed from the BEA release PDFs/tables on print day, each
   tagged with `# MANUAL:` and a Source URL on the next line (lint rule).

Rounding
--------
Most growth rates: 1 decimal (r1).
Contribution tables that BEA prints to 2 decimals: keep 2 decimals.

Focus window
------------
Quarter: Q2 2026 (April-June).
Month: June 2026 Personal Income and Outlays (same release day as GDP advance).

Pipeline order
--------------
    python scripts/01_fetch_data.py
    python scripts/02_clean_data.py
    python scripts/04_compute_stats.py   # you are here

Run from the post folder:
    python scripts/04_compute_stats.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

POST_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"
OUT_PATH = STATS_DIR / "summary_stats.json"

GDP_PATH = CLEAN_DIR / "gdp_quarterly.csv"
MONTHLY_PATH = CLEAN_DIR / "monthly_pce.csv"


def r1(val) -> float | None:
    """Round to one decimal for display (e.g. 1.53 -> 1.5)."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return round(float(val), 1)


def r2(val) -> float | None:
    """Round to two decimals (contribution tables often use 2.12 style)."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return round(float(val), 2)


def main() -> None:
    # Load clean series so we can pull FRED-derived fields (e.g. May y/y).
    df_q = pd.read_csv(GDP_PATH, index_col="date", parse_dates=True).sort_index()
    df_m = pd.read_csv(MONTHLY_PATH, index_col="date", parse_dates=True).sort_index()

    # Prefer explicit Q2 / June rows after the 02_clean_data.py overlays.
    # Quarterly dates use the first day of the quarter (2026-04-01 = Q2).
    q2 = df_q.loc["2026-04-01"] if "2026-04-01" in df_q.index.strftime("%Y-%m-%d") else df_q.iloc[-1]
    q1 = df_q.loc["2026-01-01"] if "2026-01-01" in df_q.index.strftime("%Y-%m-%d") else df_q.iloc[-2]

    june = df_m.loc["2026-06-01"] if "2026-06-01" in df_m.index.strftime("%Y-%m-%d") else df_m.iloc[-1]
    may = df_m.loc["2026-05-01"] if "2026-05-01" in df_m.index.strftime("%Y-%m-%d") else df_m.iloc[-2]

    # ------------------------------------------------------------------
    # MANUAL values from BEA releases dated 07/30/2026.
    # Prefer these over lagged FRED for the advance GDP / PIO prints.
    # Source GDP: https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026
    # Source PIO: https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026
    # Component detail cross-checked with Trading Economics BEA-sourced tables.
    # ------------------------------------------------------------------
    stats = {
        # Metadata
        "latest_quarter": "Q2 2026",
        "latest_quarter_label": "April-June 2026",
        "latest_month": "June 2026",
        "latest_month_short": "Jun 2026",
        "release_type": "Advance estimate",
        "release_date": "July 30, 2026",
        "release_date_us": "07/30/2026",
        "data_current_as_of": "07/30/2026",
        "release_note": (
            "BEA advance estimate for Q2 2026 GDP and Personal Income and Outlays "
            "for June 2026, both released 07/30/2026. Second GDP estimate due 08/26/2026."
        ),
        "source_url_gdp": "https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026",
        "source_url_pce": "https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026",
        # Headline GDP
        # MANUAL: BEA advance estimate headline and private final sales
        # Source: https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026
        "gdp_growth_q2": 1.5,
        "gdp_growth_q1": 2.1,
        "gdp_growth_consensus": 2.1,
        "final_sales_private_q2": 3.9,
        "final_sales_private_q1": 1.7,
        "current_dollar_gdp_q2": 7.9,
        # Component growth rates (SAAR %)
        # MANUAL: BEA advance component detail (equipment, PNFI, trade, gov)
        # Source: https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026
        "pce_growth_q2": 3.2,
        "pce_growth_q1": 0.5,
        "equipment_growth_q2": 15.2,
        "equipment_growth_q1": 15.8,
        "pnfi_growth_q2": 8.4,
        "pnfi_growth_q1": 10.6,
        "structures_growth_q2": -5.0,
        "ip_products_growth_q2": 8.8,
        "residential_growth_q2": 1.5,
        "exports_growth_q2": 4.5,
        "imports_growth_q2": 11.5,
        "govt_growth_q2": -0.8,
        # Contributions (pp)
        # MANUAL: BEA-sourced contribution tables for Q2 advance (two decimals)
        # Source: https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026
        "inventory_contribution_q2": -0.67,
        "pce_contribution_q2": 2.12,
        "gpdi_contribution_q2": 0.53,
        "govt_contribution_q2": -0.14,
        "exports_contribution_q2": 0.50,
        "imports_contribution_q2": -1.51,
        "netex_contribution_q2": -1.01,
        # Q1 contribution context from third estimate
        # Source: https://www.bea.gov/news/2026/gdp-third-estimate-industries-corporate-profits-state-gdp-and-state-personal-income-1st
        "pce_contribution_q1": 0.37,
        "gpdi_contribution_q1": 1.35,
        "govt_contribution_q1": 0.74,
        "netex_contribution_q1": -0.37,
        # Contribution shifts (Q2 minus Q1)
        "pce_contribution_delta": 1.75,
        "gpdi_contribution_delta": -0.82,
        "govt_contribution_delta": -0.88,
        "netex_contribution_delta": -0.64,
        # Private demand gap (private final sales minus GDP)
        "demand_gap_q2": 2.4,
        "demand_gap_q1": -0.4,
        # Q1 investment context for mix chart
        # Source: https://www.bea.gov/news/2026/gdp-third-estimate-industries-corporate-profits-state-gdp-and-state-personal-income-1st
        "structures_growth_q1": -4.7,
        "ip_products_growth_q1": 13.8,
        "residential_growth_q1": -7.8,
        # Quarterly price indexes (SAAR %)
        # MANUAL: BEA advance price indexes (GDP purchases, PCE, core PCE)
        # Source: https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026
        "gdp_price_index_q2": 5.7,  # gross domestic purchases price index
        "gdp_price_index_q1": 3.6,
        "pce_price_saar_q2": 5.1,
        "pce_price_saar_q1": 4.6,
        "core_pce_price_saar_q2": 3.4,
        "core_pce_price_saar_q1": 4.4,
        # June monthly PCE (PIO release)
        # MANUAL: BEA Personal Income and Outlays, June 2026
        # Source: https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026
        "pce_mom_june": -0.1,
        "core_pce_mom_june": 0.1,
        "pce_yoy_june": 3.7,
        "core_pce_yoy_june": 3.3,
        "pce_yoy_may": r1(may.get("pce_yoy", 4.1)) if hasattr(may, "get") else r1(may["pce_yoy"]),
        "core_pce_yoy_may": r1(may.get("core_pce_yoy", 3.3)) if hasattr(may, "get") else r1(may["core_pce_yoy"]),
        "real_pce_mom_june": 0.4,
        "personal_income_mom_june": 0.2,
        "dpi_mom_june": 0.2,
        "nominal_pce_mom_june": 0.3,
        "saving_rate_june": 2.7,
        "personal_income_change_bn": 54.9,
        "dpi_change_bn": 48.3,
        "pce_change_bn": 65.2,
        "pce_services_change_bn": 58.2,
        "pce_goods_change_bn": 7.0,
        # FRED-derived residual heat (if available)
        "core_pce_ann3_june": r1(june["core_pce_ann3"]) if "core_pce_ann3" in june.index and pd.notna(june.get("core_pce_ann3", np.nan) if hasattr(june, "get") else june["core_pce_ann3"] if "core_pce_ann3" in june.index else np.nan) else None,
        "pce_ann3_june": r1(june["pce_ann3"]) if "pce_ann3" in june.index and pd.notna(june["pce_ann3"]) else None,
        # Policy calendar
        "fed_funds_upper": 4.50,
        "second_estimate_date": "August 26, 2026",
        "second_estimate_date_us": "08/26/2026",
        # Clean CSV echoes for debugging (not required in prose)
        "fred_gdp_growth_q2": r1(q2["gdp_growth"]) if "gdp_growth" in q2.index else None,
        "fred_pce_growth_q2": r1(q2["pce_growth"]) if "pce_growth" in q2.index else None,
        "fred_equipment_growth_q2": r1(q2["equipment_growth"]) if "equipment_growth" in q2.index else None,
        "fred_gdp_growth_q1": r1(q1["gdp_growth"]) if "gdp_growth" in q1.index else None,
    }

    # Fix May YoY fallbacks if FRED already has them; else use PIO context.
    if stats["pce_yoy_may"] is None:
        # MANUAL: May headline PCE y/y fallback if FRED lags
        # Source: https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026
        stats["pce_yoy_may"] = 4.1
    if stats["core_pce_yoy_may"] is None:
        # MANUAL: May core PCE y/y fallback if FRED lags
        # Source: https://www.bea.gov/news/2026/personal-income-and-outlays-june-2026
        stats["core_pce_yoy_may"] = 3.3

    # Safer access for ann3
    try:
        if "core_pce_ann3" in df_m.columns and "2026-06-01" in df_m.index.strftime("%Y-%m-%d"):
            stats["core_pce_ann3_june"] = r1(df_m.loc["2026-06-01", "core_pce_ann3"])
        if "pce_ann3" in df_m.columns and "2026-06-01" in df_m.index.strftime("%Y-%m-%d"):
            stats["pce_ann3_june"] = r1(df_m.loc["2026-06-01", "pce_ann3"])
    except Exception:
        pass

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)

    required = [
        "latest_month",
        "data_current_as_of",
        "gdp_growth_q2",
        "final_sales_private_q2",
        "pce_growth_q2",
        "core_pce_yoy_june",
        "pce_yoy_june",
        "pce_contribution_q2",
        "netex_contribution_q2",
        "equipment_growth_q2",
    ]
    missing = [key for key in required if stats.get(key) is None]
    print(f"Saved {len(stats)} keys to {OUT_PATH}")
    print(f"Missing required keys: {missing if missing else '(none)'}")
    print(
        f"Key print: GDP {stats['gdp_growth_q2']}% | private sales "
        f"{stats['final_sales_private_q2']}% | PCE {stats['pce_growth_q2']}% | "
        f"core YoY {stats['core_pce_yoy_june']}%"
    )


if __name__ == "__main__":
    main()
