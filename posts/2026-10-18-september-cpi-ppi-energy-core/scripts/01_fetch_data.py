"""
01_fetch_data.py
================
STEP 1 of the data pipeline.

What this script does
---------------------
The default command reproduces the analysis from the committed snapshots.
It checks each raw CSV against snapshot_sha256 in data/raw/sources.json and
exits. A missing, malformed, or mismatched hash is an error. The script does
not create a new baseline and does not download.

    python scripts/01_fetch_data.py

An optional historical refetch is separate from reproduction:

    python scripts/01_fetch_data.py --refresh

--refresh requires FRED_API_KEY. It writes data/raw/refresh/ only.
CPI series use realtime_start and realtime_end of 2026-10-14.
PPI series use 2026-10-15. The funds-rate range uses 2026-10-17.
Those files do not replace the committed snapshots. An observation end
alone does not freeze later revisions.

Pipeline order
--------------
    python scripts/01_fetch_data.py
    python scripts/02_clean_data.py
    python scripts/04_compute_stats.py

Friendly name -> FRED id. Later scripts use the friendly names.

CPI: CPIAUCSL, CPIAUCNS, CPILFESL, CPILFENS, CPIENGSL, CPIENGNS,
CUSR0000SETB01, CUUR0000SETB01, CPIUFDSL, CPIUFDNS, CUSR0000SAH1,
CUUR0000SAH1, CUSR0000SASLE, CUUR0000SASLE, CUSR0000SACL1E.
PPI: PPIFIS, PPIFID, PPIDGS, PPIDSS, PPIDES, PPIDFS, WPSFD413,
WPSFD49116, WPUFD49116.
Funds: DFEDTARU, DFEDTARL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
REFRESH_DIR = RAW_DIR / "refresh"

CPI_VINTAGE = "2026-10-14"
PPI_VINTAGE = "2026-10-15"
FUNDS_VINTAGE = "2026-10-17"
OBS_START = "2010-01-01"
MONTH_END = "2026-09-01"
FUNDS_END = "2026-10-17"

CPI_ARCHIVE = "https://www.bls.gov/news.release/archives/cpi_10142026.htm"
PPI_ARCHIVE = "https://www.bls.gov/news.release/archives/ppi_10152026.htm"

CPI_SERIES = {
    "headline_sa": "CPIAUCSL",
    "headline_nsa": "CPIAUCNS",
    "core_sa": "CPILFESL",
    "core_nsa": "CPILFENS",
    "energy_sa": "CPIENGSL",
    "energy_nsa": "CPIENGNS",
    "gasoline_sa": "CUSR0000SETB01",
    "gasoline_nsa": "CUUR0000SETB01",
    "food_sa": "CPIUFDSL",
    "food_nsa": "CPIUFDNS",
    "shelter_sa": "CUSR0000SAH1",
    "shelter_nsa": "CUUR0000SAH1",
    "services_sa": "CUSR0000SASLE",
    "services_nsa": "CUUR0000SASLE",
    "core_goods_sa": "CUSR0000SACL1E",
}
PPI_SERIES = {
    "ppi_fd_sa": "PPIFIS",
    "ppi_fd_nsa": "PPIFID",
    "ppi_goods_sa": "PPIDGS",
    "ppi_services_sa": "PPIDSS",
    "ppi_energy_sa": "PPIDES",
    "ppi_foods_sa": "PPIDFS",
    "ppi_core_goods_sa": "WPSFD413",
    "ppi_x_sa": "WPSFD49116",
    "ppi_x_nsa": "WPUFD49116",
}
FUNDS_SERIES = {
    "funds_upper": "DFEDTARU",
    "funds_lower": "DFEDTARL",
}

SNAPSHOT_FILES = (
    "fred_cpi_monthly.csv",
    "fred_ppi_monthly.csv",
    "fred_funds_daily.csv",
    "bls_table6_september_2026.csv",
    "bls_ppi_manual_prints.csv",
)
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_hashes(directory: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in SNAPSHOT_FILES:
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(
                f"Committed snapshot is missing: {path}. "
                "This script will not download a replacement into data/raw/."
            )
        hashes[name] = file_sha256(path)
    return hashes


def load_expected_hashes(sources_path: Path) -> dict[str, str]:
    if not sources_path.is_file():
        raise RuntimeError(
            "Refusing to establish a new snapshot baseline: "
            f"{sources_path} is missing."
        )
    try:
        document = json.loads(sources_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{sources_path} cannot be read as JSON.") from exc
    recorded = document.get("snapshot_sha256") if isinstance(document, dict) else None
    if not isinstance(recorded, dict):
        raise RuntimeError(f"snapshot_sha256 is missing in {sources_path}.")
    expected: dict[str, str] = {}
    for name in SNAPSHOT_FILES:
        value = recorded.get(name)
        if not isinstance(value, str) or HEX_SHA256.fullmatch(value) is None:
            raise RuntimeError(f"snapshot_sha256[{name}] is missing or malformed.")
        expected[name] = value
    return expected


def source_document(hashes: dict[str, str], mode: str, output_dir: str) -> dict:
    return {
        "retrieved_for": "September 2026 CPI and PPI",
        "reproduction_mode": mode,
        "output_dir": output_dir,
        "cpi_archive_url": CPI_ARCHIVE,
        "ppi_archive_url": PPI_ARCHIVE,
        "cpi_table6_url": "https://www.bls.gov/news.release/cpi.t06.htm",
        "fred": "https://fred.stlouisfed.org/",
        "fred_vintage": {
            "cpi": {
                "realtime_start": CPI_VINTAGE,
                "realtime_end": CPI_VINTAGE,
                "observation_start": OBS_START,
                "observation_end": MONTH_END,
            },
            "ppi": {
                "realtime_start": PPI_VINTAGE,
                "realtime_end": PPI_VINTAGE,
                "observation_start": OBS_START,
                "observation_end": MONTH_END,
            },
            "funds": {
                "realtime_start": FUNDS_VINTAGE,
                "realtime_end": FUNDS_VINTAGE,
                "observation_start": OBS_START,
                "observation_end": FUNDS_END,
            },
        },
        "snapshot_sha256": {name: hashes[name] for name in SNAPSHOT_FILES},
        "cpi_series": CPI_SERIES,
        "ppi_series": PPI_SERIES,
        "funds_series": FUNDS_SERIES,
        "notes": [
            "Exact reproduction reads data/raw and does not download.",
            "python scripts/01_fetch_data.py --refresh writes data/raw/refresh/ only.",
            "CPI realtime bounds are 2026-10-14. PPI realtime bounds are 2026-10-15.",
            "Table 6 effects and the two PPI manual prints are transcribed, not estimated.",
            "observation_end alone does not freeze later revisions.",
        ],
    }


def verify_snapshots() -> None:
    sources_path = RAW_DIR / "sources.json"
    before = snapshot_hashes(RAW_DIR)
    expected = load_expected_hashes(sources_path)
    for name in SNAPSHOT_FILES:
        if before[name] != expected[name]:
            raise RuntimeError(
                f"{RAW_DIR / name} does not match snapshot_sha256. "
                f"Expected {expected[name]}, found {before[name]}. "
                "No file was modified."
            )
    sources_path.write_text(
        json.dumps(source_document(before, "committed_snapshot", "data/raw"), indent=2) + "\n",
        encoding="utf-8",
    )
    after = snapshot_hashes(RAW_DIR)
    for name in SNAPSHOT_FILES:
        if after[name] != before[name]:
            raise RuntimeError(f"Verification changed {name}.")
    print("Verified committed snapshots against snapshot_sha256. No FRED download.")


def fetch_frame(fred, series_map: dict[str, str], vintage: str, observation_end: str) -> pd.DataFrame:
    frames = {}
    for name, series_id in series_map.items():
        series = fred.get_series(
            series_id,
            observation_start=OBS_START,
            observation_end=observation_end,
            realtime_start=vintage,
            realtime_end=vintage,
        )
        if series is None or series.dropna().empty:
            raise RuntimeError(f"FRED returned no rows for {series_id} at {vintage}.")
        frames[name] = series.sort_index()
    frame = pd.DataFrame(frames).sort_index()
    frame.index.name = "date"
    return frame


def refresh_vintage() -> None:
    before = snapshot_hashes(RAW_DIR)
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("FRED_API_KEY is required for --refresh.")
    from fredapi import Fred

    REFRESH_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)
    cpi = fetch_frame(fred, CPI_SERIES, CPI_VINTAGE, MONTH_END)
    ppi = fetch_frame(fred, PPI_SERIES, PPI_VINTAGE, MONTH_END)
    funds = fetch_frame(fred, FUNDS_SERIES, FUNDS_VINTAGE, FUNDS_END)
    cpi.to_csv(REFRESH_DIR / "fred_cpi_monthly.csv")
    ppi.to_csv(REFRESH_DIR / "fred_ppi_monthly.csv")
    funds.to_csv(REFRESH_DIR / "fred_funds_daily.csv")
    after = snapshot_hashes(RAW_DIR)
    for name in SNAPSHOT_FILES:
        if after[name] != before[name]:
            raise RuntimeError(f"--refresh changed the committed snapshot {name}.")
    print(f"Wrote a side copy under {REFRESH_DIR}. Committed snapshots were not replaced.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify or refresh the CPI and PPI vintage.")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.refresh:
        refresh_vintage()
    else:
        verify_snapshots()


if __name__ == "__main__":
    main()
