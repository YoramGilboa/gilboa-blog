"""
02_clean_data.py
================
STEP 2 of the data pipeline.

What this script does
---------------------
Turns raw FRED levels into the rate columns the charts plot. Charts must
not recompute these formulas.

Canonical rate definitions
--------------------------
Month-over-month (m/m) percent, from a dollar or index level:
    (this_month / previous_month - 1) * 100
    Example: an index move from 100.0 to 100.2 is +0.2%.
    A missing previous month stays missing. Nothing is interpolated.

Year-over-year (y/y) percent:
    (this_month / twelve_months_ago - 1) * 100
    PCE price indexes on FRED are seasonally adjusted. BEA's published
    12-month PCE rates use that same index, so both m/m and y/y come
    from the chain-type price indexes. This is not the CPI convention,
    where y/y uses a not-seasonally-adjusted index.

Three-month annualized percent:
    ((this_month / three_months_ago) ** 4 - 1) * 100
    Four quarters of the three-month change. It is a momentum reading,
    not a forecast, and it is not the annual-update revision.

Food, energy, and core month changes are each index's own change.
They do not add up to the headline change, because these are chain indexes.

The saving rate (PSAVERT), the Michigan expectation, and the quarterly
GDP rates are already percents. This script does not convert them again.

Real PCE and real disposable income are indexed to January 2024 = 100.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"

AUGUST = pd.Timestamp("2026-08-01")
INDEX_BASE = pd.Timestamp("2024-01-01")
Q2 = pd.Timestamp("2026-04-01")


def mom(series: pd.Series) -> pd.Series:
    """Month-over-month percent change. See the module docstring."""
    return series.pct_change(fill_method=None) * 100


def yoy(series: pd.Series) -> pd.Series:
    """Year-over-year percent change. See the module docstring."""
    return series.pct_change(12, fill_method=None) * 100


def ann3(series: pd.Series) -> pd.Series:
    """Three-month compounded annualized percent. See the module docstring."""
    return ((series / series.shift(3)) ** 4 - 1) * 100


def index_to_base(series: pd.Series, base_date: pd.Timestamp) -> pd.Series:
    """Scale a level so the base month equals 100. Fail if the base is missing."""
    if base_date not in series.index or pd.isna(series.loc[base_date]):
        raise RuntimeError(f"Index base {base_date.date()} is missing.")
    return 100 * series / series.loc[base_date]


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    # The committed snapshot only. data/raw/refresh/ is not an input.
    monthly = pd.read_csv(RAW_DIR / "fred_pce_monthly.csv", index_col="date", parse_dates=True)
    monthly = monthly.sort_index()
    quarterly = pd.read_csv(RAW_DIR / "fred_gdp_quarterly.csv", index_col="date", parse_dates=True)
    quarterly = quarterly.sort_index()
    manual = json.loads((RAW_DIR / "manual_priors.json").read_text(encoding="utf-8"))

    if AUGUST not in monthly.index:
        raise RuntimeError("August 2026 is missing. Do not fill it.")
    if INDEX_BASE not in monthly.index:
        raise RuntimeError("January 2024 is missing, so the spending index has no base.")

    out = pd.DataFrame(index=monthly.index)
    out.index.name = "date"
    for column in (
        "pce_price",
        "core_price",
        "food_price",
        "energy_price",
        "real_pce",
        "real_dpi",
        "nominal_pce",
        "personal_income",
        "disposable_pi",
    ):
        out[column] = monthly[column]
        out[f"{column}_mom"] = mom(monthly[column])
        out[f"{column}_yoy"] = yoy(monthly[column])

    out["saving_rate"] = monthly["saving_rate"]
    out["mich"] = monthly["mich"]
    out["core_3m"] = ann3(monthly["core_price"])
    out["real_pce_index"] = index_to_base(monthly["real_pce"], INDEX_BASE)
    out["real_dpi_index"] = index_to_base(monthly["real_dpi"], INDEX_BASE)
    out.to_csv(CLEAN_DIR / "pce_monthly.csv")

    prices = out.loc[:, ["food_price_mom", "energy_price_mom", "core_price_mom", "pce_price_mom"]].copy()
    prices.to_csv(CLEAN_DIR / "pce_price_monthly.csv")

    indexed = out.loc[:, ["real_pce_index", "real_dpi_index"]].copy()
    indexed.to_csv(CLEAN_DIR / "real_indexes.csv")

    pace = out.loc[:, ["core_price_yoy", "core_3m"]].copy()
    pace.to_csv(CLEAN_DIR / "core_pace.csv")

    revision = pd.DataFrame(
        [
            {"measure": "Real GDP", "second": manual["q2_gdp_second"], "third": None},
            {
                "measure": "Private domestic final sales",
                "second": manual["q2_pdfp_second"],
                "third": None,
            },
            {"measure": "Real GDI", "second": manual["q2_gdi_second"], "third": manual["q2_gdi_third"]},
        ]
    )
    # Third-estimate GDP and private final sales come from the latest FRED vintage.
    # Real GDI is not in the FRED download. It stays the transcribed BEA figure.
    if Q2 not in quarterly.index:
        raise RuntimeError("2026 Q2 is missing from the quarterly file.")
    revision.loc[revision["measure"] == "Real GDP", "third"] = float(quarterly.loc[Q2, "gdp_saar"])
    revision.loc[revision["measure"] == "Private domestic final sales", "third"] = float(
        quarterly.loc[Q2, "pdfp_saar"]
    )
    revision.to_csv(CLEAN_DIR / "q2_revision.csv", index=False)
    quarterly.to_csv(CLEAN_DIR / "gdp_quarterly.csv")

    print(f"Clean monthly rows: {len(out):,}  last={out.index.max().date()}")
    print(f"August headline m/m={out.loc[AUGUST, 'pce_price_mom']:.3f}  y/y={out.loc[AUGUST, 'pce_price_yoy']:.3f}")
    print(f"August core m/m={out.loc[AUGUST, 'core_price_mom']:.3f}  y/y={out.loc[AUGUST, 'core_price_yoy']:.3f}")


if __name__ == "__main__":
    main()
