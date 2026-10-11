"""
01_fetch_data.py
================
STEP 1 of the data pipeline.

What this script does
---------------------
The default command reproduces the September 30, 2026 analysis from the
committed snapshots. It checks data/raw/fred_pce_monthly.csv and
data/raw/fred_gdp_quarterly.csv against snapshot_sha256 in
data/raw/sources.json and exits. A missing, malformed, or mismatched hash
is an error. The script does not create a new baseline, replace the
expected hashes, call FRED, or rewrite those two files.

    python scripts/01_fetch_data.py

An optional historical refetch is separate from reproduction:

    python scripts/01_fetch_data.py --refresh

--refresh requires FRED_API_KEY and writes data/raw/refresh/. It requests
the September 30, 2026 vintage with realtime_start and realtime_end.
An observation end alone does not freeze later revisions. If that vintage
is unavailable, the script stops. It does not fall back to current FRED.
The refresh files are not what 02_clean_data.py reads, and they never
replace the committed snapshots.

The committed CSVs are the release snapshot. This file does not claim that
a September 30 ALFRED request matched them unless sources.json records
alfred_check.matched_committed_snapshot as true after a real comparison.

Pipeline order
--------------
    python scripts/01_fetch_data.py     # verify the committed snapshot
    python scripts/02_clean_data.py     # next: m/m, y/y, annualized rates
    python scripts/04_compute_stats.py  # then: stats JSON for the prose

Friendly name -> FRED series ID
--------------------------------
    pce_price        PCEPI              headline PCE price index
    core_price       PCEPILFE           PCE price index excluding food and energy
    food_price       DFXARG3M086SBEA    food PCE chain-type price index
    energy_price     DNRGRG3M086SBEA    energy goods and services price index
    real_pce         PCEC96             real personal consumption expenditures
    real_dpi         DSPIC96            real disposable personal income
    nominal_pce      PCE                current-dollar PCE (prose only)
    personal_income  PI                 personal income (prose only)
    disposable_pi    DSPI               current-dollar disposable income (prose only)
    saving_rate      PSAVERT            saving as a percent of disposable income
    mich             MICH               Michigan year-ahead inflation (prose, conditional)
    gdp_saar         A191RL1Q225SBEA    real GDP percent change
    pdfp_saar        PB0000031Q225SBEA  real private domestic final sales

manual_priors.json holds the transcribed July release and the GDP
comparison. The default command does not rewrite it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
REFRESH_DIR = RAW_DIR / "refresh"

# Release vintage for an explicit refetch. Both realtime bounds are required.
# observation_end only limits which periods come back.
ANALYSIS_VINTAGE = "2026-09-30"
OBS_START = "2018-01-01"
MONTH_END = "2026-08-01"
QUARTER_END = "2026-04-01"

MONTHLY_SERIES = {
    "pce_price": "PCEPI",
    "core_price": "PCEPILFE",
    "food_price": "DFXARG3M086SBEA",
    "energy_price": "DNRGRG3M086SBEA",
    "real_pce": "PCEC96",
    "real_dpi": "DSPIC96",
    "nominal_pce": "PCE",
    "personal_income": "PI",
    "disposable_pi": "DSPI",
    "saving_rate": "PSAVERT",
    "mich": "MICH",
}

QUARTERLY_SERIES = {
    "gdp_saar": "A191RL1Q225SBEA",
    "pdfp_saar": "PB0000031Q225SBEA",
}

SNAPSHOT_FILES = ("fred_pce_monthly.csv", "fred_gdp_quarterly.csv")
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
            "Expected snapshot_sha256 values must already be recorded."
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


def assert_snapshots_unchanged(before: dict[str, str], directory: Path | None = None) -> None:
    after = snapshot_hashes(directory)
    for name, digest in before.items():
        if after[name] != digest:
            raw_dir = RAW_DIR if directory is None else directory
            raise RuntimeError(
                f"Refusing to leave a changed snapshot: {raw_dir / name}. "
                "Reproduction must keep the verified September 30 files."
            )


def manual_urls() -> dict[str, str]:
    manual_path = RAW_DIR / "manual_priors.json"
    manual = json.loads(manual_path.read_text(encoding="utf-8"))
    return {key: value for key, value in manual.items() if str(key).endswith("_url")}


def source_document(mode: str, output_dir: str, hashes: dict[str, str], alfred_check: object) -> dict:
    return {
        "retrieved_for": "August 2026 Personal Income and Outlays and the Q2 third estimate",
        "analysis_release_date": ANALYSIS_VINTAGE,
        "reproduction_mode": mode,
        "output_dir": output_dir,
        "fred_monthly": MONTHLY_SERIES,
        "fred_quarterly": QUARTERLY_SERIES,
        "manual": manual_urls(),
        "snapshot_sha256": {name: hashes[name] for name in SNAPSHOT_FILES},
        "alfred_check": alfred_check,
        "history_rule": (
            "Reproduction reads the committed CSVs in data/raw. "
            "Those files are the release snapshot for this post. "
            "python scripts/01_fetch_data.py verifies them and does not download. "
            "python scripts/01_fetch_data.py --refresh writes data/raw/refresh/ only, "
            "with realtime_start and realtime_end set to 2026-09-30. "
            "observation_end does not freeze later revisions. "
            "A failed or different vintage request does not replace the snapshot and "
            "does not fall back to current FRED. "
            "alfred_check records a real comparison when one was run. "
            "The pre-update July path and the second-estimate GDP comparison "
            "stay in manual_priors.json."
        ),
    }


def load_alfred_check(sources_path: Path) -> object:
    """Keep a prior comparison record. Do not invent one."""
    if not sources_path.is_file():
        return None
    try:
        document = json.loads(sources_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict):
        return None
    return document.get("alfred_check")


def verify_snapshot_dir(directory: Path) -> None:
    sources_path = directory / "sources.json"
    verified = require_snapshot_hashes(directory, sources_path)
    document = source_document(
        "committed_snapshot",
        "data/raw",
        verified,
        load_alfred_check(sources_path),
    )
    sources_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def verify_snapshots() -> None:
    before = snapshot_hashes()
    manual_before = file_sha256(RAW_DIR / "manual_priors.json")
    verify_snapshot_dir(RAW_DIR)
    assert_snapshots_unchanged(before)
    if file_sha256(RAW_DIR / "manual_priors.json") != manual_before:
        raise RuntimeError("Verify changed manual_priors.json.")
    print("Verified committed snapshots against snapshot_sha256. No FRED download. CSVs unchanged.")


def values_match(refresh_path: Path, committed_path: Path) -> bool:
    """Compare the side copy with the committed snapshot by value, not by CSV text."""
    from pandas.testing import assert_frame_equal

    refreshed = pd.read_csv(refresh_path, index_col="date", parse_dates=True).sort_index()
    committed = pd.read_csv(committed_path, index_col="date", parse_dates=True).sort_index()
    try:
        assert_frame_equal(refreshed, committed, check_exact=False, rtol=0, atol=1e-8)
    except AssertionError:
        return False
    return True


def last_observation(series: pd.Series) -> str:
    observed = series.dropna()
    if observed.empty:
        raise RuntimeError(f"Series has no observations: {series.name}")
    return pd.Timestamp(observed.index.max()).strftime("%Y-%m-%d")


def fetch_vintage(fred, series_id: str, observation_end: str) -> pd.Series:
    """Download one series at the September 30 vintage, through one cutoff."""
    try:
        series = fred.get_series(
            series_id,
            observation_start=OBS_START,
            observation_end=observation_end,
            realtime_start=ANALYSIS_VINTAGE,
            realtime_end=ANALYSIS_VINTAGE,
        )
    except Exception as exc:
        raise RuntimeError(
            f"FRED vintage request failed for {series_id} at {ANALYSIS_VINTAGE}. "
            "No current-vintage fallback was used."
        ) from exc
    if series is None or series.empty:
        raise RuntimeError(
            f"FRED returned no observations for {series_id} "
            f"at vintage {ANALYSIS_VINTAGE} through {observation_end}. "
            "No current-vintage fallback was used."
        )
    return series.sort_index()


def refresh_vintage() -> None:
    """Write a side copy of the September 30 vintage. Do not touch the snapshots."""
    before = snapshot_hashes()
    manual_before = file_sha256(RAW_DIR / "manual_priors.json")
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "FRED_API_KEY is required for --refresh. "
            "The default command reproduces the post without a key."
        )
    from fredapi import Fred

    REFRESH_DIR.mkdir(parents=True, exist_ok=True)
    fred = Fred(api_key=api_key)
    try:
        monthly_frames: dict[str, pd.Series] = {}
        for name, series_id in MONTHLY_SERIES.items():
            print(f"Refreshing {name} ({series_id}) through {MONTH_END} at {ANALYSIS_VINTAGE}")
            series = fetch_vintage(fred, series_id, MONTH_END)
            series.index = series.index.to_period("M").to_timestamp()
            series = series.groupby(series.index).last().sort_index()
            last = last_observation(series)
            if last != MONTH_END:
                raise RuntimeError(
                    f"Refresh of {name} ended at {last}, expected {MONTH_END}. "
                    "The side copy was not accepted, and the committed snapshot was not replaced."
                )
            monthly_frames[name] = series
        monthly = pd.DataFrame(monthly_frames).sort_index()
        monthly.index.name = "date"
        monthly_path = REFRESH_DIR / "fred_pce_monthly.csv"
        monthly.to_csv(monthly_path)

        quarterly_frames: dict[str, pd.Series] = {}
        for name, series_id in QUARTERLY_SERIES.items():
            print(f"Refreshing {name} ({series_id}) through {QUARTER_END} at {ANALYSIS_VINTAGE}")
            series = fetch_vintage(fred, series_id, QUARTER_END)
            series.index = series.index.to_period("Q").to_timestamp()
            series = series.groupby(series.index).last().sort_index()
            last = last_observation(series)
            if last != QUARTER_END:
                raise RuntimeError(
                    f"Refresh of {name} ended at {last}, expected {QUARTER_END}. "
                    "The side copy was not accepted, and the committed snapshot was not replaced."
                )
            quarterly_frames[name] = series
        quarterly = pd.DataFrame(quarterly_frames).sort_index()
        quarterly.index.name = "date"
        quarterly_path = REFRESH_DIR / "fred_gdp_quarterly.csv"
        quarterly.to_csv(quarterly_path)

        refreshed = snapshot_hashes(REFRESH_DIR)
        matched = all(
            values_match(REFRESH_DIR / name, RAW_DIR / name) for name in SNAPSHOT_FILES
        )
        check = {
            "checked_on": "2026-10-10",
            "realtime_start": ANALYSIS_VINTAGE,
            "realtime_end": ANALYSIS_VINTAGE,
            "observation_start": OBS_START,
            "monthly_observation_end": MONTH_END,
            "quarterly_observation_end": QUARTER_END,
            "matched_committed_snapshot": matched,
            "comparison": "values, not CSV bytes",
            "refresh_sha256": refreshed,
        }
        (REFRESH_DIR / "sources.json").write_text(
            json.dumps(
                source_document("refresh_side_copy", "data/raw/refresh", before, check),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # Record the comparison on the committed provenance file without
        # changing the snapshot hashes or the CSVs.
        committed_sources = RAW_DIR / "sources.json"
        document = json.loads(committed_sources.read_text(encoding="utf-8"))
        document["alfred_check"] = check
        document["snapshot_sha256"] = {name: before[name] for name in SNAPSHOT_FILES}
        committed_sources.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print("Refresh matches committed snapshot:", matched)
        print("Wrote", monthly_path)
        print("Wrote", quarterly_path)
        print("02_clean_data.py still reads data/raw, not data/raw/refresh.")
    finally:
        assert_snapshots_unchanged(before)
        if file_sha256(RAW_DIR / "manual_priors.json") != manual_before:
            raise RuntimeError("Refresh changed manual_priors.json.")


def _write_fixture_snapshots(directory: Path, marker: float) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    monthly = pd.DataFrame(
        {"pce_price": [marker, 2.0]},
        index=pd.to_datetime(["2026-07-01", "2026-08-01"]),
    )
    monthly.index.name = "date"
    monthly.to_csv(directory / "fred_pce_monthly.csv")
    quarterly = pd.DataFrame(
        {"gdp_saar": [1.5, 2.2]},
        index=pd.to_datetime(["2026-01-01", "2026-04-01"]),
    )
    quarterly.index.name = "date"
    quarterly.to_csv(directory / "fred_gdp_quarterly.csv")


def _snapshot_bytes(directory: Path) -> dict[str, bytes | None]:
    found: dict[str, bytes | None] = {}
    for name in (*SNAPSHOT_FILES, "sources.json"):
        path = directory / name
        found[name] = path.read_bytes() if path.exists() else None
    return found


def check_snapshot_integrity() -> None:
    """Temp-dir checks. The committed snapshots are not modified here."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "unchanged"
        _write_fixture_snapshots(raw, 100.0)
        hashes = snapshot_hashes(raw)
        (raw / "sources.json").write_text(
            json.dumps({"snapshot_sha256": hashes}) + "\n",
            encoding="utf-8",
        )
        before = _snapshot_bytes(raw)
        verify_snapshot_dir(raw)
        after = _snapshot_bytes(raw)
        if after["fred_pce_monthly.csv"] != before["fred_pce_monthly.csv"]:
            raise RuntimeError("Integrity check failed: a matching snapshot was modified")
        if after["fred_gdp_quarterly.csv"] != before["fred_gdp_quarterly.csv"]:
            raise RuntimeError("Integrity check failed: a matching snapshot was modified")
        written = json.loads((raw / "sources.json").read_text(encoding="utf-8"))
        if written.get("snapshot_sha256") != hashes:
            raise RuntimeError("Integrity check failed: a matching run replaced snapshot_sha256")

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "altered"
        _write_fixture_snapshots(raw, 100.0)
        hashes = snapshot_hashes(raw)
        (raw / "sources.json").write_text(
            json.dumps({"snapshot_sha256": hashes}) + "\n",
            encoding="utf-8",
        )
        _write_fixture_snapshots(raw, 101.0)
        before = _snapshot_bytes(raw)
        try:
            verify_snapshot_dir(raw)
        except RuntimeError as exc:
            if "does not match snapshot_sha256" not in str(exc):
                raise
        else:
            raise RuntimeError("Integrity check failed: an altered snapshot was accepted")
        if _snapshot_bytes(raw) != before:
            raise RuntimeError("Integrity check failed: a mismatch changed the fixture files")

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "missing"
        _write_fixture_snapshots(raw, 100.0)
        before = _snapshot_bytes(raw)
        try:
            verify_snapshot_dir(raw)
        except RuntimeError as exc:
            message = str(exc)
            if "Refusing to establish a new snapshot baseline" not in message or "is missing" not in message:
                raise
        else:
            raise RuntimeError("Integrity check failed: a missing baseline was accepted")
        if _snapshot_bytes(raw) != before:
            raise RuntimeError("Integrity check failed: a missing baseline changed the fixture files")


def main() -> None:
    check_snapshot_integrity()
    parser = argparse.ArgumentParser(
        description="Verify or refresh the September 30, 2026 PCE snapshot."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Write a September 30 vintage side copy under data/raw/refresh/. Does not replace data/raw CSVs.",
    )
    args = parser.parse_args()
    if args.refresh:
        refresh_vintage()
    else:
        verify_snapshots()


if __name__ == "__main__":
    main()
