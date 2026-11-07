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
and it does not replace those files. A missing, malformed, or mismatched
hash is an error. This script will not invent a new baseline.

    python scripts/01_fetch_data.py --refresh

--refresh requires FRED_API_KEY. It writes data/raw/refresh/ only.
CES and CPS use the November 6, 2026 Employment Situation vintage.
JOLTS uses the November 3, 2026 vintage. Claims use the November 5, 2026
DOL vintage. An observation end alone does not freeze later revisions.
02_clean_data.py reads data/raw/, not data/raw/refresh/.

Friendly name -> FRED series ID
--------------------------------
payems                 PAYEMS            nonfarm payroll employment, thousands
uspriv                 USPRIV            private payroll employment, thousands
usgovt                 USGOVT            government payroll employment, thousands
unrate                 UNRATE            unemployment rate, U-3, percent
u6rate                 U6RATE            U-6 unemployment rate, percent
civpart                CIVPART           labor force participation rate, percent
emratio                EMRATIO           employment-population ratio, percent
ahe                    CES0500000003     average hourly earnings, all private employees, dollars
ahe_prod               AHETPI            average hourly earnings, production and nonsupervisory, dollars
hours                  AWHAETP           average weekly hours, all private employees
professional           USPBS             professional and business services, thousands
healthcare             CES6562000101     health care employment, thousands
manufacturing          MANEMP            manufacturing employment, thousands
construction           USCONS            construction employment, thousands
information            USINFO            information employment, thousands
financial              USFIRE            financial activities, thousands
leisure                USLAH             leisure and hospitality, thousands
temp_help              TEMPHELPS         temporary help services, thousands
labor_force            CLF16OV           civilian labor force, thousands
employed               CE16OV            household employment, thousands
unemployed             UNEMPLOY          unemployed level, thousands
pte_economic           LNS12032194       part time for economic reasons, thousands
long_term_unemployed   UEMP27OV          unemployed 27 weeks or more, thousands
jolts_openings         JTSJOL            job openings, thousands
jolts_openings_rate    JTSJOR            job openings rate, percent
jolts_hires            JTSHIL            hires, thousands
jolts_quits            JTSQUL            quits, thousands
jolts_quits_rate       JTSQUR            quits rate, percent
jolts_layoffs          JTSLDL            layoffs and discharges, thousands
initial_claims         ICSA              new unemployment-insurance filings
claims_4wk             IC4WSA            four-week average of initial claims
continued_claims       CCSA              continued claims
insured_rate           IURSA             insured unemployment rate, percent

What the raw CSVs contain
--------------------------
fred_monthly.csv is one row per month from January 2019.
Payrolls and the household survey end in October 2026.
JOLTS ends in September 2026, so October is blank on those columns.
fred_weekly.csv is one row per week. Initial claims end the week of
October 31, 2026. Continued claims and the insured rate end the week of
October 24, 2026. A blank cell is a missing published week, not a zero.
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

CES_VINTAGE = "2026-11-06"
JOLTS_VINTAGE = "2026-11-03"
CLAIMS_VINTAGE = "2026-11-05"
OBS_START = "2019-01-01"
CES_END = "2026-10-01"
JOLTS_END = "2026-09-01"
CLAIMS_END = "2026-10-31"
CONTINUING_END = "2026-10-24"

BLS_ARCHIVE_URL = "https://www.bls.gov/news.release/archives/empsit_11062026.htm"
JOLTS_ARCHIVE_URL = "https://www.bls.gov/news.release/archives/jolts_11032026.htm"
CLAIMS_RELEASE_URL = "https://www.dol.gov/ui/data.pdf"
FOMC_URL = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm"

