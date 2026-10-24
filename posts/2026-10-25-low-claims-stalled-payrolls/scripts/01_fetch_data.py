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
checks data/raw/fred_monthly.csv and data/raw/fred_weekly.csv against
snapshot_sha256 in data/raw/sources.json and exits. It does not call FRED
and it does not replace those files. A missing or mismatched hash is an error.
This script will not invent a new baseline.

    python scripts/01_fetch_data.py --refresh

--refresh requires FRED_API_KEY. It writes data/raw/refresh/ only.
Weekly claims use the October 22, 2026 release vintage. Payrolls, household
rates, earnings, and the recession flag use the October 2, 2026 Employment
Situation vintage. An observation end alone does not freeze later revisions.
02_clean_data.py reads data/raw/, not data/raw/refresh/.

Friendly name -> FRED series ID
--------------------------------
initial_claims      ICSA              new unemployment-insurance filings
claims_4wk          IC4WSA            official 4-week average of those filings
continuing_claims   CCSA              people still on unemployment insurance
continuing_4wk      CC4WSA            official 4-week average of that stock
insured_rate        IURSA             continued claims as a percent of covered jobs
payems              PAYEMS            nonfarm payroll employment, thousands
unrate              UNRATE            unemployment rate
civpart             CIVPART           labor force participation rate
ahe                 CES0500000003     average hourly earnings, total private
usrec               USREC             NBER recession months (1 = recession)

What the raw CSVs contain
--------------------------
fred_weekly.csv is one row per week ending Saturday, back to 1967.
fred_monthly.csv is one row per month. Payrolls and the household survey end
in September 2026. Claims end the week of October 17, 2026. Continued claims
and the insured rate end the week of October 10, 2026.
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

CLAIMS_VINTAGE = "2026-10-22"
PAYROLL_VINTAGE = "2026-10-02"
OBS_START = "1967-01-01"
CLAIMS_END = "2026-10-17"
CONTINUING_END = "2026-10-10"
MONTHLY_END = "2026-09-01"

BLS_ARCHIVE_URL = "https://www.bls.gov/news.release/archives/empsit_10022026.htm"
FOMC_URL = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm"
CLAIMS_RELEASE_URL = "https://www.dol.gov/ui/data.pdf"

WEEKLY_SERIES = {
    "initial_claims": "ICSA",
    "claims_4wk": "IC4WSA",
    "continuing_claims": "CCSA",
    "continuing_4wk": "CC4WSA",
    "insured_rate": "IURSA",
}

MONTHLY_SERIES = {
    "payems": "PAYEMS",
    "unrate": "UNRATE",
    "civpart": "CIVPART",
    "ahe": "CES0500000003",
    "usrec": "USREC",
}

SNAPSHOT_FILES = ("fred_monthly.csv", "fred_weekly.csv")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_hashes(directory: Path | None = None) -> dict[str, str]:
    raw_dir = RAW_DIR if directory is None else directory
    hashes: dict[str, str] = {}
    for name in SNAPSHOT_FILES:
        path = raw_dir / name
        if not path.exists():
            raise FileNotFoundError(
                f"Committed snapshot is missing: {path}. "
                "This script will not download a replacement into data/raw/."
            )
        hashes[name] = file_sha256(path)
    return hashes


