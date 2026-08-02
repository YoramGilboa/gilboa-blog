"""
02_clean_data.py
================
STEP 2 of 3 in the data pipeline.

What this script does (beginner version)
----------------------------------------
1. Reads the raw FRED CSVs written by 01_fetch_data.py.
2. Computes the growth rates the charts need (m/m, y/y, SAAR, etc.).
3. Builds small "table" CSVs for contribution, bridge, and investment charts
   using the BEA release-day snapshot when FRED is still lagging.
4. Writes clean CSVs under data/clean/ that index.qmd plots directly.

This file is the **home of rate formulas**. Chart code in index.qmd only plots
columns; it does not re-derive the math.

Pipeline order
--------------
    python scripts/01_fetch_data.py
    python scripts/02_clean_data.py   # you are here
    python scripts/04_compute_stats.py

Run from the post folder:
    python scripts/02_clean_data.py

Canonical rate definitions
--------------------------
Month-over-month (m/m) for a price index I:
    mom = (I_t / I_{t-1} - 1) * 100
    Plain English: percent change from last month to this month.

Year-over-year (y/y):
    yoy = (I_t / I_{t-12} - 1) * 100
    Plain English: percent change vs the same month one year earlier.

Three-month annualized (ann3):
    ann3 = ((I_t / I_{t-3}) ** 4 - 1) * 100
    Plain English: take the last three months of change and scale it to a
    full year (useful residual-heat check).

Quarter-over-quarter annualized (SAAR) for a level series X:
    saar = ((X_t / X_{t-1}) ** 4 - 1) * 100
    Plain English: quarter-to-quarter growth, compounded as if it lasted a year.

FRED series A191RL1Q225SBEA is *already* published as SAAR percent change;
we use that column as-is for GDP growth history.

Outputs (data/clean/)
---------------------
    gdp_quarterly.csv       - SAAR growth series for charts
    monthly_pce.csv         - PCE price rates + income/labor
    contribution_shift.csv  - Q1 vs Q2 contributions
    gdp_bridge.csv          - waterfall steps for Figure 2
    private_demand.csv      - real GDP vs private final sales
    investment_mix.csv      - equipment / IP / structures / residential
    gdp_contributions.csv   - Q2-only contribution snapshot (compat)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"

RAW_Q = RAW_DIR / "fred_quarterly.csv"
RAW_M = RAW_DIR / "fred_monthly.csv"


def annualized_qoq(series: pd.Series) -> pd.Series:
    """
    Quarter-over-quarter compounded annualized percent change (SAAR).

    Example: if the level rises 0.5% in one quarter, SAAR is about 2.0%.
    """
    return ((series / series.shift(1)) ** 4 - 1) * 100


def mom_pct(series: pd.Series) -> pd.Series:
    """Month-over-month percent change."""
    return series.pct_change(1) * 100


def yoy_pct(series: pd.Series) -> pd.Series:
    """Year-over-year percent change (compare to 12 months earlier)."""
    return series.pct_change(12) * 100


def ann3_pct(series: pd.Series) -> pd.Series:
    """Three-month compounded annualized percent change."""
    return ((series / series.shift(3)) ** 4 - 1) * 100


def build_gdp_quarterly(df_q: pd.DataFrame, df_m: pd.DataFrame) -> pd.DataFrame:
    """
    Build the quarterly chart table.

    Steps a beginner can follow:
    1. Keep only true quarter rows (drop empty noise).
    2. Copy FRED's published GDP SAAR growth.
    3. Convert monthly real PCE into quarterly averages, then SAAR growth.
    4. Convert equipment and PNFI levels into SAAR growth.
    5. Keep contribution columns if present (history only; Q2 snapshot is separate).
    """
    q = df_q.dropna(how="all").copy()
    q = q[~q["gdp_growth"].isna() | ~q["real_gdp_level"].isna()].copy()
    # Force a clean quarter-start index (Jan/Apr/Jul/Oct).
    q = q.resample("QS").last()

    out = pd.DataFrame(index=q.index)
    out["gdp_growth"] = q["gdp_growth"]

    # Real PCE is monthly on FRED; average months inside each quarter first.
    pce_q = df_m["real_pce"].dropna().resample("QS").mean()
    out["pce_growth"] = annualized_qoq(pce_q)

    equip = q["nres_equipment"].dropna()
    out["equipment_growth"] = annualized_qoq(equip)

    pnfi = q["pnfi"].dropna()
    out["pnfi_growth"] = annualized_qoq(pnfi)

    deflator = q["gdp_deflator"].dropna()
    out["gdp_deflator_growth"] = annualized_qoq(deflator)

    for col in [
        "pce_contribution",
        "gpdi_contribution",
        "govt_contribution",
        "netex_contribution",
    ]:
        if col in q.columns:
            out[col] = q[col]

    # Charts start around 2019 so the reader sees recent history without noise.
    out = out[out.index >= "2019-01-01"].copy()
    out.index.name = "date"
    return out


def build_monthly_pce(df_m: pd.DataFrame) -> pd.DataFrame:
    """
    Build monthly inflation and income columns used by the PCE charts.

    Price rates are the main product. Income, unemployment, and payrolls
    are kept for context or future prose.
    """
    out = pd.DataFrame(index=df_m.index)
    out["pce_mom"] = mom_pct(df_m["pce_price_index"])
    out["core_pce_mom"] = mom_pct(df_m["core_pce"])
    out["pce_yoy"] = yoy_pct(df_m["pce_price_index"])
    out["core_pce_yoy"] = yoy_pct(df_m["core_pce"])
    out["pce_ann3"] = ann3_pct(df_m["pce_price_index"])
    out["core_pce_ann3"] = ann3_pct(df_m["core_pce"])
    out["real_pce"] = df_m["real_pce"]
    out["real_pce_mom"] = mom_pct(df_m["real_pce"])
    out["real_dpi"] = df_m["real_dpi"]
    out["real_dpi_mom"] = mom_pct(df_m["real_dpi"])
    out["saving_rate"] = df_m["saving_rate"]
    out["unrate"] = df_m["unrate"]
    out["payems"] = df_m["payems"]
    # Jobs change = this month's payrolls minus last month's (thousands).
    out["payroll_change"] = df_m["payems"].diff()

    # First year of y/y is missing by construction; drop incomplete rows.
    out = out.dropna(subset=["pce_yoy", "core_pce_yoy"]).copy()
    out.index.name = "date"
    return out


def build_contributions_shift() -> pd.DataFrame:
    """
    Q1 vs Q2 contribution comparison (percentage points).

    These are not computed from FRED levels. They are typed from the BEA
    release tables (see MANUAL notes in 04_compute_stats.py) so the chart
    matches the print day even if FRED is still on an older vintage.

    Inventories sit *inside* GPDI and are not a separate major row here.
    """
    rows = [
        {"component": "Consumer (PCE)", "q1_pp": 0.37, "q2_pp": 2.12, "sort": 4},
        {"component": "Investment (GPDI)", "q1_pp": 1.35, "q2_pp": 0.53, "sort": 3},
        {"component": "Government", "q1_pp": 0.74, "q2_pp": -0.14, "sort": 2},
        {"component": "Net exports", "q1_pp": -0.37, "q2_pp": -1.01, "sort": 1},
    ]
    df = pd.DataFrame(rows)
    # Positive delta = component helped growth more in Q2 than in Q1.
    df["delta_pp"] = df["q2_pp"] - df["q1_pp"]
    return df.sort_values("sort")


def build_gdp_bridge() -> pd.DataFrame:
    """
    Waterfall steps that sum to real GDP SAAR.

    kind = "flow"  -> signed contribution used in the running total
    kind = "memo"  -> inventory note (already inside GPDI; not double-counted)
    kind = "total" -> final real GDP SAAR bar
    """
    return pd.DataFrame(
        [
            {"step": "Consumer (PCE)", "value": 2.12, "kind": "flow", "sort": 1},
            {"step": "Investment (GPDI)", "value": 0.53, "kind": "flow", "sort": 2},
            {"step": "  Inventories (in GPDI)", "value": -0.67, "kind": "memo", "sort": 3},
            {"step": "Government", "value": -0.14, "kind": "flow", "sort": 4},
            {"step": "Net exports", "value": -1.01, "kind": "flow", "sort": 5},
            {"step": "Real GDP (SAAR)", "value": 1.50, "kind": "total", "sort": 6},
        ]
    )


def build_private_demand() -> pd.DataFrame:
    """
    Q1 vs Q2: real GDP SAAR vs real private final sales SAAR.

    demand_gap_pp = private final sales - real GDP.
    Positive gap means private domestic demand grew faster than the headline.
    """
    df = pd.DataFrame(
        [
            {
                "quarter": "Q1 2026",
                "gdp_growth": 2.1,
                "private_final_sales": 1.7,
            },
            {
                "quarter": "Q2 2026",
                "gdp_growth": 1.5,
                "private_final_sales": 3.9,
            },
        ]
    )
    df["demand_gap_pp"] = df["private_final_sales"] - df["gdp_growth"]
    return df


def build_investment_mix() -> pd.DataFrame:
    """
    Q1 vs Q2 SAAR growth for investment subcomponents.

    Equipment and IP are the AI/capex heart of the story; structures and
    residential show the broader investment mix.
    """
    return pd.DataFrame(
        [
            {"component": "Equipment", "q1": 15.8, "q2": 15.2, "sort": 4},
            {"component": "IP products", "q1": 13.8, "q2": 8.8, "sort": 3},
            {"component": "Structures", "q1": -4.7, "q2": -5.0, "sort": 2},
            {"component": "Residential", "q1": -7.8, "q2": 1.5, "sort": 1},
        ]
    ).sort_values("sort")


def main() -> None:
    """Run all clean builders and write CSV outputs."""
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # --- Load raw downloads from step 01 ---
    df_q = pd.read_csv(RAW_Q, index_col="date", parse_dates=True)
    df_m = pd.read_csv(RAW_M, index_col="date", parse_dates=True)

    quarterly = build_gdp_quarterly(df_q, df_m)
    monthly = build_monthly_pce(df_m)
    contrib_shift = build_contributions_shift()
    bridge = build_gdp_bridge()
    private = build_private_demand()
    invest = build_investment_mix()

    # -----------------------------------------------------------------
    # Release-day overlays
    # On print day, FRED may still show the previous quarter/month.
    # We write the BEA advance numbers into the latest row so charts match
    # the post. Source: BEA GDP advance estimate, 07/30/2026.
    # -----------------------------------------------------------------
    q2 = pd.Timestamp("2026-04-01")
    if q2 not in quarterly.index:
        quarterly.loc[q2] = pd.NA
    quarterly.loc[q2, "gdp_growth"] = 1.5
    quarterly.loc[q2, "pce_growth"] = 3.2
    quarterly.loc[q2, "equipment_growth"] = 15.2
    quarterly.loc[q2, "pnfi_growth"] = 8.4
    quarterly = quarterly.sort_index()
    # Interaction series: equipment growth minus consumer growth (pp).
    quarterly["equip_minus_pce"] = quarterly["equipment_growth"] - quarterly["pce_growth"]

    # June 2026 PCE price rates from the same-day Personal Income release.
    june = pd.Timestamp("2026-06-01")
    if june not in monthly.index:
        if len(monthly):
            monthly.loc[june] = monthly.iloc[-1]
        else:
            monthly.loc[june] = pd.NA
    monthly.loc[june, "pce_mom"] = -0.1
    monthly.loc[june, "core_pce_mom"] = 0.1
    monthly.loc[june, "pce_yoy"] = 3.7
    monthly.loc[june, "core_pce_yoy"] = 3.3
    monthly.loc[june, "saving_rate"] = 2.7
    monthly = monthly.sort_index()

    # --- Write every clean table ---
    outputs = {
        CLEAN_DIR / "gdp_quarterly.csv": quarterly,
        CLEAN_DIR / "monthly_pce.csv": monthly,
        CLEAN_DIR / "contribution_shift.csv": contrib_shift,
        CLEAN_DIR / "gdp_bridge.csv": bridge,
        CLEAN_DIR / "private_demand.csv": private,
        CLEAN_DIR / "investment_mix.csv": invest,
    }
    for path, frame in outputs.items():
        # Time-series tables keep the date index; small chart tables do not.
        if path.name in {"gdp_quarterly.csv", "monthly_pce.csv"}:
            frame.to_csv(path)
        else:
            frame.to_csv(path, index=False)
        print(f"Saved {path}  rows={len(frame)}")

    # Q2-only contribution snapshot kept for older chart code paths.
    q2_only = contrib_shift[["component", "q2_pp", "sort"]].rename(
        columns={"q2_pp": "contribution_pp"}
    )
    q2_path = CLEAN_DIR / "gdp_contributions.csv"
    q2_only.to_csv(q2_path, index=False)
    print(f"Saved {q2_path}  rows={len(q2_only)}")
    print("\nDone. Next: python scripts/04_compute_stats.py")


if __name__ == "__main__":
    main()
