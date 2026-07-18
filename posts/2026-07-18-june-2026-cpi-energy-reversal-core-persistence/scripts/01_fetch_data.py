"""Fetch every FRED series used by the June 2026 CPI post."""

import os
from pathlib import Path

import pandas as pd
from fredapi import Fred

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"

MONTHLY_SERIES = {
    "headline": "CPIAUCSL",
    "core": "CPILFESL",
    "energy": "CPIENGSL",
    "gasoline": "CUSR0000SETB01",
    "shelter": "CUSR0000SAH1",
    "food": "CPIFABSL",
    "core_goods": "CUSR0000SACL1E",
    "median_cpi_yoy": "MEDCPIM159SFRBCLE",
    "trimmed_mean_cpi_yoy": "TRMMEANCPIM159SFRBCLE",
    "sticky_ex_shelter_yoy": "CRESTKCPIXSLTRM159SFRBATL",
    "payems": "PAYEMS",
    "unrate": "UNRATE",
    "fedfunds": "FEDFUNDS",
}

DAILY_SERIES = {
    "dgs2": "DGS2",
    "dgs10": "DGS10",
}

FOMC_SERIES = {
    "fed_target_median": "FEDTARMD",
    "fed_target_longer_run": "FEDTARMDLR",
}


def fetch_group(fred, series_map, start):
    frames = {}
    for name, series_id in series_map.items():
        series = fred.get_series(series_id, observation_start=start)
        frames[name] = series
        latest = series.dropna().index[-1]
        print(f"{name:24s} {series_id:24s} latest {latest.date()}")
    frame = pd.DataFrame(frames).sort_index()
    frame.index.name = "date"
    return frame


def main():
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY not found. Get a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)

    monthly = fetch_group(fred, MONTHLY_SERIES, "2018-01-01")
    monthly.to_csv(RAW_DIR / "fred_monthly.csv")

    daily = fetch_group(fred, DAILY_SERIES, "2024-01-01")
    daily.to_csv(RAW_DIR / "fred_daily.csv")

    fomc = fetch_group(fred, FOMC_SERIES, "2026-01-01")
    fomc.to_csv(RAW_DIR / "fred_fomc.csv")


if __name__ == "__main__":
    main()
