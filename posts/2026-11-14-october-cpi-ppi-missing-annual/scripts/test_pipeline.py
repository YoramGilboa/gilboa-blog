import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {name}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


clean = load_script("02_clean_data")
fetch = load_script("01_fetch_data")


class PipelineTests(unittest.TestCase):
    def test_complete_window_matches_endpoint_formula(self):
        series = pd.Series([100.0, 101.0, 102.0, 103.0])
        self.assertAlmostEqual(clean.ann3(series).iloc[-1], ((103 / 100) ** 4 - 1) * 100)

    def test_every_missing_position_invalidates_window(self):
        for position in range(4):
            with self.subTest(position=position):
                series = pd.Series([100.0, 101.0, 102.0, 103.0])
                series.iloc[position] = float("nan")
                self.assertTrue(pd.isna(clean.ann3(series).iloc[-1]))

    def test_actual_gap_and_current_print(self):
        levels = clean.load_levels(clean.RAW_DIR / "fred_cpi_monthly.csv")
        pace = clean.ann3(levels["core_sa"])
        self.assertTrue(pace.loc["2025-10-01":"2026-01-01"].isna().all())
        self.assertAlmostEqual(round(pace.loc["2026-10-01"], 1), 3.7)

    def test_snapshot_verification_preserves_manifest_and_files(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp)
            for name in fetch.SNAPSHOT_FILES:
                (raw / name).write_bytes(b"locked data\n")
            manifest = {"snapshot_sha256": fetch.snapshot_hashes(raw), "provenance": "Keep this note."}
            (raw / "sources.json").write_text(json.dumps(manifest), encoding="utf-8")
            before = {file.name: file.read_bytes() for file in raw.iterdir()}
            with patch.object(fetch, "RAW_DIR", raw):
                fetch.verify_snapshots()
            self.assertEqual(before, {file.name: file.read_bytes() for file in raw.iterdir()})

    def test_changed_snapshot_fails_without_rebaselining(self):
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp)
            for name in fetch.SNAPSHOT_FILES:
                (raw / name).write_bytes(b"locked data\n")
            manifest = json.dumps({"snapshot_sha256": fetch.snapshot_hashes(raw)})
            (raw / "sources.json").write_text(manifest, encoding="utf-8")
            (raw / fetch.SNAPSHOT_FILES[0]).write_bytes(b"changed\n")
            with patch.object(fetch, "RAW_DIR", raw), self.assertRaisesRegex(RuntimeError, "does not match"):
                fetch.verify_snapshots()
            self.assertEqual((raw / "sources.json").read_text(encoding="utf-8"), manifest)


if __name__ == "__main__":
    unittest.main()
