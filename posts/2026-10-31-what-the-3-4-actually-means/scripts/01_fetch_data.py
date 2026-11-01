"""
01_fetch_data.py
================
STEP 1 of the data pipeline.

Pipeline order
--------------
    python scripts/01_fetch_data.py
    python scripts/02_clean_data.py
    python scripts/04_compute_stats.py

The default command reproduces this post from the committed snapshots. It
checks each raw CSV against snapshot_sha256 in data/raw/sources.json and
exits. It does not call FRED and it does not replace those files.

    python scripts/01_fetch_data.py --refresh

--refresh requires FRED_API_KEY. It writes data/raw/refresh/ only.
GDP, prices, and the personal-income accounts use the October 29, 2026
vintage. The Employment Cost Index uses the October 30, 2026 vintage.
Payrolls use the October 2, 2026 Employment Situation vintage. Initial
claims use the October 29, 2026 vintage. An observation end alone does
not freeze later revisions. 02_clean_data.py reads data/raw/, not
data/raw/refresh/.

    python scripts/01_fetch_data.py --write-snapshot

Creates the snapshot once, only when the raw CSVs are still absent.
It will not overwrite an existing snapshot.

Friendly name -> FRED series ID
--------------------------------
Quarterly growth rates are already published as percent changes at a
seasonally adjusted annual rate. Contribution series are percentage
points at an annual rate. Price indexes are index levels. Monthly PCE
prices and real spending are index or level series. ECI series are
index levels. See sources.json for the full map.

What the raw CSVs contain
--------------------------
fred_quarterly.csv is one row per quarter, dated on the first day of
the quarter, through 2026-07-01 (third quarter of 2026).
fred_monthly.csv is one row per month through September 2026.
fred_eci.csv is one row per quarter through 2026-07-01.
fred_payems.csv is monthly payroll employment through September 2026.
fred_claims.csv is weekly initial claims through the week ended
2026-10-24.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
REFRESH_DIR = RAW_DIR / "refresh"

BEA_VINTAGE = "2026-10-29"
ECI_VINTAGE = "2026-10-30"
PAYROLL_VINTAGE = "2026-10-02"
CLAIMS_VINTAGE = "2026-10-29"
OBS_START_Q = "1959-01-01"
OBS_START_M = "2016-01-01"
OBS_START_ECI = "2001-01-01"
QUARTER_END = "2026-07-01"
MONTH_END = "2026-09-01"
CLAIMS_END = "2026-10-24"

QUARTERLY_SERIES = {
    "gdp_saar": "A191RL1Q225SBEA",
    "pdfp_saar": "PB0000031Q225SBEA",
    "final_sales_saar": "A190RL1Q225SBEA",
    "pce_saar": "DPCERL1Q225SBEA",
    "equipment_saar": "Y033RL1Q225SBEA",
    "ip_saar": "Y001RL1Q225SBEA",
    "nonres_saar": "A008RL1Q225SBEA",
    "structures_saar": "A009RL1Q225SBEA",
    "residential_saar": "A011RL1Q225SBEA",
    "imports_saar": "A021RL1Q158SBEA",
    "exports_saar": "A020RL1Q158SBEA",
    "government_saar": "A822RL1Q225SBEA",
    "federal_saar": "A823RL1Q225SBEA",
    "defense_saar": "A824RL1Q225SBEA",
    "nondefense_saar": "A825RL1Q225SBEA",
    "info_equip_saar": "Y034RL1Q225SBEA",
    "computers_saar": "B935RL1Q225SBEA",
    "real_dpi_saar": "A067RL1Q156SBEA",
    "pce_pp": "DPCERY2Q224SBEA",
    "equipment_pp": "Y033RY2Q224SBEA",
    "ip_pp": "Y001RY2Q224SBEA",
    "structures_pp": "A009RY2Q224SBEA",
    "residential_pp": "A011RY2Q224SBEA",
    "inventories_pp": "A014RY2Q224SBEA",
    "net_exports_pp": "A019RY2Q224SBEA",
    "imports_pp": "A021RY2Q224SBEA",
    "exports_pp": "A020RY2Q224SBEA",
    "government_pp": "A822RY2Q224SBEA",
    "federal_pp": "A823RY2Q224SBEA",
    "nondefense_pp": "A825RY2Q224SBEA",
    "computers_pp": "B935RY2Q224SBEA",
    "info_equip_pp": "Y034RY2Q224SBEA",
    "software_pp": "B985RY2Q224SBEA",
    "pce_price_index": "PCECTPI",
    "core_price_saar": "DPCCRV1Q225SBEA",
    "computers_price": "B935RG3Q086SBEA",
    "info_price": "Y034RG3Q086SBEA",
}

MONTHLY_SERIES = {
    "pce_price": "PCEPI",
    "core_price": "PCEPILFE",
    "real_pce": "PCEC96",
    "real_dpi": "DSPIC96",
    "saving": "PSAVERT",
    "income": "PI",
    "nominal_pce": "PCE",
    "dpi": "DSPI",
}

ECI_SERIES = {
    "comp_sa": "ECIALLCIV",
    "comp_nsa": "CIU1010000000000I",
    "wages_sa": "CIS1020000000000I",
    "wages_nsa": "CIU1020000000000I",
    "benefits_sa": "CIS1030000000000I",
    "benefits_nsa": "CIU1030000000000I",
}

SNAPSHOT_FILES = (
    "fred_quarterly.csv",
    "fred_monthly.csv",
    "fred_eci.csv",
    "fred_payems.csv",
    "fred_claims.csv",
)


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
        if not path.exists():
            raise FileNotFoundError(
                f"Committed snapshot is missing: {path}. "
                "This script will not download a replacement into data/raw/."
            )
        hashes[name] = file_sha256(path)
    return hashes


def load_expected_hashes(sources_path: Path) -> dict[str, str]:
    if not sources_path.is_file():
        raise RuntimeError(f"Missing snapshot record: {sources_path}")
    document = json.loads(sources_path.read_text(encoding="utf-8"))
    recorded = document.get("snapshot_sha256")
    if not isinstance(recorded, dict):
        raise RuntimeError("snapshot_sha256 is missing from sources.json.")
    expected: dict[str, str] = {}
    for name in SNAPSHOT_FILES:
        value = recorded.get(name)
        if not isinstance(value, str) or len(value) != 64:
            raise RuntimeError(f"snapshot_sha256[{name}] is missing or malformed.")
        expected[name] = value
    return expected


def last_observation(series: pd.Series) -> str:
    observed = series.dropna()
    if observed.empty:
        raise RuntimeError(f"Series has no observations: {series.name}")
    return pd.Timestamp(observed.index.max()).strftime("%Y-%m-%d")


def fetch_frame(fred, series_map: dict[str, str], vintage: str, start: str, end: str, freq: str) -> pd.DataFrame:
    frames: dict[str, pd.Series] = {}
    for name, series_id in series_map.items():
        try:
            series = fred.get_series(
                series_id,
                observation_start=start,
                observation_end=end,
                realtime_start=vintage,
                realtime_end=vintage,
            )
        except Exception as exc:
            raise RuntimeError(
                f"FRED vintage request failed for {series_id} at {vintage}. "
                "No current-vintage fallback was used."
            ) from exc
        if series is None or series.dropna().empty:
            raise RuntimeError(f"FRED returned no observations for {series_id} at {vintage}.")
        series = series.sort_index()
        if freq == "Q":
            series.index = series.index.to_period("Q").to_timestamp()
        elif freq == "M":
            series.index = series.index.to_period("M").to_timestamp()
        series = series.groupby(series.index).last().sort_index()
        series.name = name
        ended = last_observation(series)
        if ended != end:
            raise RuntimeError(f"{name} ended at {ended}, expected {end}.")
        frames[name] = series
    frame = pd.DataFrame(frames).sort_index()
    frame.index.name = "date"
    return frame


def fetch_claims(fred) -> pd.DataFrame:
    series = fred.get_series(
        "ICSA",
        observation_start="2024-01-01",
        observation_end=CLAIMS_END,
        realtime_start=CLAIMS_VINTAGE,
        realtime_end=CLAIMS_VINTAGE,
    )
    series = series.dropna().sort_index()
    series.index = pd.to_datetime(series.index).tz_localize(None)
    ended = last_observation(series)
    if ended != CLAIMS_END:
        raise RuntimeError(f"Initial claims ended at {ended}, expected {CLAIMS_END}.")
    frame = series.to_frame("initial_claims")
    frame.index.name = "date"
    return frame


def build_frames(fred) -> dict[str, pd.DataFrame]:
    quarterly = fetch_frame(fred, QUARTERLY_SERIES, BEA_VINTAGE, OBS_START_Q, QUARTER_END, "Q")
    if float(quarterly["gdp_saar"].iloc[-1]) != 3.4:
        raise RuntimeError("Quarterly snapshot is not the 3.4 percent advance estimate.")
    monthly = fetch_frame(fred, MONTHLY_SERIES, BEA_VINTAGE, OBS_START_M, MONTH_END, "M")
    eci = fetch_frame(fred, ECI_SERIES, ECI_VINTAGE, OBS_START_ECI, QUARTER_END, "Q")
    payems = fetch_frame(fred, {"payems": "PAYEMS"}, PAYROLL_VINTAGE, "2024-01-01", MONTH_END, "M")
    claims = fetch_claims(fred)
    return {
        "fred_quarterly.csv": quarterly,
        "fred_monthly.csv": monthly,
        "fred_eci.csv": eci,
        "fred_payems.csv": payems,
        "fred_claims.csv": claims,
    }


def source_document(mode: str, output_dir: str, hashes: dict[str, str]) -> dict:
    return {
        "retrieved_for": "Q3 2026 GDP advance estimate and September 2026 personal income",
        "bea_vintage": BEA_VINTAGE,
        "eci_vintage": ECI_VINTAGE,
        "payroll_vintage": PAYROLL_VINTAGE,
        "claims_vintage": CLAIMS_VINTAGE,
        "reproduction_mode": mode,
        "output_dir": output_dir,
        "fred_quarterly": QUARTERLY_SERIES,
        "fred_monthly": MONTHLY_SERIES,
        "fred_eci": ECI_SERIES,
        "fred_payems": {"payems": "PAYEMS"},
        "fred_claims": {"initial_claims": "ICSA"},
        "manual_prints": "data/raw/manual_prints.json",
        "bea_gdp_url": "https://www.bea.gov/news/2026/gdp-advance-estimate-3rd-quarter-2026",
        "bea_pce_url": "https://www.bea.gov/news/2026/personal-income-and-outlays-september-2026",
        "bls_eci_url": "https://www.bls.gov/news.release/eci.nr0.htm",
        "bls_payroll_url": "https://www.bls.gov/news.release/archives/empsit_10022026.htm",
        "snapshot_sha256": {name: hashes[name] for name in SNAPSHOT_FILES},
        "history_rule": (
            "Reproduction reads the committed CSVs in data/raw. "
            "python scripts/01_fetch_data.py verifies them and does not download. "
            "python scripts/01_fetch_data.py --refresh writes data/raw/refresh/ only. "
            "observation_end does not freeze later revisions."
        ),
    }


def write_frames(directory: Path, frames: dict[str, pd.DataFrame]) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(directory / name, lineterminator="\n")
    return snapshot_hashes(directory)


def verify_snapshots() -> None:
    sources_path = RAW_DIR / "sources.json"
    expected = load_expected_hashes(sources_path)
    actual = snapshot_hashes(RAW_DIR)
    for name in SNAPSHOT_FILES:
        if actual[name] != expected[name]:
            raise RuntimeError(
                f"{name} does not match snapshot_sha256. "
                f"Expected {expected[name]}, found {actual[name]}."
            )
    print("Verified committed snapshots against snapshot_sha256. No FRED download.")


def refresh() -> None:
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("FRED_API_KEY is required for --refresh.")
    before = snapshot_hashes(RAW_DIR)
    from fredapi import Fred

    frames = build_frames(Fred(api_key=api_key))
    hashes = write_frames(REFRESH_DIR, frames)
    (REFRESH_DIR / "sources.json").write_text(
        json.dumps(source_document("refresh_side_copy", "data/raw/refresh", hashes), indent=2) + "\n",
        encoding="utf-8",
    )
    after = snapshot_hashes(RAW_DIR)
    if after != before:
        raise RuntimeError("Refresh changed the committed snapshot.")
    print("Wrote refresh copies under data/raw/refresh/. Committed CSVs were not replaced.")


def write_snapshot() -> None:
    existing = [name for name in SNAPSHOT_FILES if (RAW_DIR / name).exists()]
    if existing:
        raise RuntimeError(
            "Refusing to overwrite an existing snapshot: " + ", ".join(existing)
        )
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("FRED_API_KEY is required for --write-snapshot.")
    from fredapi import Fred

    frames = build_frames(Fred(api_key=api_key))
    hashes = write_frames(RAW_DIR, frames)
    (RAW_DIR / "sources.json").write_text(
        json.dumps(source_document("committed_snapshot", "data/raw", hashes), indent=2) + "\n",
        encoding="utf-8",
    )
    print("Wrote the initial snapshot and sources.json.")
    for name, digest in hashes.items():
        print(f"  {name} {digest}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch or verify the Q3 2026 GDP snapshot.")
    parser.add_argument("--refresh", action="store_true", help="Write a side copy under data/raw/refresh/.")
    parser.add_argument("--write-snapshot", action="store_true", help="Create the snapshot once if it is absent.")
    args = parser.parse_args()
    if args.refresh and args.write_snapshot:
        raise SystemExit("Choose only one of --refresh or --write-snapshot.")
    if args.write_snapshot:
        write_snapshot()
    elif args.refresh:
        refresh()
    else:
        verify_snapshots()


if __name__ == "__main__":
    main()
