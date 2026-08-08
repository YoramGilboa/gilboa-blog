"""Fetch official labor-market data for the July 2026 payrolls post."""

from __future__ import annotations

import json
import os
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from fredapi import Fred


POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

FRED_SERIES = {
    "PAYEMS": "All employees, total nonfarm",
    "USPRIV": "All employees, total private",
    "ADPMNUSNERSA": "ADP total private payroll employment",
    "ADPMINDEDHLTNERSA": "ADP education and health services employment",
    "USEHS": "BLS private education and health services employment",
    "CES6561000001": "BLS private educational services employment",
    "CES6562000001": "BLS health care and social assistance employment",
    "CES6562000101": "BLS health care employment",
    "CES6562400001": "BLS social assistance employment",
    "UNRATE": "Unemployment rate",
    "CIVPART": "Labor force participation rate",
    "ICSA": "Initial unemployment claims",
    "CES0500000003": "Average hourly earnings, total private",
}

ADP_ARCHIVES = {
    "adp_ner": "https://adpemploymentreport.com/artifacts/us_ner/20260805/ADP_NER_history.zip",
    "adp_pay": "https://payinsights.adp.com/artifacts/us_wage/20260805/ADP_PAY_history.zip",
}


def fetch_fred() -> None:
    """Download validated FRED observations as one tidy CSV."""
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY is required. Register at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    fred = Fred(api_key=api_key)
    frames = []
    for series_id, description in FRED_SERIES.items():
        info = fred.get_series_info(series_id)
        values = fred.get_series(series_id).rename("value").dropna()
        frame = values.rename_axis("date").reset_index()
        frame["series_id"] = series_id
        frame["description"] = description
        frame["official_title"] = info["title"]
        frame["frequency"] = info["frequency"]
        frame["units"] = info["units"]
        frames.append(frame)

    output = pd.concat(frames, ignore_index=True)
    output.to_csv(RAW_DIR / "fred_series.csv", index=False)


def fetch_adp_archives() -> None:
    """Download and unpack the official ADP employment and pay archives."""
    for archive_name, url in ADP_ARCHIVES.items():
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        destination = RAW_DIR / archive_name
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            archive.extractall(destination)


def write_sources() -> None:
    """Record the source contract used by the downstream pipeline."""
    sources = {
        "retrieved_on": "2026-08-08",
        "fred": {
            "url": "https://fred.stlouisfed.org/",
            "series": FRED_SERIES,
        },
        "adp_national_employment_report": {
            "url": "https://adpemploymentreport.com/",
            "archive": ADP_ARCHIVES["adp_ner"],
        },
        "adp_pay_insights": {
            "url": "https://payinsights.adp.com/",
            "archive": ADP_ARCHIVES["adp_pay"],
        },
        "bls_employment_situation": {
            "url": "https://www.bls.gov/news.release/empsit.nr0.htm"
        },
        "fomc_statement": {
            "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm"
        },
    }
    (RAW_DIR / "sources.json").write_text(
        json.dumps(sources, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    fetch_fred()
    fetch_adp_archives()
    write_sources()
    print(f"Fetched {len(FRED_SERIES)} FRED series and {len(ADP_ARCHIVES)} ADP archives.")


if __name__ == "__main__":
    main()