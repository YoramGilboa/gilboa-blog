"""
download_fred_data.py
Downloads all FRED series used by the May 2026 jobs report post into
data/{SERIES_ID}.csv. The .qmd loads these CSVs as a cache when the
FRED_API_KEY environment variable is not available (e.g. on the GitHub
Actions runner with no secret configured).

Usage (from the post directory):
    python scripts/download_fred_data.py

Requires: FRED_API_KEY environment variable. Falls back to the public
FRED graph CSV endpoint when no key is set.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests


SERIES_IDS = [
    # Headline
    "PAYEMS", "UNRATE", "CES0500000003", "CE16OV",
    # Labor force detail
    "CIVPART", "EMRATIO",
    # JOLTS
    "JTSJOL", "JTSQUR",
    # Claims
    "ICSA",
    # Inflation and wage anchors
    "CPIAUCSL", "OPHNFB", "ULCNFB",
    # Recession indicator
    "USREC",
    # Private payrolls and ADP
    "USPRIV", "ADPMNUSNERSA",
    # Sector employment (using public-endpoint-friendly aliases)
    "USCONS", "MANEMP", "USTPU", "USPBS", "USEHS",
    "CES6562000001", "USLAH", "USGOVT", "USINFO",
    # State unemployment
    "CAUR", "TXUR", "NYUR", "FLUR",
]


def fetch_via_fredapi(series_id: str, api_key: str) -> pd.Series:
    from fredapi import Fred
    fred = Fred(api_key=api_key)
    s = fred.get_series(series_id)
    s.index = pd.to_datetime(s.index)
    s.index.name = "observation_date"
    s.name = series_id
    return s.astype(float).sort_index()


def fetch_via_csv(series_id: str) -> pd.Series:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(r.text))
    date_col = "observation_date" if "observation_date" in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    val_col = [c for c in df.columns if c != date_col][0]
    s = df.set_index(date_col)[val_col]
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    s.name = series_id
    return s


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("FRED_API_KEY", "").strip()
    using = "fredapi" if api_key else "public CSV endpoint"
    print(f"Downloading {len(SERIES_IDS)} series via {using} -> {out_dir}")

    for sid in SERIES_IDS:
        out_path = out_dir / f"{sid}.csv"
        try:
            if api_key:
                s = fetch_via_fredapi(sid, api_key)
            else:
                s = fetch_via_csv(sid)
            s.to_frame().reset_index().to_csv(out_path, index=False)
            print(f"  {sid}: {len(s)} rows -> {out_path.name}")
        except Exception as exc:
            print(f"  {sid}: FAILED ({exc})", file=sys.stderr)
        time.sleep(0.5)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