# name -> (FRED id, vintage date, last observation date, monthly or weekly)
SERIES = {
    "payems": ("PAYEMS", CES_VINTAGE, CES_END, "M"),
    "uspriv": ("USPRIV", CES_VINTAGE, CES_END, "M"),
    "usgovt": ("USGOVT", CES_VINTAGE, CES_END, "M"),
    "unrate": ("UNRATE", CES_VINTAGE, CES_END, "M"),
    "u6rate": ("U6RATE", CES_VINTAGE, CES_END, "M"),
    "civpart": ("CIVPART", CES_VINTAGE, CES_END, "M"),
    "emratio": ("EMRATIO", CES_VINTAGE, CES_END, "M"),
    "ahe": ("CES0500000003", CES_VINTAGE, CES_END, "M"),
    "ahe_prod": ("AHETPI", CES_VINTAGE, CES_END, "M"),
    "hours": ("AWHAETP", CES_VINTAGE, CES_END, "M"),
    "professional": ("USPBS", CES_VINTAGE, CES_END, "M"),
    "healthcare": ("CES6562000101", CES_VINTAGE, CES_END, "M"),
    "manufacturing": ("MANEMP", CES_VINTAGE, CES_END, "M"),
    "construction": ("USCONS", CES_VINTAGE, CES_END, "M"),
    "information": ("USINFO", CES_VINTAGE, CES_END, "M"),
    "financial": ("USFIRE", CES_VINTAGE, CES_END, "M"),
    "leisure": ("USLAH", CES_VINTAGE, CES_END, "M"),
    "temp_help": ("TEMPHELPS", CES_VINTAGE, CES_END, "M"),
    "labor_force": ("CLF16OV", CES_VINTAGE, CES_END, "M"),
    "employed": ("CE16OV", CES_VINTAGE, CES_END, "M"),
    "unemployed": ("UNEMPLOY", CES_VINTAGE, CES_END, "M"),
    "pte_economic": ("LNS12032194", CES_VINTAGE, CES_END, "M"),
    "long_term_unemployed": ("UEMP27OV", CES_VINTAGE, CES_END, "M"),
    "jolts_openings": ("JTSJOL", JOLTS_VINTAGE, JOLTS_END, "M"),
    "jolts_openings_rate": ("JTSJOR", JOLTS_VINTAGE, JOLTS_END, "M"),
    "jolts_hires": ("JTSHIL", JOLTS_VINTAGE, JOLTS_END, "M"),
    "jolts_quits": ("JTSQUL", JOLTS_VINTAGE, JOLTS_END, "M"),
    "jolts_quits_rate": ("JTSQUR", JOLTS_VINTAGE, JOLTS_END, "M"),
    "jolts_layoffs": ("JTSLDL", JOLTS_VINTAGE, JOLTS_END, "M"),
    "initial_claims": ("ICSA", CLAIMS_VINTAGE, CLAIMS_END, "W"),
    "claims_4wk": ("IC4WSA", CLAIMS_VINTAGE, CLAIMS_END, "W"),
    "continued_claims": ("CCSA", CLAIMS_VINTAGE, CONTINUING_END, "W"),
    "insured_rate": ("IURSA", CLAIMS_VINTAGE, CONTINUING_END, "W"),
}

MONTHLY_SERIES = {name: spec[0] for name, spec in SERIES.items() if spec[3] == "M"}
WEEKLY_SERIES = {name: spec[0] for name, spec in SERIES.items() if spec[3] == "W"}
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
        raise RuntimeError(
            f"{sources_path} is malformed and cannot be read as JSON."
        ) from exc
    recorded = document.get("snapshot_sha256") if isinstance(document, dict) else None
    if not isinstance(recorded, dict):
        raise RuntimeError(f"snapshot_sha256 is missing or malformed in {sources_path}.")
    expected: dict[str, str] = {}
    for name in SNAPSHOT_FILES:
        value = recorded.get(name)
        if not isinstance(value, str) or HEX_SHA256.fullmatch(value) is None:
            raise RuntimeError(
                f"snapshot_sha256[{name}] is missing or malformed in {sources_path}."
            )
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
                f"Expected {expected[name]}, found {actual[name]}. "
                "The snapshot files and sources.json were not modified."
            )
    return expected


def last_observation(series: pd.Series) -> str:
    observed = series.dropna()
    if observed.empty:
        raise RuntimeError(f"Series has no observations: {series.name}")
    return pd.Timestamp(observed.index[-1]).strftime("%Y-%m-%d")


def verify_frame(frame: pd.DataFrame, names: dict[str, str], label: str) -> dict[str, str]:
    missing = [name for name in names if name not in frame.columns]
    if missing:
        raise RuntimeError(f"{label} snapshot is missing required columns: {missing}")
    latest: dict[str, str] = {}
    for name in names:
        last = last_observation(frame[name])
        expected = SERIES[name][2]
        if last != expected:
            raise RuntimeError(
                f"{label} series {name} ends at {last}, expected {expected}. "
                "A longer file is a newer vintage, not this analysis."
            )
        latest[name] = last
    return latest


def source_document(latest: dict[str, str], mode: str, output_dir: str, hashes: dict[str, str]) -> dict:
    return {
        "retrieved_for": "October 2026 Employment Situation",
        "analysis_release_date": CES_VINTAGE,
        "reproduction_mode": mode,
        "output_dir": output_dir,
        "bls_archive_url": BLS_ARCHIVE_URL,
        "jolts_archive_url": JOLTS_ARCHIVE_URL,
        "claims_release_url": CLAIMS_RELEASE_URL,
        "fomc_statement_url": FOMC_URL,
        "fred": "https://fred.stlouisfed.org/",
        "fred_vintage": {
            "ces_cps": {"realtime_start": CES_VINTAGE, "realtime_end": CES_VINTAGE, "observation_end": CES_END},
            "jolts": {"realtime_start": JOLTS_VINTAGE, "realtime_end": JOLTS_VINTAGE, "observation_end": JOLTS_END},
            "claims": {
                "realtime_start": CLAIMS_VINTAGE,
                "realtime_end": CLAIMS_VINTAGE,
                "initial_claims_end": CLAIMS_END,
                "continued_claims_end": CONTINUING_END,
            },
            "observation_start": OBS_START,
        },
        "snapshot_sha256": {name: hashes[name] for name in SNAPSHOT_FILES},
        "monthly_series": MONTHLY_SERIES,
        "weekly_series": WEEKLY_SERIES,
        "latest_observation": latest,
        "notes": [
            "Exact reproduction reads data/raw/fred_monthly.csv and fred_weekly.csv.",
            "python scripts/01_fetch_data.py verifies those files and does not download.",
            "python scripts/01_fetch_data.py --refresh writes data/raw/refresh/ only.",
            "CES and CPS realtime bounds are 2026-11-06. JOLTS bounds are 2026-11-03. Claims bounds are 2026-11-05.",
            "observation_end alone does not freeze revisions.",
            "JOLTS ends in September 2026. Do not treat it as October payrolls.",
            "October 2025 household values may be blank because that month was not collected. Leave the hole.",
            "Published Employment Situation changes win when a FRED level difference disagrees. Those pins live in 04.",
        ],
    }


