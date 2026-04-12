"""
02_clean_data.py
Reads raw BLS JSON files from data/raw/, cleans and computes derived series,
and writes clean CSVs to data/clean/.

Outputs:
  data/clean/payrolls.csv         - monthly payroll change, 3-month MA, consensus flag
  data/clean/unemployment.csv     - unemployment rate, LFPR, employment-population ratio
  data/clean/sector_contributions.csv - March 2026 sector breakdown (manually entered
                                        from BLS Employment Situation Table B-1)

Run from the post folder:
    python scripts/02_clean_data.py
"""

import json
import os
import pandas as pd

RAW_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
CLEAN_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "clean")
os.makedirs(CLEAN_DIR, exist_ok=True)

MONTH_MAP = {
    "January": "01", "February": "02", "March": "03", "April": "04",
    "May": "05", "June": "06", "July": "07", "August": "08",
    "September": "09", "October": "10", "November": "11", "December": "12",
}


def load_bls_json(name: str) -> pd.DataFrame:
    path = os.path.join(RAW_DIR, f"{name}.json")
    with open(path) as f:
        data = json.load(f)
    rows = []
    for obs in data["data"]:
        month_str = MONTH_MAP.get(obs["periodName"])
        if month_str is None:
            continue
        rows.append({
            "date": pd.Timestamp(f"{obs['year']}-{month_str}-01"),
            "value": float(obs["value"].replace(",", "")),
        })
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df


def build_payrolls():
    """Compute monthly payroll change from levels, add 3-month MA and consensus."""
    df = load_bls_json("payrolls")
    df = df.rename(columns={"value": "level"})
    df["payroll_change"] = df["level"].diff() * 1000   # BLS reports in thousands
    df = df.dropna(subset=["payroll_change"]).copy()
    df["payroll_change"] = df["payroll_change"].astype(int)
    df["payroll_change_3mma"] = df["payroll_change"].rolling(3).mean()

    # Mark revised months per BLS release
    df["is_revised"] = df["date"].isin([
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-02-01"),
    ])

    # Consensus estimate for March 2026 (Bloomberg/FactSet median)
    df["consensus"] = None
    df.loc[df["date"] == pd.Timestamp("2026-03-01"), "consensus"] = 59000

    df = df[["date", "payroll_change", "payroll_change_3mma", "is_revised", "consensus"]]
    df.to_csv(os.path.join(CLEAN_DIR, "payrolls.csv"), index=False)
    print(f"  payrolls.csv: {len(df)} rows")


def build_unemployment():
    """Merge unemployment rate, LFPR, and employment-population ratio."""
    urate = load_bls_json("unemployment_rate").rename(columns={"value": "unemployment_rate"})
    lfpr  = load_bls_json("lfpr").rename(columns={"value": "lfpr"})
    emp   = load_bls_json("emp_pop_ratio").rename(columns={"value": "emp_pop_ratio"})

    df = urate.merge(lfpr, on="date", how="outer").merge(emp, on="date", how="outer")
    df = df.sort_values("date").reset_index(drop=True)
    df.to_csv(os.path.join(CLEAN_DIR, "unemployment.csv"), index=False)
    print(f"  unemployment.csv: {len(df)} rows")


def build_sector_contributions():
    """
    Sector contributions for March 2026.
    Source: BLS Employment Situation Table B-1, April 3, 2026 release.
    These figures are entered manually from the published tables.
    """
    rows = [
        ("Health care",                    76000,  "positive"),
        ("Construction",                   26000,  "positive"),
        ("Transportation & warehousing",   21000,  "positive"),
        ("Social assistance",              14000,  "positive"),
        ("Retail trade",                    8000,  "positive"),
        ("Professional & business services", 6000, "positive"),
        ("Financial activities",            4000,  "positive"),
        ("Leisure & hospitality",          -2000,  "negative"),
        ("Information",                    -3000,  "negative"),
        ("Manufacturing",                  -7000,  "negative"),
        ("Federal government",            -11000,  "negative"),
    ]
    df = pd.DataFrame(rows, columns=["sector", "change", "category"])
    df.to_csv(os.path.join(CLEAN_DIR, "sector_contributions.csv"), index=False)
    print(f"  sector_contributions.csv: {len(df)} rows")


def main():
    print("Cleaning BLS data...")
    build_payrolls()
    build_unemployment()
    build_sector_contributions()
    print("Done.")


if __name__ == "__main__":
    main()
