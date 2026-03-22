"""
02_compute_stats.py
Compute summary statistics for inline values and key metrics cards.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

CLEAN = Path(__file__).resolve().parent.parent / "data" / "clean"
STATS = Path(__file__).resolve().parent.parent / "stats"
STATS.mkdir(parents=True, exist_ok=True)

LATEST = 202605
PRIOR = 202604

# ── National headline numbers ────────────────────────────────────────────────

df_nat = pd.read_csv(CLEAN / "national_index.csv")
# Filter out NaN indicators and source citation rows
df_nat = df_nat[df_nat["indicator"].notna() & ~df_nat["indicator"].str.startswith("Source:", na=False)]
nat_latest = df_nat[df_nat["cycle"] == LATEST].set_index("indicator")["index_value"]
nat_prior = df_nat[df_nat["cycle"] == PRIOR].set_index("indicator")["index_value"]

stats = {
    "release_date": "March 12, 2026",
    "collection_period": "February 23 to March 8, 2026",
    "reference_period": "February 9 to 22, 2026",
    "data_current_as_of": "March 12, 2026 (BTOS cycle 202605)",

    # Current indicators
    "current_performance": float(nat_latest.get("Current performance", np.nan)),
    "revenues": float(nat_latest.get("Revenues", np.nan)),
    "employees": float(nat_latest.get("Employees", np.nan)),
    "hours": float(nat_latest.get("Hours", np.nan)),
    "demand": float(nat_latest.get("Demand", np.nan)),
    "input_prices": float(nat_latest.get("Input prices", np.nan)),
    "output_prices": float(nat_latest.get("Output prices", np.nan)),
    "delivery_time": float(nat_latest.get("Delivery time", np.nan)),

    # Future indicators
    "future_performance": float(nat_latest.get("Future performance", np.nan)),
    "future_employees": float(nat_latest.get("Future employees", np.nan)),
    "future_demand": float(nat_latest.get("Future demand", np.nan)),
    "future_input_prices": float(nat_latest.get("Future input prices", np.nan)),
    "future_output_prices": float(nat_latest.get("Future output prices", np.nan)),

    # Changes from prior cycle
    "current_performance_chg": round(float(nat_latest.get("Current performance", 0) - nat_prior.get("Current performance", 0)), 1),
    "revenues_chg": round(float(nat_latest.get("Revenues", 0) - nat_prior.get("Revenues", 0)), 1),
    "employees_chg": round(float(nat_latest.get("Employees", 0) - nat_prior.get("Employees", 0)), 1),
    "input_prices_chg": round(float(nat_latest.get("Input prices", 0) - nat_prior.get("Input prices", 0)), 1),
    "future_demand_chg": round(float(nat_latest.get("Future demand", 0) - nat_prior.get("Future demand", 0)), 1),
}

# ── Sector highlights ────────────────────────────────────────────────────────

df_sec = pd.read_csv(CLEAN / "sector_index.csv")
df_sec = df_sec[df_sec["indicator"].notna() & ~df_sec["indicator"].str.startswith("Source:", na=False)]
sec_latest = df_sec[df_sec["cycle"] == LATEST].copy()

# Sector with lowest employees index
emp_by_sector = sec_latest[sec_latest["indicator"] == "Employees"].dropna(subset=["index_value"])
if len(emp_by_sector) > 0:
    worst_hiring = emp_by_sector.loc[emp_by_sector["index_value"].idxmin()]
    best_hiring = emp_by_sector.loc[emp_by_sector["index_value"].idxmax()]
    stats["worst_hiring_sector"] = worst_hiring["sector_name"]
    stats["worst_hiring_value"] = float(worst_hiring["index_value"])
    stats["best_hiring_sector"] = best_hiring["sector_name"]
    stats["best_hiring_value"] = float(best_hiring["index_value"])

# Sector with highest input prices
inp_by_sector = sec_latest[sec_latest["indicator"] == "Input prices"].dropna(subset=["index_value"])
if len(inp_by_sector) > 0:
    highest_input = inp_by_sector.loc[inp_by_sector["index_value"].idxmax()]
    stats["highest_input_sector"] = highest_input["sector_name"]
    stats["highest_input_value"] = float(highest_input["index_value"])

# Sector count above/below 50 for employees
stats["sectors_hiring_above_50"] = int((emp_by_sector["index_value"] > 50).sum())
stats["sectors_hiring_below_50"] = int((emp_by_sector["index_value"] < 50).sum())

# ── State highlights ─────────────────────────────────────────────────────────

df_state = pd.read_csv(CLEAN / "state_index.csv")
df_state = df_state[df_state["indicator"].notna() & ~df_state["indicator"].str.startswith("Source:", na=False)]
state_latest = df_state[df_state["cycle"] == LATEST].copy()

emp_by_state = state_latest[state_latest["indicator"] == "Employees"].dropna(subset=["index_value"])
if len(emp_by_state) > 0:
    stats["states_hiring_above_50"] = int((emp_by_state["index_value"] > 50).sum())
    stats["states_hiring_below_50"] = int((emp_by_state["index_value"] < 50).sum())
    weakest_state = emp_by_state.loc[emp_by_state["index_value"].idxmin()]
    strongest_state = emp_by_state.loc[emp_by_state["index_value"].idxmax()]
    stats["weakest_hiring_state"] = weakest_state["state"]
    stats["weakest_hiring_state_value"] = float(weakest_state["index_value"])
    stats["strongest_hiring_state"] = strongest_state["state"]
    stats["strongest_hiring_state_value"] = float(strongest_state["index_value"])

# ── AI adoption (from Response Estimates) ────────────────────────────────────

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
df_resp = pd.read_excel(RAW / "National.xlsx", sheet_name="Response Estimates")
ai_current = df_resp[df_resp["Question"].str.contains("last two weeks.*Artificial Intelligence", na=False, regex=True)]
ai_future = df_resp[df_resp["Question"].str.contains("next six months.*Artificial Intelligence", na=False, regex=True)]

for _, row in ai_current.iterrows():
    val = str(row.get("202605", "")).replace("%", "")
    try:
        val_f = float(val)
    except ValueError:
        continue
    if row["Answer"] == "Yes":
        stats["ai_current_yes"] = val_f

for _, row in ai_future.iterrows():
    val = str(row.get("202605", "")).replace("%", "")
    try:
        val_f = float(val)
    except ValueError:
        continue
    if row["Answer"] == "Yes":
        stats["ai_future_yes"] = val_f

# Next release
stats["next_release_date"] = "March 26, 2026"

# ── Write ────────────────────────────────────────────────────────────────────

with open(STATS / "summary_stats.json", "w") as f:
    json.dump(stats, f, indent=2)

print("Summary stats written to:", STATS / "summary_stats.json")
for k, v in stats.items():
    print(f"  {k}: {v}")
