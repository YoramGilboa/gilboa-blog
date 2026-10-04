"""
01_fetch_data.py
================
STEP 1 of the data pipeline.

What this script does
---------------------
The default command reproduces the October 2, 2026 analysis from the committed
snapshots. It checks data/raw/fred_monthly.csv and data/raw/fred_weekly.csv
against snapshot_sha256 in data/raw/sources.json, records vintage metadata, and
exits. A missing, malformed, or mismatched hash is an error. The script does
not create a new baseline or replace the expected hashes. It does not call
FRED and does not replace those two files.

    python scripts/01_fetch_data.py

An optional historical refetch is separate from reproduction:

    python scripts/01_fetch_data.py --refresh

--refresh requires FRED_API_KEY and writes data/raw/refresh/. It requests the
October 2, 2026 release vintage (realtime_start and realtime_end) and the
observation cutoffs below. An observation end alone does not freeze later
revisions. The refresh files are not what 02_clean_data.py reads, and they
never replace the committed snapshots.

Pipeline order
--------------
    python scripts/01_fetch_data.py     # verify the committed snapshot
    python scripts/02_clean_data.py     # next: changes, m/m, y/y
    python scripts/04_compute_stats.py  # then: stats JSON for the prose

Friendly name -> FRED ID. Later scripts use the friendly names so they
never have to remember CES7072200001 versus PAYEMS.

Observation cutoffs for this post
----------------------------------
CES and CPS through 2026-09-01.
JOLTS through 2026-08-01 (August is the latest month in the October 2 snapshot).
Initial claims through the week ending 2026-09-26.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
REFRESH_DIR = RAW_DIR / "refresh"

# The Employment Situation vintage this draft was checked against.
# A refetch must set both realtime bounds. One observation_end does not
# freeze revisions that FRED publishes later.
ANALYSIS_VINTAGE = "2026-10-02"
OBS_START = "2019-01-01"
CES_CPS_END = "2026-09-01"
JOLTS_END = "2026-08-01"
CLAIMS_END = "2026-09-26"

BLS_ARCHIVE_URL = "https://www.bls.gov/news.release/archives/empsit_10022026.htm"
BLS_TABLE_URL = "https://www.bls.gov/news.release/archives/empsit_10022026.htm"
AUGUST_ARCHIVE_URL = "https://www.bls.gov/news.release/archives/empsit_09042026.htm"

# Employment levels are in thousands of jobs unless noted.
MONTHLY_SERIES = {
    "payems": "PAYEMS",
    "uspriv": "USPRIV",
    "usgovt": "USGOVT",
    "unrate": "UNRATE",
    "u6rate": "U6RATE",
    "civpart": "CIVPART",
    "emratio": "EMRATIO",
    "ahe": "CES0500000003",
    "ahe_prod": "AHETPI",
    "hours": "AWHAETP",
    "food_services": "CES7072200001",
    "local_education": "CES9093161101",
    "construction": "USCONS",
    "manufacturing": "MANEMP",
    "information": "USINFO",
    "leisure": "USLAH",
    "healthcare": "CES6562000101",
    "financial": "USFIRE",
    "professional": "USPBS",
    "temp_help": "TEMPHELPS",
    "insurance_carriers": "CES5552400001",
    "labor_force": "CLF16OV",
    "employed": "CE16OV",
    "nilf": "LNS15000000",
    "unemployed": "UNEMPLOY",
    "pte_economic": "LNS12032194",
    "long_term_unemployed": "UEMP27OV",
    "jolts_openings": "JTSJOL",
    "jolts_hires": "JTSHIL",
    "jolts_quits": "JTSQUL",
    "jolts_layoffs": "JTSLDL",
}

JOLTS_NAMES = {
    "jolts_openings",
    "jolts_hires",
    "jolts_quits",
    "jolts_layoffs",
}

WEEKLY_SERIES = {
    "initial_claims": "ICSA",
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
            f"{sources_path} is missing. "
            "Expected snapshot_sha256 values must already be recorded. "
            "This script will not write replacement hashes."
        )
    try:
        document = json.loads(sources_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Refusing to establish a new snapshot baseline: "
            f"{sources_path} is malformed and cannot be read as JSON."
        ) from exc
    if not isinstance(document, dict):
        raise RuntimeError(
            "Refusing to establish a new snapshot baseline: "
            f"{sources_path} does not contain a JSON object."
        )
    recorded = document.get("snapshot_sha256")
    if not isinstance(recorded, dict):
        raise RuntimeError(
            "Refusing to establish a new snapshot baseline: "
            f"snapshot_sha256 is missing or malformed in {sources_path}."
        )
    expected: dict[str, str] = {}
    for name in SNAPSHOT_FILES:
        value = recorded.get(name)
        if not isinstance(value, str) or HEX_SHA256.fullmatch(value) is None:
            raise RuntimeError(
                "Refusing to establish a new snapshot baseline: "
                f"snapshot_sha256[{name}] is missing or malformed in {sources_path}."
            )
        expected[name] = value
    return expected


def require_snapshot_hashes(directory: Path, sources_path: Path) -> dict[str, str]:
    """Return the recorded hashes only when both CSVs still match them."""
    expected = load_expected_snapshot_hashes(sources_path)
    actual = snapshot_hashes(directory)
    for name in SNAPSHOT_FILES:
        if actual[name] != expected[name]:
            raise RuntimeError(
                "Refusing to overwrite expected snapshot hashes: "
                f"{directory / name} does not match snapshot_sha256 in {sources_path}. "
                f"Expected {expected[name]}, found {actual[name]}. "
                "The snapshot files and sources.json were not modified."
            )
    return expected


def assert_snapshots_unchanged(before: dict[str, str]) -> None:
    after = snapshot_hashes()
    for name, digest in before.items():
        if after[name] != digest:
            raise RuntimeError(
                f"Refusing to leave a changed snapshot: {RAW_DIR / name}. "
                "Reproduction must keep the verified October 2 files."
            )


def expected_end(name: str) -> str:
    if name in JOLTS_NAMES:
        return JOLTS_END
    if name == "initial_claims":
        return CLAIMS_END
    return CES_CPS_END


def last_observation(series: pd.Series) -> str:
    observed = series.dropna()
    if observed.empty:
        raise RuntimeError(f"Series has no observations: {series.name}")
    return pd.Timestamp(observed.index[-1]).strftime("%Y-%m-%d")


def verify_frame(frame: pd.DataFrame, names: dict[str, str], label: str) -> dict[str, str]:
    """Require every series to end on its October 2 analysis date."""
    missing = [name for name in names if name not in frame.columns]
    if missing:
        raise RuntimeError(f"{label} snapshot is missing required columns: {missing}")

    latest: dict[str, str] = {}
    for name in names:
        last = last_observation(frame[name])
        expected = expected_end(name)
        if last != expected:
            raise RuntimeError(
                f"{label} series {name} ends at {last}, expected {expected}. "
                "A longer file is a newer vintage, not this analysis. "
                "Leave the committed snapshot in place. "
                "python scripts/01_fetch_data.py --refresh writes a side copy "
                "under data/raw/refresh/."
            )
        latest[name] = last
    return latest


def source_document(
    latest: dict[str, str],
    mode: str,
    output_dir: str,
    hashes: dict[str, str],
) -> dict:
    return {
        "retrieved_for": "September 2026 Employment Situation",
        "analysis_release_date": ANALYSIS_VINTAGE,
        "reproduction_mode": mode,
        "output_dir": output_dir,
        "bls_archive_url": BLS_ARCHIVE_URL,
        "bls_release_url": BLS_ARCHIVE_URL,
        "bls_table_b1_url": BLS_TABLE_URL,
        "august_bls_archive_url": AUGUST_ARCHIVE_URL,
        "adp_release_url": (
            "https://mediacenter.adp.com/2026-09-30-ADP-National-Employment-Report-"
            "Private-Sector-Employment-Increased-by-90,000-Jobs-in-September"
        ),
        "fred": "https://fred.stlouisfed.org/",
        "fred_vintage": {
            "realtime_start": ANALYSIS_VINTAGE,
            "realtime_end": ANALYSIS_VINTAGE,
            "observation_start": OBS_START,
            "observation_end": {
                "ces_cps": CES_CPS_END,
                "jolts": JOLTS_END,
                "initial_claims": CLAIMS_END,
            },
        },
        "snapshot_sha256": {name: hashes[name] for name in SNAPSHOT_FILES},
        "monthly_series": MONTHLY_SERIES,
        "weekly_series": WEEKLY_SERIES,
        "latest_observation": latest,
        "skipped_optional": [],
        "notes": [
            "Exact reproduction reads data/raw/fred_monthly.csv and fred_weekly.csv.",
            "python scripts/01_fetch_data.py verifies those files and does not download.",
            "python scripts/01_fetch_data.py --refresh writes data/raw/refresh/ only.",
            "Refresh sets realtime_start and realtime_end to 2026-10-02 and the observation cutoffs. observation_end alone does not freeze revisions.",
            "The committed CSVs are the snapshot checked against the October 2, 2026 Employment Situation. This script does not replace them with a later FRED vintage.",
            "PAYEMS and industry CES series are employment levels in thousands.",
            "JOLTS series lag the monthly jobs print; do not treat them as September.",
            "First-print payroll revisions are not in the FRED snapshot and are pinned in 04.",
            "ADP is a private-sector contrast, not the official BLS count.",
            "Dated BLS text is the October 2 archive, not the live empsit.nr0.htm page.",
        ],
    }


def verify_snapshot_dir(raw_dir: Path) -> dict[str, str]:
    """Check recorded hashes before any metadata write, then refresh metadata."""
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
    assert_snapshots_unchanged(before)
    print("Verified committed snapshots against snapshot_sha256. No FRED download. CSVs unchanged.")
    print("Wrote", RAW_DIR / "sources.json")
    for name, stamp in latest.items():
        print(f"  {name}: {stamp}")


def observation_end_for(name: str) -> str:
    return expected_end(name)


def fetch_vintage(fred, series_id: str, observation_end: str) -> pd.Series:
    """Download one series at the October 2 vintage, through one cutoff."""
    series = fred.get_series(
        series_id,
        observation_start=OBS_START,
        observation_end=observation_end,
        realtime_start=ANALYSIS_VINTAGE,
        realtime_end=ANALYSIS_VINTAGE,
    )
    if series.empty:
        raise RuntimeError(
            f"FRED returned no observations for {series_id} "
            f"at vintage {ANALYSIS_VINTAGE} through {observation_end}"
        )
    return series.sort_index()


def refresh_vintage() -> None:
    """Write a side copy of the October 2 vintage. Do not touch the snapshots."""
    before = snapshot_hashes()
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY is required for --refresh. "
            "The default command reproduces the post without a key. "
            "Get a key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    from fredapi import Fred

    REFRESH_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)

    monthly_frames: dict[str, pd.Series] = {}
    latest: dict[str, str] = {}
    for name, series_id in MONTHLY_SERIES.items():
        end = observation_end_for(name)
        print(f"Refreshing {name} ({series_id}) through {end} at {ANALYSIS_VINTAGE}")
        series = fetch_vintage(fred, series_id, end)
        series.index = series.index.to_period("M").to_timestamp()
        series = series.groupby(series.index).last().sort_index()
        monthly_frames[name] = series
        last = last_observation(series)
        if last != end:
            raise RuntimeError(
                f"Refresh of {name} ended at {last}, expected {end}. "
                "The side copy was not accepted."
            )
        latest[name] = last

    monthly = pd.DataFrame(monthly_frames).sort_index()
    monthly.index.name = "date"
    monthly_path = REFRESH_DIR / "fred_monthly.csv"
    monthly.to_csv(monthly_path)

    weekly_frames: dict[str, pd.Series] = {}
    for name, series_id in WEEKLY_SERIES.items():
        end = observation_end_for(name)
        print(f"Refreshing {name} ({series_id}) through {end} at {ANALYSIS_VINTAGE}")
        series = fetch_vintage(fred, series_id, end)
        weekly_frames[name] = series
        last = last_observation(series)
        if last != end:
            raise RuntimeError(
                f"Refresh of {name} ended at {last}, expected {end}. "
                "The side copy was not accepted."
            )
        latest[name] = last

    weekly = pd.DataFrame(weekly_frames).sort_index()
    weekly.index.name = "date"
    weekly_path = REFRESH_DIR / "fred_weekly.csv"
    weekly.to_csv(weekly_path)

    document = source_document(latest, "refresh_side_copy", "data/raw/refresh", before)
    (REFRESH_DIR / "sources.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    assert_snapshots_unchanged(before)
    print("Wrote", monthly_path)
    print("Wrote", weekly_path)
    print("Wrote", REFRESH_DIR / "sources.json")
    print("Committed snapshots were not modified.")
    print("02_clean_data.py still reads data/raw, not data/raw/refresh.")


def _write_fixture_snapshots(directory: Path, historical_payems: float) -> None:
    """Small CSVs with the required columns and October 2 ending dates."""
    directory.mkdir(parents=True, exist_ok=True)
    dates = pd.to_datetime(["2026-07-01", "2026-08-01", "2026-09-01"])
    columns: dict[str, list[object]] = {}
    for name in MONTHLY_SERIES:
        if name in JOLTS_NAMES:
            columns[name] = [1.0, 2.0, pd.NA]
        elif name == "payems":
            columns[name] = [historical_payems, 2.0, 3.0]
        else:
            columns[name] = [1.0, 2.0, 3.0]
    monthly = pd.DataFrame(columns, index=dates)
    monthly.index.name = "date"
    monthly.to_csv(directory / "fred_monthly.csv")
    weekly = pd.DataFrame(
        {"initial_claims": [180000.0, 197000.0]},
        index=pd.to_datetime(["2026-09-19", "2026-09-26"]),
    )
    weekly.index.name = "date"
    weekly.to_csv(directory / "fred_weekly.csv")


def _write_sources(directory: Path, payload: object) -> None:
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2) + "\n"
    (directory / "sources.json").write_text(text, encoding="utf-8")


def _snapshot_bytes(directory: Path) -> dict[str, bytes | None]:
    found: dict[str, bytes | None] = {}
    for name in (*SNAPSHOT_FILES, "sources.json"):
        path = directory / name
        found[name] = path.read_bytes() if path.exists() else None
    return found


def _expect_integrity_failure(directory: Path, before: dict[str, bytes | None], label: str, snippet: str) -> None:
    try:
        verify_snapshot_dir(directory)
    except RuntimeError as exc:
        if snippet not in str(exc):
            raise RuntimeError(f"{label} raised the wrong error: {exc}") from exc
    else:
        raise RuntimeError(f"Integrity check failed: {label} was accepted")
    if _snapshot_bytes(directory) != before:
        raise RuntimeError(f"Integrity check failed: {label} changed the fixture files")


def check_snapshot_integrity() -> None:
    """Temp-dir checks. The committed snapshots are only copied, never modified."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "unchanged"
        _write_fixture_snapshots(raw, 100.0)
        hashes = snapshot_hashes(raw)
        _write_sources(raw, {"snapshot_sha256": hashes, "note": "fixture"})
        before = _snapshot_bytes(raw)
        verify_snapshot_dir(raw)
        after = _snapshot_bytes(raw)
        if after["fred_monthly.csv"] != before["fred_monthly.csv"] or after["fred_weekly.csv"] != before["fred_weekly.csv"]:
            raise RuntimeError("Integrity check failed: a matching snapshot was modified")
        written = json.loads((raw / "sources.json").read_text(encoding="utf-8"))
        if written.get("snapshot_sha256") != hashes:
            raise RuntimeError("Integrity check failed: a matching run replaced snapshot_sha256")

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "altered"
        _write_fixture_snapshots(raw, 100.0)
        _write_sources(raw, {"snapshot_sha256": snapshot_hashes(raw)})
        _write_fixture_snapshots(raw, 101.0)
        before = _snapshot_bytes(raw)
        _expect_integrity_failure(
            raw,
            before,
            "an altered historical payroll value",
            "Refusing to overwrite expected snapshot hashes",
        )

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "wrong-hash"
        _write_fixture_snapshots(raw, 100.0)
        hashes = snapshot_hashes(raw)
        hashes["fred_monthly.csv"] = "0" * 64
        _write_sources(raw, {"snapshot_sha256": hashes})
        before = _snapshot_bytes(raw)
        _expect_integrity_failure(
            raw,
            before,
            "a mismatched expected hash",
            "Refusing to overwrite expected snapshot hashes",
        )

    malformed_payloads = (
        "{",
        "[]",
        json.dumps({"retrieved_for": "no hashes"}),
        json.dumps({"snapshot_sha256": None}),
        json.dumps({"snapshot_sha256": "abc"}),
        json.dumps({"snapshot_sha256": {"fred_weekly.csv": "a" * 64}}),
        json.dumps(
            {
                "snapshot_sha256": {
                    "fred_monthly.csv": "not-a-hash",
                    "fred_weekly.csv": "b" * 64,
                }
            }
        ),
        json.dumps(
            {
                "snapshot_sha256": {
                    "fred_monthly.csv": "g" * 64,
                    "fred_weekly.csv": "a" * 64,
                }
            }
        ),
    )
    for payload in malformed_payloads:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            _write_fixture_snapshots(raw, 100.0)
            _write_sources(raw, payload)
            before = _snapshot_bytes(raw)
            _expect_integrity_failure(
                raw,
                before,
                "malformed expected hashes",
                "Refusing to establish a new snapshot baseline",
            )

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "missing"
        _write_fixture_snapshots(raw, 100.0)
        before = _snapshot_bytes(raw)
        _expect_integrity_failure(
            raw,
            before,
            "a directory with no sources.json",
            "Refusing to establish a new snapshot baseline",
        )

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "real-copy"
        raw.mkdir()
        for name in (*SNAPSHOT_FILES, "sources.json"):
            shutil.copyfile(RAW_DIR / name, raw / name)
        before = _snapshot_bytes(raw)
        verify_snapshot_dir(raw)
        after = _snapshot_bytes(raw)
        if after["fred_monthly.csv"] != before["fred_monthly.csv"] or after["fred_weekly.csv"] != before["fred_weekly.csv"]:
            raise RuntimeError("Integrity check failed: the real snapshot copy was modified")
        written = json.loads(after["sources.json"].decode("utf-8"))
        original = json.loads(before["sources.json"].decode("utf-8"))
        if written.get("snapshot_sha256") != original.get("snapshot_sha256"):
            raise RuntimeError("Integrity check failed: expected hashes for the real snapshot were replaced")

    print(
        "Snapshot integrity check passed: unchanged files match, and missing, "
        "malformed, or altered snapshots raise without writing."
    )


def main() -> None:
    check_snapshot_integrity()
    parser = argparse.ArgumentParser(description="Verify or refresh the October 2, 2026 jobs snapshot.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help=(
            "Refetch the 2026-10-02 vintage into data/raw/refresh/. "
            "Does not replace data/raw/fred_monthly.csv or fred_weekly.csv."
        ),
    )
    args = parser.parse_args()
    if args.refresh:
        refresh_vintage()
    else:
        verify_snapshots()


if __name__ == "__main__":
    main()
