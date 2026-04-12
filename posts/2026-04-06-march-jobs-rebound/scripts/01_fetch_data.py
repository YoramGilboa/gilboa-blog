"""
01_fetch_data.py
Fetches nonfarm payroll, unemployment, and labor force data from the BLS public API.
Outputs raw JSON to data/raw/.

BLS series used:
  CES0000000001  - Total nonfarm payroll employment (seasonally adjusted)
  LNS14000000    - Unemployment rate (seasonally adjusted)
  LNS11300000    - Civilian labor force participation rate (SA)
  LNS12300000    - Employment-population ratio (SA)
  LNS13000000    - Number of unemployed persons (SA, thousands)

Run from the post folder:
    python scripts/01_fetch_data.py
"""

import json
import os
import requests

# ── Config ────────────────────────────────────────────────────────────────────

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

SERIES = {
    "payrolls":            "CES0000000001",
    "unemployment_rate":   "LNS14000000",
    "lfpr":                "LNS11300000",
    "emp_pop_ratio":       "LNS12300000",
    "unemployed_persons":  "LNS13000000",
}

START_YEAR = "2024"
END_YEAR   = "2026"

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_series(series_ids: list[str], start: str, end: str) -> dict:
    payload = {
        "seriesid": series_ids,
        "startyear": start,
        "endyear": end,
        "catalog": False,
        "calculations": False,
    }
    resp = requests.post(BLS_API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main():
    print("Fetching BLS data...")
    data = fetch_series(list(SERIES.values()), START_YEAR, END_YEAR)

    if data.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API error: {data.get('message', data)}")

    for series_obj in data["Results"]["series"]:
        sid = series_obj["seriesID"]
        name = next((k for k, v in SERIES.items() if v == sid), sid)
        out_path = os.path.join(OUT_DIR, f"{name}.json")
        with open(out_path, "w") as f:
            json.dump(series_obj, f, indent=2)
        print(f"  Saved {name} → {out_path} ({len(series_obj['data'])} observations)")

    print("Done.")


if __name__ == "__main__":
    main()
