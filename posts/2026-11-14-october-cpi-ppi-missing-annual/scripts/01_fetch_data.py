"""
01_fetch_data.py
================
STEP 1 of the data pipeline.

Pipeline order
--------------
    python scripts/01_fetch_data.py
    python scripts/02_clean_data.py
    python scripts/04_compute_stats.py

The default command reproduces the post from the committed files in
data/raw/. It checks each snapshot against snapshot_sha256 in
data/raw/sources.json and exits. It does not download.

    python scripts/01_fetch_data.py --refresh

--refresh needs FRED_API_KEY. It writes data/raw/refresh/ only, with
realtime_start and realtime_end set to each release date. It does not
replace the committed CSVs. An observation end alone does not freeze
later revisions.

The first lock of those committed files is a separate step. This script
will not invent a new baseline when sources.json is missing.

FRED key
--------
Read FRED_API_KEY from the environment. The key is not stored in the repo.
https://fred.stlouisfed.org/docs/api/api_key.html

Friendly name -> series id
--------------------------
CPI vintage 2026-11-10
    headline_sa              CPIAUCSL
    headline_nsa             CPIAUCNS
    core_sa                  CPILFESL
    core_nsa                 CPILFENS
    food_sa                  CPIUFDSL
    energy_sa                CPIENGSL
    shelter_sa               CUSR0000SAH1
    rent_sa                  CUSR0000SEHA
    oer_sa                   CUSR0000SEHC
    gasoline_sa              CUSR0000SETB01
    gasoline_nsa             CUUR0000SETB01

PPI vintage 2026-11-13
    ppi_fd_sa                PPIFIS
    ppi_fd_nsa               PPIFID
    ppi_goods_sa             PPIDGS
    ppi_goods_nsa            PPIFDG
    ppi_services_sa          PPIDSS
    ppi_services_nsa         PPIFDS
    ppi_foods_sa             PPIDFS
    ppi_energy_sa            PPIDES
    ppi_core_goods_sa        WPSFD413
    ppi_x_sa                 WPSFD49116
    ppi_x_nsa                WPUFD49116

Productivity vintage 2026-11-05
    prod_q_ann               PRS85006092
    prod_yoy                 PRS85006091
    ulc_q_ann                PRS85006112
    ulc_yoy                  PRS85006111

PCE vintage 2026-10-29, through September 2026
    pce                      PCEPI
    core_pce                 PCEPILFE

Earnings vintage 2026-11-06
    ahe                      CES0500000003

Funds vintage 2026-11-13
    funds_upper              DFEDTARU
    funds_lower              DFEDTARL

What the raw files contain
--------------------------
fred_cpi_monthly.csv, fred_ppi_monthly.csv, fred_pce_monthly.csv, and
fred_earnings_monthly.csv are index levels (earnings are dollars).
fred_productivity_quarterly.csv holds published percent changes.
fred_funds_monthly.csv holds the last available daily target-range reading
in each month, dated to the first of that month. It is not a daily file.
bls_table6_october_2026.csv is a transcribed slice of the BLS 1-month
analysis table. manual_prints.json holds figures that are not FRED series.
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

OBS_START = "2015-01-01"
CPI_VINTAGE = "2026-11-10"
PPI_VINTAGE = "2026-11-13"
PROD_VINTAGE = "2026-11-05"
PCE_VINTAGE = "2026-10-29"
AHE_VINTAGE = "2026-11-06"
FUNDS_VINTAGE = "2026-11-13"
CPI_END = "2026-10-01"
PPI_END = "2026-10-01"
PROD_END = "2026-07-01"
PCE_END = "2026-09-01"
AHE_END = "2026-10-01"
FUNDS_END = "2026-11-13"

CPI_RELEASE = "https://www.bls.gov/news.release/cpi.nr0.htm"
PPI_RELEASE = "https://www.bls.gov/news.release/ppi.nr0.htm"
PROD_RELEASE = "https://www.bls.gov/news.release/prod2.htm"
TABLE6_URL = "https://www.bls.gov/news.release/cpi.t06.htm"

CPI_SERIES = {
    "headline_sa": "CPIAUCSL",
    "headline_nsa": "CPIAUCNS",
    "core_sa": "CPILFESL",
    "core_nsa": "CPILFENS",
    "food_sa": "CPIUFDSL",
    "energy_sa": "CPIENGSL",
    "shelter_sa": "CUSR0000SAH1",
    "rent_sa": "CUSR0000SEHA",
    "oer_sa": "CUSR0000SEHC",
    "gasoline_sa": "CUSR0000SETB01",
    "gasoline_nsa": "CUUR0000SETB01",
}
PPI_SERIES = {
    "ppi_fd_sa": "PPIFIS",
    "ppi_fd_nsa": "PPIFID",
    "ppi_goods_sa": "PPIDGS",
    "ppi_goods_nsa": "PPIFDG",
    "ppi_services_sa": "PPIDSS",
    "ppi_services_nsa": "PPIFDS",
    "ppi_foods_sa": "PPIDFS",
    "ppi_energy_sa": "PPIDES",
    "ppi_core_goods_sa": "WPSFD413",
    "ppi_x_sa": "WPSFD49116",
    "ppi_x_nsa": "WPUFD49116",
}
PROD_SERIES = {
    "prod_q_ann": "PRS85006092",
    "prod_yoy": "PRS85006091",
    "ulc_q_ann": "PRS85006112",
    "ulc_yoy": "PRS85006111",
}
PCE_SERIES = {
    "pce": "PCEPI",
    "core_pce": "PCEPILFE",
}
AHE_SERIES = {"ahe": "CES0500000003"}
FUNDS_SERIES = {
    "funds_upper": "DFEDTARU",
    "funds_lower": "DFEDTARL",
}

FRED_FILES = (
    "fred_cpi_monthly.csv",
    "fred_ppi_monthly.csv",
    "fred_productivity_quarterly.csv",
    "fred_pce_monthly.csv",
    "fred_earnings_monthly.csv",
    "fred_funds_monthly.csv",
)
CURATED_FILES = (
    "bls_table6_october_2026.csv",
    "manual_prints.json",
)
SNAPSHOT_FILES = FRED_FILES + CURATED_FILES
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_hashes(directory: Path, names: tuple[str, ...] = SNAPSHOT_FILES) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in names:
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
        "retrieved_for": "October 2026 CPI and PPI",
        "reproduction_mode": mode,
        "output_dir": output_dir,
        "cpi_release_url": CPI_RELEASE,
        "ppi_release_url": PPI_RELEASE,
        "productivity_release_url": PROD_RELEASE,
        "cpi_table6_url": TABLE6_URL,
        "cpi_gap_notice_url": "https://www.bls.gov/cpi/notices/2026/12m-changes-202610.htm",
        "fred": "https://fred.stlouisfed.org/",
        "fred_vintage": {
            "cpi": {
                "realtime_start": CPI_VINTAGE,
                "realtime_end": CPI_VINTAGE,
                "observation_start": OBS_START,
                "observation_end": CPI_END,
            },
            "ppi": {
                "realtime_start": PPI_VINTAGE,
                "realtime_end": PPI_VINTAGE,
                "observation_start": OBS_START,
                "observation_end": PPI_END,
            },
            "productivity": {
                "realtime_start": PROD_VINTAGE,
                "realtime_end": PROD_VINTAGE,
                "observation_start": OBS_START,
                "observation_end": PROD_END,
            },
            "pce": {
                "realtime_start": PCE_VINTAGE,
                "realtime_end": PCE_VINTAGE,
                "observation_start": OBS_START,
                "observation_end": PCE_END,
            },
            "earnings": {
                "realtime_start": AHE_VINTAGE,
                "realtime_end": AHE_VINTAGE,
                "observation_start": OBS_START,
                "observation_end": AHE_END,
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
        "productivity_series": PROD_SERIES,
        "pce_series": PCE_SERIES,
        "earnings_series": AHE_SERIES,
        "funds_series": FUNDS_SERIES,
        "notes": [
            "Exact reproduction reads data/raw and does not download.",
            "python scripts/01_fetch_data.py --refresh writes data/raw/refresh/ only.",
            "CPI realtime bounds are 2026-11-10. PPI bounds are 2026-11-13.",
            "Productivity bounds are 2026-11-05. PCE bounds are 2026-10-29.",
            "Earnings bounds are 2026-11-06. Funds bounds are 2026-11-13.",
            "Table 6 rows used in the post are transcribed, not estimated.",
            "# MANUAL: Table 6 source https://www.bls.gov/news.release/cpi.t06.htm",
            "October 2025 CPI levels that FRED leaves blank stay blank.",
            "observation_end alone does not freeze later revisions.",
            "Funds are daily FRED series sampled at the last available reading in each month.",
        ],
    }


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, lineterminator="\n")


def fetch_frame(fred, series_map: dict[str, str], vintage: str, observation_end: str, quarterly: bool = False) -> pd.DataFrame:
    frames = {}
    for name, series_id in series_map.items():
        series = fred.get_series(
            series_id,
            observation_start=OBS_START if not quarterly else "2018-01-01",
            observation_end=observation_end,
            realtime_start=vintage,
            realtime_end=vintage,
        )
        if series is None or series.dropna().empty:
            raise RuntimeError(f"FRED returned no rows for {series_id} at {vintage}.")
        series = series.sort_index()
        series.index = pd.to_datetime(series.index)
        if quarterly:
            series.index = series.index.to_period("Q").to_timestamp()
        else:
            series.index = series.index.to_period("M").to_timestamp()
        series = series.groupby(series.index).last().sort_index()
        frames[name] = series
    frame = pd.DataFrame(frames).sort_index()
    frame.index.name = "date"
    return frame


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
    after = snapshot_hashes(RAW_DIR)
    for name in SNAPSHOT_FILES:
        if after[name] != before[name]:
            raise RuntimeError(f"Verification changed {name}.")
    print("Verified committed snapshots against snapshot_sha256. No files changed. No FRED download.")


def refresh_vintage() -> None:
    snapshots_exist = all((RAW_DIR / name).is_file() for name in FRED_FILES)
    before = snapshot_hashes(RAW_DIR, FRED_FILES) if snapshots_exist else None
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY is required for --refresh. "
            "The default command reproduces the post without a key."
        )
    from fredapi import Fred

    REFRESH_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)
    cpi = fetch_frame(fred, CPI_SERIES, CPI_VINTAGE, CPI_END)
    ppi = fetch_frame(fred, PPI_SERIES, PPI_VINTAGE, PPI_END)
    prod = fetch_frame(fred, PROD_SERIES, PROD_VINTAGE, PROD_END, quarterly=True)
    pce = fetch_frame(fred, PCE_SERIES, PCE_VINTAGE, PCE_END)
    ahe = fetch_frame(fred, AHE_SERIES, AHE_VINTAGE, AHE_END)
    funds = fetch_frame(fred, FUNDS_SERIES, FUNDS_VINTAGE, FUNDS_END)
    write_csv(cpi, REFRESH_DIR / "fred_cpi_monthly.csv")
    write_csv(ppi, REFRESH_DIR / "fred_ppi_monthly.csv")
    write_csv(prod, REFRESH_DIR / "fred_productivity_quarterly.csv")
    write_csv(pce, REFRESH_DIR / "fred_pce_monthly.csv")
    write_csv(ahe, REFRESH_DIR / "fred_earnings_monthly.csv")
    write_csv(funds, REFRESH_DIR / "fred_funds_monthly.csv")
    if before is not None:
        after = snapshot_hashes(RAW_DIR, FRED_FILES)
        for name, digest in before.items():
            if after[name] != digest:
                raise RuntimeError(f"--refresh changed the committed snapshot: {RAW_DIR / name}")
    print(f"Wrote a side copy under {REFRESH_DIR}. Committed snapshots were not replaced.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify or refresh the October 2026 vintage.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refetch vintages into data/raw/refresh/. Does not replace data/raw CSVs.",
    )
    args = parser.parse_args()
    if args.refresh:
        refresh_vintage()
    else:
        verify_snapshots()


if __name__ == "__main__":
    main()
