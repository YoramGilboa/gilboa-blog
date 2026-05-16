"""
04_compute_stats.py
-------------------
Build the compact JSON file used for inline numbers, KPI tiles, and chart
annotations in index.qmd.

April 2026 headline values are copied from the official BLS CPI News Release
dated May 12, 2026. The historical CSV is used for chart continuity.

Run from the post folder after 02_clean_data.py:
    python scripts/04_compute_stats.py
"""

import json
import os

import pandas as pd


IN_PATH = "data/clean/cpi_trends.csv"
OUT_PATH = "stats/summary_stats.json"


def main():
    df = pd.read_csv(IN_PATH, index_col="date", parse_dates=True)

    apr = df.loc["2026-04-01"]
    mar = df.loc["2026-03-01"]

    def r1(val):
        """Round numeric values to one decimal place for public-facing display."""
        return round(float(val), 1)

    stats = {
        "headline_mom": 0.6,
        "headline_yoy": 3.8,
        "prev_headline_mom": r1(mar["headline_mom"]),
        "prev_headline_yoy": 3.3,
        "core_mom": 0.4,
        "core_yoy": 2.8,
        "prev_core_mom": r1(mar["core_mom"]),
        "prev_core_yoy": 2.6,
        "energy_mom": 3.8,
        "energy_yoy": 17.9,
        "prev_energy_mom": 10.9,
        "prev_energy_yoy": 12.5,
        "gasoline_mom": 5.4,
        "gasoline_yoy": 28.4,
        "prev_gasoline_mom": 21.2,
        "prev_gasoline_yoy": 18.9,
        "food_mom": 0.5,
        "food_yoy": 3.2,
        "prev_food_mom": r1(mar["food_mom"]),
        "prev_food_yoy": 2.7,
        "food_at_home_mom": 0.7,
        "food_at_home_yoy": 2.9,
        "food_away_mom": 0.2,
        "food_away_yoy": 3.6,
        "shelter_mom": 0.6,
        "shelter_yoy": 3.3,
        "prev_shelter_mom": r1(mar["shelter_mom"]),
        "prev_shelter_yoy": 3.0,
        "rent_mom": 0.5,
        "owners_equivalent_rent_mom": 0.5,
        "lodging_away_mom": 2.4,
        "services_ex_energy_mom": 0.5,
        "services_ex_energy_yoy": 3.3,
        "transportation_services_mom": 0.3,
        "transportation_services_yoy": 4.3,
        "airline_fares_mom": 2.8,
        "airline_fares_yoy": 20.7,
        "household_furnishings_mom": 0.7,
        "personal_care_mom": 0.7,
        "apparel_mom": 0.6,
        "new_vehicles_mom": -0.2,
        "used_cars_mom": 0.0,
        "medical_care_mom": -0.1,
        "electricity_mom": 2.1,
        "electricity_yoy": 6.1,
        "fuel_oil_mom": 5.8,
        "fuel_oil_yoy": 54.3,
        "natural_gas_mom": -0.1,
        "natural_gas_yoy": 3.0,
        "energy_contribution_share": 40,
        "headline_nsa_mom": 0.9,
        "cpi_u_index_nsa": 333.020,
        "cpi_w_yoy": 3.9,
        "c_cpi_u_yoy": 3.6,
        "real_hourly_earnings_mom": -0.5,
        "real_hourly_earnings_yoy": -0.3,
        "latest_month": "April 2026",
        "previous_month": "March 2026",
        "release_date": "May 12, 2026",
        "data_current_as_of": "April 2026 (BLS release: May 12, 2026)",
        "next_release": "June 10, 2026",
        "source_url": "https://www.bls.gov/news.release/archives/cpi_05122026.htm",
    }

    os.makedirs("stats", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Saved {len(stats)} stats to {OUT_PATH}\n")
    print("Key figures:")
    for key in ["headline_mom", "headline_yoy", "core_mom", "core_yoy", "energy_mom"]:
        print(f"  {key:30s}: {stats[key]:+.1f}")
    print(f"\nLatest chart row: {apr.name.date()} headline YoY {apr['headline_yoy']:.1f}%")


if __name__ == "__main__":
    main()
