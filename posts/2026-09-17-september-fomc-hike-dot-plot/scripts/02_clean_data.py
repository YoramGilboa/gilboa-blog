"""
02_clean_data.py
----------------
Step 2 of the pipeline: turn raw files into chart-ready tables.

Canonical rate definitions used by this post (and by the charts, which only
plot finished columns):

- Month-over-month percent change: (this month / last month - 1) * 100
- Year-over-year percent change: (this month / the month 12 months earlier - 1) * 100

Do not drop non-adjacent months together. A FRED hole stays a hole.

Run after 01_fetch_data.py, from the post folder:
    python scripts/02_clean_data.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"


def yoy_pct(series: pd.Series) -> pd.Series:
    """Year-over-year percent change for a monthly index."""
    return series.pct_change(12).mul(100)


def mom_pct(series: pd.Series) -> pd.Series:
    """Month-over-month percent change for a monthly index."""
    return series.pct_change(1).mul(100)


def clean_inflation() -> None:
    raw = pd.read_csv(RAW_DIR / "fred_inflation_raw.csv", index_col="date", parse_dates=True)
    out = pd.DataFrame(index=raw.index)
    for col in raw.columns:
        out[f"{col}_yoy"] = yoy_pct(raw[col])
        out[f"{col}_mom"] = mom_pct(raw[col])
        out[col] = raw[col]
    out.to_csv(CLEAN_DIR / "inflation.csv")
    last = out.dropna(how="all").index[-1].date()
    print(f"  inflation.csv: {len(out)} rows, last month {last}")


def clean_labor() -> None:
    raw = pd.read_csv(RAW_DIR / "fred_labor_raw.csv", index_col="date", parse_dates=True)
    out = pd.DataFrame(index=raw.index)
    out["payroll_change_k"] = raw["payems"].diff()
    out["unrate"] = raw["unrate"]
    out["payems"] = raw["payems"]
    out.to_csv(CLEAN_DIR / "labor.csv")
    last = out.dropna(how="all").index[-1].date()
    print(f"  labor.csv: {len(out)} rows, last month {last}")


def clean_rates() -> None:
    raw = pd.read_csv(RAW_DIR / "fred_rates_raw.csv", index_col="date", parse_dates=True)
    out = raw.copy()
    out["target_mid"] = (out["dfedtarl"] + out["dfedtaru"]) / 2.0
    out.to_csv(CLEAN_DIR / "rates_daily.csv")
    monthly = out.resample("ME").last()
    monthly.to_csv(CLEAN_DIR / "rates_monthly.csv")
    print(
        f"  rates_daily.csv: {len(out)} rows; "
        f"rates_monthly.csv: {len(monthly)} rows"
    )


def clean_sep() -> None:
    medians = pd.read_csv(RAW_DIR / "sep_medians_raw.csv")
    medians.to_csv(CLEAN_DIR / "sep_medians.csv", index=False)

    dots = pd.read_csv(RAW_DIR / "sep_dots_2026_raw.csv")
    dots.to_csv(CLEAN_DIR / "sep_dots_2026.csv", index=False)

    market = pd.read_csv(RAW_DIR / "market_path_raw.csv", parse_dates=["date"])
    market.to_csv(CLEAN_DIR / "market_path.csv", index=False)
    print("  sep_medians.csv, sep_dots_2026.csv, market_path.csv")


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    print("Cleaning inflation...")
    clean_inflation()
    print("Cleaning labor...")
    clean_labor()
    print("Cleaning rates...")
    clean_rates()
    print("Cleaning SEP and market tables...")
    clean_sep()


if __name__ == "__main__":
    main()