def load_expected_snapshot_hashes(sources_path: Path) -> dict[str, str]:
    """Read the recorded baseline. Never invent one when the record is unusable."""
    if not sources_path.is_file():
        raise RuntimeError(
            "Refusing to establish a new snapshot baseline: "
            f"{sources_path} is missing."
        )
    try:
        document = json.loads(sources_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{sources_path} is malformed and cannot be read as JSON.") from exc
    recorded = document.get("snapshot_sha256") if isinstance(document, dict) else None
    if not isinstance(recorded, dict):
        raise RuntimeError(f"snapshot_sha256 is missing or malformed in {sources_path}.")
    expected: dict[str, str] = {}
    for name in SNAPSHOT_FILES:
        value = recorded.get(name)
        if not isinstance(value, str) or HEX_SHA256.fullmatch(value) is None:
            raise RuntimeError(f"snapshot_sha256[{name}] is missing or malformed in {sources_path}.")
        expected[name] = value
    return expected


def require_snapshot_hashes(directory: Path, sources_path: Path) -> dict[str, str]:
    expected = load_expected_snapshot_hashes(sources_path)
    actual = snapshot_hashes(directory)
    for name in SNAPSHOT_FILES:
        if actual[name] != expected[name]:
            raise RuntimeError(
                "Refusing to overwrite expected snapshot hashes: "
                f"{directory / name} does not match snapshot_sha256. "
                f"Expected {expected[name]}, found {actual[name]}."
            )
    return expected


def last_observation(series: pd.Series) -> str:
    observed = series.dropna()
    if observed.empty:
        raise RuntimeError(f"Series has no observations: {series.name}")
    return pd.Timestamp(observed.index[-1]).strftime("%Y-%m-%d")


def expected_end(name: str) -> str:
    if name in {"initial_claims", "claims_4wk"}:
        return CLAIMS_END
    if name in {"continuing_claims", "continuing_4wk", "insured_rate"}:
        return CONTINUING_END
    return MONTHLY_END


def verify_frame(frame: pd.DataFrame, names: dict[str, str], label: str) -> dict[str, str]:
    missing = [name for name in names if name not in frame.columns]
    if missing:
        raise RuntimeError(f"{label} is missing columns: {missing}")
    latest: dict[str, str] = {}
    for name in names:
        last = last_observation(frame[name])
        expected = expected_end(name)
        if last != expected:
            raise RuntimeError(
                f"{label} series {name} ends at {last}, expected {expected}. "
                "A longer file is a newer vintage, not this analysis."
            )
        latest[name] = last
    return latest


def source_document(latest: dict[str, str], mode: str, output_dir: str, hashes: dict[str, str]) -> dict:
    return {
        "retrieved_for": "October 22, 2026 weekly claims and October 2, 2026 Employment Situation",
        "reproduction_mode": mode,
        "output_dir": output_dir,
        "claims_release_url": CLAIMS_RELEASE_URL,
        "bls_archive_url": BLS_ARCHIVE_URL,
        "fomc_statement_url": FOMC_URL,
        "fred": "https://fred.stlouisfed.org/",
        "fred_vintage": {
            "weekly_realtime_start": CLAIMS_VINTAGE,
            "weekly_realtime_end": CLAIMS_VINTAGE,
            "monthly_realtime_start": PAYROLL_VINTAGE,
            "monthly_realtime_end": PAYROLL_VINTAGE,
            "observation_start": OBS_START,
            "observation_end": {
                "initial_claims": CLAIMS_END,
                "continuing_claims": CONTINUING_END,
                "monthly": MONTHLY_END,
            },
        },
        "snapshot_sha256": {name: hashes[name] for name in SNAPSHOT_FILES},
        "weekly_series": WEEKLY_SERIES,
        "monthly_series": MONTHLY_SERIES,
        "latest_observation": latest,
        "prose_only_series": ["IURSA", "UNRATE", "CIVPART", "CES0500000003"],
        "notes": [
            "Exact reproduction reads data/raw and does not download.",
            "--refresh writes data/raw/refresh/ and does not replace the committed CSVs.",
            "Weekly series use realtime_end 2026-10-22. Monthly series use realtime_end 2026-10-02.",
            "observation_end alone does not freeze later revisions.",
            "The prior week's advance claims print, 199,000, is not in the revised FRED vintage. It is transcribed in 04.",
            "The payroll confidence interval and the July-August revision are transcribed from the October 2 BLS archive.",
            "The funds-rate range is the September 16, 2026 decision, not an October result.",
        ],
    }


def verify_snapshots() -> None:
    sources_path = RAW_DIR / "sources.json"
    before = snapshot_hashes()
    verified = require_snapshot_hashes(RAW_DIR, sources_path)
    monthly = pd.read_csv(RAW_DIR / "fred_monthly.csv", index_col="date", parse_dates=True)
    weekly = pd.read_csv(RAW_DIR / "fred_weekly.csv", index_col="date", parse_dates=True)
    latest: dict[str, str] = {}
    latest.update(verify_frame(monthly, MONTHLY_SERIES, "fred_monthly.csv"))
    latest.update(verify_frame(weekly, WEEKLY_SERIES, "fred_weekly.csv"))
    document = source_document(latest, "committed_snapshot", "data/raw", verified)
    sources_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    after = snapshot_hashes()
    for name, digest in before.items():
        if after[name] != digest:
            raise RuntimeError(f"Reproduction changed {RAW_DIR / name}.")
    print("Verified committed snapshots. No FRED download. CSVs unchanged.")
    for name, stamp in latest.items():
        print(f"  {name}: {stamp}")


def fetch_vintage(fred, series_id: str, observation_end: str, vintage: str) -> pd.Series:
    series = fred.get_series(
        series_id,
        observation_start=OBS_START,
        observation_end=observation_end,
        realtime_start=vintage,
        realtime_end=vintage,
    )
    if series.empty:
        raise RuntimeError(
            f"FRED returned no observations for {series_id} at vintage {vintage} through {observation_end}"
        )
    return series.sort_index()


def refresh_vintage() -> None:
    """Write a side copy. Do not create or replace data/raw snapshots."""
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("FRED_API_KEY is required for --refresh.")

    existing = {}
    if all((RAW_DIR / name).exists() for name in SNAPSHOT_FILES):
        existing = snapshot_hashes()

    from fredapi import Fred

    REFRESH_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)
    latest: dict[str, str] = {}

    monthly_frames: dict[str, pd.Series] = {}
    for name, series_id in MONTHLY_SERIES.items():
        print(f"Refreshing {name} ({series_id}) through {MONTHLY_END} at {PAYROLL_VINTAGE}")
        series = fetch_vintage(fred, series_id, MONTHLY_END, PAYROLL_VINTAGE)
        series.index = series.index.to_period("M").to_timestamp()
        series = series.groupby(series.index).last().sort_index()
        last = last_observation(series)
        if last != MONTHLY_END:
            raise RuntimeError(f"Refresh of {name} ended at {last}, expected {MONTHLY_END}.")
        monthly_frames[name] = series
        latest[name] = last
    monthly = pd.DataFrame(monthly_frames).sort_index()
    monthly.index.name = "date"
    monthly_path = REFRESH_DIR / "fred_monthly.csv"
    monthly.to_csv(monthly_path)

    weekly_frames: dict[str, pd.Series] = {}
    for name, series_id in WEEKLY_SERIES.items():
        end = expected_end(name)
        print(f"Refreshing {name} ({series_id}) through {end} at {CLAIMS_VINTAGE}")
        series = fetch_vintage(fred, series_id, end, CLAIMS_VINTAGE)
        last = last_observation(series)
        if last != end:
            raise RuntimeError(f"Refresh of {name} ended at {last}, expected {end}.")
        weekly_frames[name] = series
        latest[name] = last
    weekly = pd.DataFrame(weekly_frames).sort_index()
    weekly.index.name = "date"
    weekly_path = REFRESH_DIR / "fred_weekly.csv"
    weekly.to_csv(weekly_path)

    # Hash the side copy only. Do not write those hashes onto the committed files.
    side_hashes = {
        "fred_monthly.csv": file_sha256(monthly_path),
        "fred_weekly.csv": file_sha256(weekly_path),
    }
    document = source_document(latest, "refresh_side_copy", "data/raw/refresh", side_hashes)
    (REFRESH_DIR / "sources.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    if existing:
        after = snapshot_hashes()
        for name, digest in existing.items():
            if after[name] != digest:
                raise RuntimeError(f"--refresh changed the committed snapshot {name}.")
    print("Wrote", monthly_path)
    print("Wrote", weekly_path)
    print("Committed snapshots were not modified.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify or refresh the FRED snapshots for this post.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Write the release vintages under data/raw/refresh/. Does not replace data/raw CSVs.",
    )
    args = parser.parse_args()
    if args.refresh:
        refresh_vintage()
    else:
        verify_snapshots()


if __name__ == "__main__":
    main()