def verify_snapshot_dir(raw_dir: Path) -> dict[str, str]:
    sources_path = raw_dir / "sources.json"
    verified = require_snapshot_hashes(raw_dir, sources_path)
    monthly = pd.read_csv(raw_dir / "fred_monthly.csv", index_col="date", parse_dates=True)
    weekly = pd.read_csv(raw_dir / "fred_weekly.csv", index_col="date", parse_dates=True)
    latest: dict[str, str] = {}
    latest.update(verify_frame(monthly, MONTHLY_SERIES, "fred_monthly.csv"))
    latest.update(verify_frame(weekly, WEEKLY_SERIES, "fred_weekly.csv"))
    document = source_document(latest, "committed_snapshot", "data/raw", verified)
    sources_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return latest


def verify_snapshots() -> None:
    before = snapshot_hashes()
    latest = verify_snapshot_dir(RAW_DIR)
    after = snapshot_hashes()
    for name, digest in before.items():
        if after[name] != digest:
            raise RuntimeError(f"Reproduction changed the snapshot: {RAW_DIR / name}")
    print("Verified committed snapshots against snapshot_sha256. No FRED download. CSVs unchanged.")
    for name, stamp in latest.items():
        print(f"  {name}: {stamp}")


def fetch_vintage(fred, series_id: str, vintage: str, observation_end: str) -> pd.Series:
    series = fred.get_series(
        series_id,
        observation_start=OBS_START,
        observation_end=observation_end,
        realtime_start=vintage,
        realtime_end=vintage,
    )
    if series.empty:
        raise RuntimeError(
            f"FRED returned no observations for {series_id} "
            f"at vintage {vintage} through {observation_end}"
        )
    return series.sort_index()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    """Write LF endings so a later Git checkout does not change the hash."""
    frame.to_csv(path, lineterminator="\n")


def refresh_vintage() -> None:
    """Write a side copy. Do not create or replace the committed snapshot."""
    snapshots_exist = all((RAW_DIR / name).exists() for name in SNAPSHOT_FILES)
    before = snapshot_hashes() if snapshots_exist else None
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY is required for --refresh. "
            "The default command reproduces the post without a key."
        )

    from fredapi import Fred

    REFRESH_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)
    monthly_frames: dict[str, pd.Series] = {}
    weekly_frames: dict[str, pd.Series] = {}
    latest: dict[str, str] = {}

    for name, (series_id, vintage, end, freq) in SERIES.items():
        print(f"Refreshing {name} ({series_id}) through {end} at {vintage}")
        series = fetch_vintage(fred, series_id, vintage, end)
        if freq == "M":
            series.index = series.index.to_period("M").to_timestamp()
            series = series.groupby(series.index).last().sort_index()
            monthly_frames[name] = series
        else:
            series.index = pd.to_datetime(series.index)
            series = series.groupby(series.index).last().sort_index()
            weekly_frames[name] = series
        last = last_observation(series)
        if last != end:
            raise RuntimeError(
                f"Refresh of {name} ended at {last}, expected {end}. "
                "The side copy was not accepted."
            )
        latest[name] = last

    monthly = pd.DataFrame(monthly_frames).sort_index()
    monthly.index.name = "date"
    weekly = pd.DataFrame(weekly_frames).sort_index()
    weekly.index.name = "date"
    write_csv(monthly, REFRESH_DIR / "fred_monthly.csv")
    write_csv(weekly, REFRESH_DIR / "fred_weekly.csv")
    hashes = snapshot_hashes(REFRESH_DIR)
    document = source_document(latest, "refresh_side_copy", "data/raw/refresh", hashes)
    (REFRESH_DIR / "sources.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    if before is not None:
        after = snapshot_hashes()
        for name, digest in before.items():
            if after[name] != digest:
                raise RuntimeError(f"--refresh changed the committed snapshot: {RAW_DIR / name}")
    print("Wrote", REFRESH_DIR / "fred_monthly.csv")
    print("Wrote", REFRESH_DIR / "fred_weekly.csv")
    print("Committed snapshots were not modified.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify or refresh the November 2026 labor snapshot."
    )
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
