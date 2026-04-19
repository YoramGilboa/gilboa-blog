"""
04_compute_stats.py
-------------------
Build the compact JSON file used for inline numbers, KPI tiles, and chart
annotations in index.qmd.

Why this separate JSON file exists:
    - It keeps narrative numbers in one auditable place.
    - It avoids repeating hard-coded values throughout the post.
    - It lets the Quarto document stay focused on presentation.

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

    # Pull the two months compared throughout the post.
    mar = df.loc["2026-03-01"]
    feb = df.loc["2026-02-01"]

    def r1(val):
        """Round numeric values to one decimal place for public-facing display."""
        return round(float(val), 1)

    stats = {
        # Month-over-month figures come from seasonally adjusted FRED series.
        # Year-over-year figures below use official BLS 12-month changes, which
        # are not seasonally adjusted. This matches the BLS release convention.
        "headline_mom": r1(mar["headline_mom"]),
        "headline_yoy": 3.3,
        "prev_headline_mom": r1(feb["headline_mom"]),
        "prev_headline_yoy": 2.4,

        "core_mom": r1(mar["core_mom"]),
        "core_yoy": 2.6,
        "prev_core_mom": r1(feb["core_mom"]),
        "prev_core_yoy": 2.5,

        "energy_mom": r1(mar["energy_mom"]),
        "energy_yoy": 12.5,
        "prev_energy_mom": r1(feb["energy_mom"]),
        "prev_energy_yoy": 0.5,

        "shelter_mom": r1(mar["shelter_mom"]),
        "shelter_yoy": 3.0,
        "prev_shelter_mom": r1(feb["shelter_mom"]),
        "prev_shelter_yoy": 3.0,

        "food_mom": r1(mar["food_mom"]),
        "food_yoy": 2.7,
        "prev_food_mom": r1(feb["food_mom"]),
        "prev_food_yoy": 3.1,

        # Component detail copied from the official BLS CPI News Release dated
        # April 10, 2026. These values are used in text and component charts.
        "gasoline_mom": 21.2,
        "gasoline_yoy": 18.9,
        "fuel_oil_mom": 30.7,
        "electricity_mom": 0.8,
        "electricity_yoy": 4.6,
        "airline_fares_mom": 2.7,
        "apparel_mom": 1.0,
        "new_vehicles_mom": 0.1,
        "food_at_home_mom": -0.2,
        "medical_care_mom": -0.2,
        "used_cars_mom": -0.4,
        "personal_care_mom": -0.5,

        # Estimated contribution facts for the waterfall chart. These are
        # percentage points of the +0.9pp monthly headline CPI move.
        "gasoline_contribution_pp": 0.68,
        "energy_contribution_pp": 0.71,
        "shelter_contribution_pp": 0.10,
        "gasoline_contribution_pct": 75,

        "latest_month": "March 2026",
        "release_date": "April 10, 2026",
        "data_current_as_of": "March 2026 (BLS release: April 10, 2026)",
        "next_release": "May 12, 2026",
    }

    os.makedirs("stats", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"Saved {len(stats)} stats to {OUT_PATH}\n")
    print("Key figures:")
    key_fields = [
        "headline_mom",
        "headline_yoy",
        "core_mom",
        "core_yoy",
        "energy_mom",
        "energy_yoy",
        "gasoline_mom",
        "shelter_mom",
        "shelter_yoy",
    ]
    for key in key_fields:
        print(f"  {key:30s}: {stats[key]:+.1f}")


if __name__ == "__main__":
    main()
