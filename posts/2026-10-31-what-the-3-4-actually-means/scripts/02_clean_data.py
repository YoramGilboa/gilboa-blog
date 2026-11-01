"""
02_clean_data.py
================
STEP 2 of the data pipeline.

Reads data/raw and writes data/clean. Rate formulas live here.
Chart cells only plot the columns this script writes.

Definitions
-----------
Month-over-month percent: 100 * (level / prior level - 1).
The prior level is the previous calendar month. A missing month stays
missing. This script does not fill gaps and does not drop rows.

Year-over-year percent: 100 * (level / level twelve months earlier - 1).
That compares a month with the same month a year earlier.

Quarterly annualized percent from an index:
100 * ((level / prior quarter) ** 4 - 1).
Use this only for index levels. Series that FRED already publishes as
an annualized percent change are copied through unchanged.

Employment Cost Index:
The 3-month percent uses the seasonally adjusted index.
The 12-month percent uses the not-seasonally-adjusted index.
That matches the way BLS publishes the two rates.

Dollar changes in income and spending are the difference in seasonally
adjusted annual-rate levels, in billions of dollars. They are not cash
received or spent during the month. Real PCE dollars are billions of
chained 2017 dollars.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"


def percent_change(series: pd.Series, periods: int) -> pd.Series:
    """Percent change versus a prior row. Leaves calendar gaps as NaN."""
    return (series / series.shift(periods) - 1.0) * 100.0


def annualize_quarter(series: pd.Series) -> pd.Series:
    """Compound one quarter's index change to a four-quarter rate."""
    return ((series / series.shift(1)) ** 4 - 1.0) * 100.0


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    quarterly = pd.read_csv(RAW_DIR / "fred_quarterly.csv", index_col="date", parse_dates=True).sort_index()
    quarterly["pce_price_ann"] = annualize_quarter(quarterly["pce_price_index"])
    quarterly["computers_price_ann"] = annualize_quarter(quarterly["computers_price"])
    quarterly["info_price_ann"] = annualize_quarter(quarterly["info_price"])
    # One display group: two published contribution series added together.
    # This is not a new growth rate.
    quarterly["equipment_ip_pp"] = quarterly["equipment_pp"] + quarterly["ip_pp"]
    quarterly.to_csv(CLEAN_DIR / "gdp_quarterly.csv", lineterminator="\n")

    monthly = pd.read_csv(RAW_DIR / "fred_monthly.csv", index_col="date", parse_dates=True).sort_index()
    for source, mom_name, yoy_name in (
        ("pce_price", "pce_mom", "pce_yoy"),
        ("core_price", "core_mom", "core_yoy"),
        ("real_pce", "real_pce_mom", "real_pce_yoy"),
        ("real_dpi", "real_dpi_mom", "real_dpi_yoy"),
        ("income", "income_mom", None),
        ("nominal_pce", "nominal_pce_mom", None),
        ("dpi", "dpi_mom", None),
    ):
        monthly[mom_name] = percent_change(monthly[source], 1)
        if yoy_name:
            monthly[yoy_name] = percent_change(monthly[source], 12)
    monthly["real_pce_dollar"] = monthly["real_pce"].diff()
    monthly["income_dollar"] = monthly["income"].diff()
    monthly["dpi_dollar"] = monthly["dpi"].diff()
    monthly["nominal_pce_dollar"] = monthly["nominal_pce"].diff()
    monthly.to_csv(CLEAN_DIR / "pce_monthly.csv", lineterminator="\n")

    eci = pd.read_csv(RAW_DIR / "fred_eci.csv", index_col="date", parse_dates=True).sort_index()
    eci["comp_qoq"] = percent_change(eci["comp_sa"], 1)
    eci["wages_qoq"] = percent_change(eci["wages_sa"], 1)
    eci["benefits_qoq"] = percent_change(eci["benefits_sa"], 1)
    eci["comp_yoy"] = percent_change(eci["comp_nsa"], 4)
    eci["wages_yoy"] = percent_change(eci["wages_nsa"], 4)
    eci["benefits_yoy"] = percent_change(eci["benefits_nsa"], 4)
    # PCE year rate in the last month of the same quarter.
    # A quarter dated July 1 ends in September, two months later.
    quarter_end = eci.index + pd.DateOffset(months=2)
    eci["pce_yoy"] = quarter_end.map(monthly["pce_yoy"])
    eci["wage_minus_pce"] = eci["wages_yoy"] - eci["pce_yoy"]
    eci.to_csv(CLEAN_DIR / "eci_quarterly.csv", lineterminator="\n")

    payems = pd.read_csv(RAW_DIR / "fred_payems.csv", index_col="date", parse_dates=True).sort_index()
    payems["payems_change"] = payems["payems"].diff()
    payems.to_csv(CLEAN_DIR / "labor_payems.csv", lineterminator="\n")

    claims = pd.read_csv(RAW_DIR / "fred_claims.csv", index_col="date", parse_dates=True).sort_index()
    claims.to_csv(CLEAN_DIR / "labor_claims.csv", lineterminator="\n")
    print("Wrote clean CSVs.")


if __name__ == "__main__":
    main()
