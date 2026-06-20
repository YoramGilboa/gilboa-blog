"""
02_clean_data.py
----------------
Step 2 of the pipeline: turn raw FRED CSVs into clean, post-ready tables.

Each function reads one raw file, computes the derived series the post needs
(year-over-year change, month-over-month change, target-range midpoint), and
writes a tidy table to data/clean/.

Run after 01_fetch_data.py:
    python scripts/02_clean_data.py
"""

import os

import pandas as pd

RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"


def yoy_pct(series):
    """Year-over-year percent change for a monthly series."""
    return series.pct_change(12).mul(100)


def mom_pct(series):
    """Month-over-month percent change for a monthly series."""
    return series.pct_change(1).mul(100)


def clean_inflation():
    """Compute YoY and MoM for headline CPI, core CPI, energy CPI, PCE, core PCE."""
    df = pd.read_csv(f"{RAW_DIR}/fred_inflation_raw.csv",
                     index_col="date", parse_dates=True)
    out = pd.DataFrame(index=df.index)
    for col in df.columns:
        out[f"{col}_yoy"] = yoy_pct(df[col])
        out[f"{col}_mom"] = mom_pct(df[col])
    out = out.dropna(how="all")
    out.to_csv(f"{CLEAN_DIR}/inflation.csv")
    print(f"  inflation.csv: {len(out)} rows, last month {out.index[-1].date()}")
    return out


def clean_labor():
    """Compute monthly payroll change and keep unemployment + participation levels."""
    df = pd.read_csv(f"{RAW_DIR}/fred_labor_raw.csv",
                     index_col="date", parse_dates=True)
    out = pd.DataFrame(index=df.index)
    out["payroll_change_k"] = df["payems"].diff()   # thousands per month
    out["unrate"] = df["unrate"]
    out["civpart"] = df["civpart"]
    out = out.dropna(how="all")
    out.to_csv(f"{CLEAN_DIR}/labor.csv")
    print(f"  labor.csv: {len(out)} rows, last month {out.index[-1].date()}")
    return out


def clean_claims():
    """Resample weekly initial claims into a monthly average."""
    df = pd.read_csv(f"{RAW_DIR}/fred_claims_raw.csv",
                     index_col="date", parse_dates=True)
    out = df["icsa"].resample("ME").mean().to_frame("icsa_monthly_avg").dropna()
    out.to_csv(f"{CLEAN_DIR}/claims.csv")
    print(f"  claims.csv: {len(out)} rows, last month {out.index[-1].date()}")
    return out


def clean_rates():
    """Build a daily rates table with target-range midpoint and Treasury yields."""
    df = pd.read_csv(f"{RAW_DIR}/fred_rates_raw.csv",
                     index_col="date", parse_dates=True)
    df["target_mid"] = (df["dfedtarl"] + df["dfedtaru"]) / 2.0
    keep = ["fedfunds", "target_mid", "dgs1", "dgs2", "dgs10"]
    out = df[keep].copy()
    out.to_csv(f"{CLEAN_DIR}/rates_daily.csv")
    # Also a monthly version for the long line chart
    monthly = out.resample("ME").last().dropna(how="all")
    monthly.to_csv(f"{CLEAN_DIR}/rates_monthly.csv")
    print(f"  rates_daily.csv: {len(out)} rows; rates_monthly.csv: {len(monthly)} rows")
    return out


def main():
    os.makedirs(CLEAN_DIR, exist_ok=True)
    print("Cleaning inflation series...")
    clean_inflation()
    print("Cleaning labor series...")
    clean_labor()
    print("Cleaning claims series...")
    clean_claims()
    print("Cleaning rates series...")
    clean_rates()


if __name__ == "__main__":
    main()
