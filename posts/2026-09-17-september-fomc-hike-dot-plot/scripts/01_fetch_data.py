"""
01_fetch_data.py
----------------
Step 1 of the pipeline (01 -> 02 -> 04).

Downloads the FRED series this post uses and writes curated official SEP
tables plus a market-path snapshot. Later scripts read only from data/raw/.

Set the FRED API key before running:
    PowerShell: $env:FRED_API_KEY="your_key_here"

Run from the post folder:
    python scripts/01_fetch_data.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from fredapi import Fred

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"

# Friendly name -> FRED series ID.
INFLATION_SERIES = {
    "headline_cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "headline_pce": "PCEPI",
    "core_pce": "PCEPILFE",
}
LABOR_SERIES = {
    "payems": "PAYEMS",
    "unrate": "UNRATE",
}
RATES_SERIES = {
    "fedfunds": "FEDFUNDS",
    "dff": "DFF",
    "dfedtarl": "DFEDTARL",
    "dfedtaru": "DFEDTARU",
    "dgs2": "DGS2",
    "dgs10": "DGS10",
}

START = "2018-01-01"


def fetch_group(fred: Fred, series_map: dict[str, str], start: str) -> pd.DataFrame:
    """Download one group of series and align them by date."""
    frames = {}
    for name, series_id in series_map.items():
        print(f"  {name:14s} <- {series_id}")
        series = fred.get_series(series_id, observation_start=start)
        if series.empty:
            raise RuntimeError(f"FRED series returned no observations: {series_id}")
        frames[name] = series
    frame = pd.DataFrame(frames)
    frame.index.name = "date"
    return frame


def write_sep_tables() -> None:
    """Write transcribed official SEP tables with source URLs in sources.json.

    These numbers are not FRED series. They come from the Federal Reserve's
    September 16 and June 17, 2026 projection materials.
    """
    medians = pd.DataFrame(
        [
            {"meeting": "June 2026", "horizon": "2026", "funds": 3.8, "pce": 3.6, "core_pce": 3.3, "gdp": 2.2, "unrate": 4.3, "unrate_longer": 4.2, "funds_longer": 3.1},
            {"meeting": "June 2026", "horizon": "2027", "funds": 3.6, "pce": 2.3, "core_pce": 2.5, "gdp": 2.3, "unrate": 4.3, "unrate_longer": 4.2, "funds_longer": 3.1},
            {"meeting": "June 2026", "horizon": "2028", "funds": 3.4, "pce": 2.0, "core_pce": 2.1, "gdp": 2.2, "unrate": 4.2, "unrate_longer": 4.2, "funds_longer": 3.1},
            {"meeting": "June 2026", "horizon": "Longer run", "funds": 3.1, "pce": 2.0, "core_pce": None, "gdp": 2.0, "unrate": 4.2, "unrate_longer": 4.2, "funds_longer": 3.1},
            {"meeting": "September 2026", "horizon": "2026", "funds": 4.1, "pce": 3.7, "core_pce": 3.4, "gdp": 2.3, "unrate": 4.1, "unrate_longer": 4.2, "funds_longer": 3.2},
            {"meeting": "September 2026", "horizon": "2027", "funds": 4.1, "pce": 2.3, "core_pce": 2.5, "gdp": 2.4, "unrate": 4.1, "unrate_longer": 4.2, "funds_longer": 3.2},
            {"meeting": "September 2026", "horizon": "2028", "funds": 3.9, "pce": 2.1, "core_pce": 2.2, "gdp": 2.2, "unrate": 4.1, "unrate_longer": 4.2, "funds_longer": 3.2},
            {"meeting": "September 2026", "horizon": "2029", "funds": 3.6, "pce": 2.0, "core_pce": 2.0, "gdp": 2.1, "unrate": 4.1, "unrate_longer": 4.2, "funds_longer": 3.2},
            {"meeting": "September 2026", "horizon": "Longer run", "funds": 3.2, "pce": 2.0, "core_pce": None, "gdp": 2.0, "unrate": 4.2, "unrate_longer": 4.2, "funds_longer": 3.2},
        ]
    )
    medians.to_csv(RAW_DIR / "sep_medians_raw.csv", index=False)

    # Individual end-2026 dots, rounded to the nearest 1/8 as in SEP Figure 2.
    june_dots = (
        [3.375] * 1
        + [3.625] * 8
        + [3.875] * 3
        + [4.125] * 5
        + [4.375] * 1
    )
    sept_dots = (
        [3.875] * 2
        + [4.125] * 12
        + [4.375] * 4
    )
    dots_rows = [{"meeting": "June 2026", "dot": value} for value in june_dots]
    dots_rows.extend({"meeting": "September 2026", "dot": value} for value in sept_dots)
    pd.DataFrame(dots_rows).to_csv(RAW_DIR / "sep_dots_2026_raw.csv", index=False)

    # Futures-implied expected funds rate around remaining 2026 meetings.
    # Expected value = current midpoint + probability * 0.25.
    current_mid = 3.875
    oct_prob = 0.50
    dec_prob = 0.79
    market = pd.DataFrame(
        [
            {"date": "2026-09-16", "label": "After Sept hike", "implied_rate": current_mid, "kind": "realized_mid"},
            {"date": "2026-10-28", "label": "Oct FOMC (expected)", "implied_rate": round(current_mid + oct_prob * 0.25, 3), "kind": "futures"},
            {"date": "2026-12-09", "label": "Dec FOMC (expected)", "implied_rate": round(current_mid + dec_prob * 0.25, 3), "kind": "futures"},
            {"date": "2026-12-31", "label": "SEP median end-2026", "implied_rate": 4.1, "kind": "sep"},
            {"date": "2027-12-31", "label": "SEP median end-2027", "implied_rate": 4.1, "kind": "sep"},
            {"date": "2028-12-31", "label": "SEP median end-2028", "implied_rate": 3.9, "kind": "sep"},
        ]
    )
    market.to_csv(RAW_DIR / "market_path_raw.csv", index=False)

    sources = {
        "fomc_statement": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
        "implementation_note": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a1.htm",
        "september_sep": "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm",
        "june_sep": "https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20260617.htm",
        "fomc_calendar": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "market_notes": (
            "October ~50% hike and December ~79% at least one more hike from "
            "contemporaneous reconstructions of 30-day fed funds futures after "
            "the 9/16/2026 decision. CME FedWatch is not a stable public CSV."
        ),
        "used_for": {
            "sep_medians_raw.csv": "Median SEP paths, June vs September",
            "sep_dots_2026_raw.csv": "Individual end-2026 dots",
            "market_path_raw.csv": "Futures-implied expected path vs SEP medians",
        },
    }
    (RAW_DIR / "sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    print("  wrote curated SEP tables and market snapshot")


def main() -> None:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY not found. Set it as an environment variable before running."
        )
    fred = Fred(api_key=api_key)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching inflation series...")
    infl = fetch_group(fred, INFLATION_SERIES, START)
    infl.to_csv(RAW_DIR / "fred_inflation_raw.csv")
    print(f"  saved {len(infl)} rows, last {infl.dropna(how='all').index[-1].date()}\n")

    print("Fetching labor series...")
    labor = fetch_group(fred, LABOR_SERIES, START)
    labor.to_csv(RAW_DIR / "fred_labor_raw.csv")
    print(f"  saved {len(labor)} rows, last {labor.dropna(how='all').index[-1].date()}\n")

    print("Fetching rates series...")
    rates = fetch_group(fred, RATES_SERIES, START)
    rates.to_csv(RAW_DIR / "fred_rates_raw.csv")
    print(f"  saved {len(rates)} rows, last {rates.dropna(how='all').index[-1].date()}\n")

    write_sep_tables()


if __name__ == "__main__":
    main()
