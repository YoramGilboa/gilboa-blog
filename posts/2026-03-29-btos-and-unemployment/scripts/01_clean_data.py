"""
01_clean_data.py
Read raw BTOS XLSX files and unemployment claims CSVs, output clean CSVs.
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
CLEAN = Path(__file__).resolve().parent.parent / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

LATEST_CYCLE = "202606"

# ── Helpers ──────────────────────────────────────────────────────────────────

def read_index_sheet(filepath: Path) -> pd.DataFrame:
    """Read the 'Index Estimates' sheet, melt time columns into long format."""
    df = pd.read_excel(filepath, sheet_name="Index Estimates")
    # Identify time columns (format YYYYWW, all numeric column names)
    id_cols = [c for c in df.columns if not str(c).isdigit()]
    time_cols = [c for c in df.columns if str(c).isdigit()]
    df_long = df.melt(id_vars=id_cols, value_vars=time_cols,
                      var_name="cycle", value_name="index_value")
    df_long["cycle"] = df_long["cycle"].astype(str)
    # Convert suppressed / missing to NaN
    df_long["index_value"] = pd.to_numeric(df_long["index_value"], errors="coerce")
    return df_long


def read_collection_dates(filepath: Path) -> pd.DataFrame:
    """Read cycle-to-date mapping."""
    df = pd.read_excel(filepath, sheet_name="Collection and Reference Dates")
    return df


# ── National ─────────────────────────────────────────────────────────────────

print("Processing National.xlsx...")
df_nat = read_index_sheet(RAW / "BTOS" / "National.xlsx")
df_nat.rename(columns={"Option Text": "indicator"}, inplace=True)
df_nat.to_csv(CLEAN / "national_index.csv", index=False)

# Also read collection dates for reference
df_dates = read_collection_dates(RAW / "BTOS" / "National.xlsx")
df_dates.to_csv(CLEAN / "collection_dates.csv", index=False)

print(f"  National: {len(df_nat)} rows, {df_nat['indicator'].nunique()} indicators")


# ── Sector ───────────────────────────────────────────────────────────────────

print("Processing Sector.xlsx...")
df_sec = read_index_sheet(RAW / "BTOS" / "Sector.xlsx")
df_sec.rename(columns={"Option Text": "indicator", "Sector": "sector"}, inplace=True)

# Build sector name lookup from the raw codes
SECTOR_NAMES = {
    "11": "Agriculture",
    "21": "Mining & Oil/Gas",
    "22": "Utilities",
    "23": "Construction",
    "31": "Manufacturing",
    "42": "Wholesale Trade",
    "44": "Retail Trade",
    "48": "Transport & Warehousing",
    "51": "Information",
    "52": "Finance & Insurance",
    "53": "Real Estate",
    "54": "Professional Services",
    "55": "Management",
    "56": "Admin & Waste Mgmt",
    "61": "Education",
    "62": "Health Care",
    "71": "Arts & Entertainment",
    "72": "Accommodation & Food",
    "81": "Other Services",
    "XX": "Multi-sector",
}

# Extract the 2-digit code from the sector column
df_sec["sector_code"] = df_sec["sector"].astype(str).str.extract(r"^(\d{2}|XX)")
df_sec["sector_name"] = df_sec["sector_code"].map(SECTOR_NAMES)
df_sec.to_csv(CLEAN / "sector_index.csv", index=False)

print(f"  Sector: {len(df_sec)} rows, {df_sec['sector_code'].nunique()} sectors")


# ── State ────────────────────────────────────────────────────────────────────

print("Processing State.xlsx...")
df_state = read_index_sheet(RAW / "BTOS" / "State.xlsx")
df_state.rename(columns={"Option Text": "indicator", "State": "state"}, inplace=True)
# Exclude XX (multi-state) and PR (Puerto Rico) for main analysis
df_state = df_state[~df_state["state"].isin(["XX", "PR"])].copy()
df_state.to_csv(CLEAN / "state_index.csv", index=False)

print(f"  State: {len(df_state)} rows, {df_state['state'].nunique()} states")


# ── Top 25 MSA ───────────────────────────────────────────────────────────────

print("Processing Top 25 MSA.xlsx...")
df_msa = read_index_sheet(RAW / "BTOS" / "Top 25 MSA.xlsx")
df_msa.rename(columns={"Option Text": "indicator", "MSA": "msa"}, inplace=True)
df_msa.to_csv(CLEAN / "msa_index.csv", index=False)

print(f"  MSA: {len(df_msa)} rows, {df_msa['msa'].nunique()} MSAs")


# ── Unemployment Claims ─────────────────────────────────────────────────────

print("Processing ICSA.csv (initial claims)...")
df_icsa = pd.read_csv(RAW / "ICSA.csv", parse_dates=["observation_date"])
df_icsa.rename(columns={"observation_date": "date", "ICSA": "initial_claims"}, inplace=True)
df_icsa["initial_claims"] = pd.to_numeric(df_icsa["initial_claims"], errors="coerce")
df_icsa = df_icsa.sort_values("date").reset_index(drop=True)
# Compute 4-week moving average
df_icsa["initial_claims_4wma"] = df_icsa["initial_claims"].rolling(4).mean()
df_icsa.to_csv(CLEAN / "initial_claims.csv", index=False)
print(f"  Initial claims: {len(df_icsa)} rows, {df_icsa['date'].min()} to {df_icsa['date'].max()}")

print("Processing CCSA.csv (continuing claims)...")
df_ccsa = pd.read_csv(RAW / "CCSA.csv", parse_dates=["observation_date"])
df_ccsa.rename(columns={"observation_date": "date", "CCSA": "continuing_claims"}, inplace=True)
df_ccsa["continuing_claims"] = pd.to_numeric(df_ccsa["continuing_claims"], errors="coerce")
df_ccsa = df_ccsa.sort_values("date").reset_index(drop=True)
# Compute 4-week moving average
df_ccsa["continuing_claims_4wma"] = df_ccsa["continuing_claims"].rolling(4).mean()
df_ccsa.to_csv(CLEAN / "continuing_claims.csv", index=False)
print(f"  Continuing claims: {len(df_ccsa)} rows, {df_ccsa['date'].min()} to {df_ccsa['date'].max()}")


print("\nDone. Clean CSVs written to:", CLEAN)
