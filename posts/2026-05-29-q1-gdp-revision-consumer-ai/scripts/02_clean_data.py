"""
02_clean_data.py
----------------
Transform raw FRED data into chart-ready CSVs.

Outputs:
    data/clean/gdp_quarterly.csv   - GDP growth, PCE growth, equipment growth, deflator
    data/clean/monthly_indicators.csv - Core PCE YoY, unemployment, payrolls
    data/clean/expansion_indexed.csv  - Real GDP indexed to 100 at cycle troughs

Run from the post folder after 01_fetch_data.py:
    python scripts/02_clean_data.py
"""

import os

import numpy as np
import pandas as pd


RAW_Q = "data/raw/fred_quarterly.csv"
RAW_M = "data/raw/fred_monthly.csv"
CLEAN_DIR = "data/clean"


def annualized_qoq(series):
    """Compute quarter-over-quarter annualized percent change."""
    return ((series / series.shift(1)) ** 4 - 1) * 100


def quarterly_avg(monthly_series):
    """Resample a monthly series to quarterly averages."""
    return monthly_series.resample("QS").mean()


def build_gdp_quarterly(df_q):
    """Build quarterly GDP/investment/PCE growth table."""
    # GDP growth comes directly from FRED (already annualized SAAR)
    gdp_growth = df_q["gdp_growth"].dropna()

    # Equipment investment: compute annualized QoQ growth from levels
    equip_growth = annualized_qoq(df_q["nres_equipment"].dropna())
    equip_growth.name = "equipment_growth"

    # PNFI growth
    pnfi_growth = annualized_qoq(df_q["pnfi"].dropna())
    pnfi_growth.name = "pnfi_growth"

    # PCE components: real_pce, pce_durable, pce_nondurable are monthly.
    # Resample to quarterly averages, then compute annualized growth.
    pce_monthly = df_q[["real_pce", "pce_durable", "pce_nondurable"]].dropna()
    pce_q = pce_monthly.resample("QS").mean()
    pce_growth = annualized_qoq(pce_q["real_pce"])
    pce_growth.name = "pce_growth"
    pce_dur_growth = annualized_qoq(pce_q["pce_durable"])
    pce_dur_growth.name = "pce_durable_growth"
    pce_nondur_growth = annualized_qoq(pce_q["pce_nondurable"])
    pce_nondur_growth.name = "pce_nondurable_growth"

    # PCE services is already quarterly
    pce_svc_growth = annualized_qoq(df_q["pce_services"].dropna())
    pce_svc_growth.name = "pce_services_growth"

    # GDP deflator: annualized QoQ from index level
    deflator_growth = annualized_qoq(df_q["gdp_deflator"].dropna())
    deflator_growth.name = "gdp_deflator_growth"

    # Combine all quarterly series
    result = pd.concat([
        gdp_growth,
        pce_growth,
        pce_dur_growth,
        pce_nondur_growth,
        pce_svc_growth,
        equip_growth,
        pnfi_growth,
        deflator_growth,
    ], axis=1)

    # Filter to 2019-Q1 onward for charting (enough pre-COVID context)
    result = result[result.index >= "2019-01-01"]
    return result


def build_monthly_indicators(df_m):
    """Build monthly inflation and labor market indicators."""
    # PCE price indices: compute year-over-year percent change
    pce_yoy = df_m["pce_price_index"].pct_change(12) * 100
    pce_yoy.name = "pce_yoy"

    core_pce_yoy = df_m["core_pce"].pct_change(12) * 100
    core_pce_yoy.name = "core_pce_yoy"

    # Payroll month-over-month change (thousands)
    payroll_chg = df_m["payems"].diff()
    payroll_chg.name = "payroll_change"

    # 3-month moving average of payroll changes
    payroll_3m = payroll_chg.rolling(3).mean()
    payroll_3m.name = "payroll_3m_avg"

    result = pd.concat([
        pce_yoy,
        core_pce_yoy,
        df_m["unrate"],
        df_m["payems"],
        payroll_chg,
        payroll_3m,
        df_m["consumer_sentiment"],
    ], axis=1)

    # Drop rows where YoY cannot be computed (first 12 months)
    result = result.dropna(subset=["pce_yoy", "core_pce_yoy"])
    return result


def build_expansion_indexed(df_q):
    """Index real GDP to 100 at each expansion trough for cross-cycle comparison."""
    gdp = df_q["real_gdp_level"].dropna()

    # Trough quarters for three recent expansions
    troughs = {
        "dotcom":  "2001-10-01",   # Q4 2001 trough
        "gfc":     "2009-04-01",   # Q2 2009 trough
        "covid":   "2020-04-01",   # Q2 2020 trough
    }

    max_quarters = 24  # Track 6 years from each trough
    records = []

    for name, trough_date in troughs.items():
        trough_ts = pd.Timestamp(trough_date)
        if trough_ts not in gdp.index:
            print(f"  WARNING: trough {trough_date} not in GDP data, skipping {name}")
            continue

        trough_val = gdp.loc[trough_ts]
        # Get data from trough onward
        expansion = gdp[gdp.index >= trough_ts].head(max_quarters + 1)

        for i, (date, val) in enumerate(expansion.items()):
            records.append({
                "expansion": name,
                "quarters_since_trough": i,
                "date": date,
                "gdp_indexed": (val / trough_val) * 100,
            })

    result = pd.DataFrame(records)
    return result


def main():
    df_q = pd.read_csv(RAW_Q, index_col="date", parse_dates=True)
    df_m = pd.read_csv(RAW_M, index_col="date", parse_dates=True)

    print(f"Loaded {len(df_q)} quarterly rows and {len(df_m)} monthly rows\n")

    os.makedirs(CLEAN_DIR, exist_ok=True)

    # 1. GDP quarterly
    gdp_q = build_gdp_quarterly(df_q)
    gdp_q.to_csv(f"{CLEAN_DIR}/gdp_quarterly.csv")
    print(f"Saved {len(gdp_q)} rows to gdp_quarterly.csv")
    print("  Q1 2026 snapshot:")
    q1 = gdp_q.loc["2026-01-01"]
    for col in gdp_q.columns:
        if not np.isnan(q1[col]):
            print(f"    {col:25s}: {q1[col]:+.1f}%")

    # 2. Monthly indicators
    monthly = build_monthly_indicators(df_m)
    monthly.to_csv(f"{CLEAN_DIR}/monthly_indicators.csv")
    print(f"\nSaved {len(monthly)} rows to monthly_indicators.csv")
    latest = monthly.iloc[-1]
    print(f"  Latest month: {monthly.index[-1].strftime('%B %Y')}")
    print(f"    Core PCE YoY:  {latest['core_pce_yoy']:.1f}%")
    print(f"    Unemployment:  {latest['unrate']:.1f}%")
    print(f"    Payroll chg:   {latest['payroll_change']:+.0f}K")

    # 3. Expansion comparison
    expansion = build_expansion_indexed(df_q)
    expansion.to_csv(f"{CLEAN_DIR}/expansion_indexed.csv", index=False)
    print(f"\nSaved {len(expansion)} rows to expansion_indexed.csv")
    for name in ["dotcom", "gfc", "covid"]:
        subset = expansion[expansion["expansion"] == name]
        if len(subset) > 0:
            latest_idx = subset["gdp_indexed"].iloc[-1]
            print(f"  {name}: {len(subset)} quarters, latest indexed = {latest_idx:.1f}")


if __name__ == "__main__":
    main()
