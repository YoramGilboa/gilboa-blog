"""
Step 3 of 3: freeze the headline numbers used in the post text and cards.

Pipeline order (run from this post folder):
  1. python scripts/01_fetch_data.py
  2. python scripts/02_clean_data.py   # rate definitions live there
  3. python scripts/04_compute_stats.py  <-- you are here

Input:  data/clean/main.csv
Output: stats/summary_stats.json

Why a JSON file?
  The Quarto post never hard-codes economic numbers in the prose. Instead it
  writes things like:
      `{python} fmt(stats['ppi_final_demand_yoy'])`
  so a data refresh only requires re-running this script and re-rendering.

Rounding
  We round display stats once here (one decimal place) so the cards, prose,
  and charts stay consistent. Chart series still use full precision from main.csv.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"


def r1(value: float) -> float:
    """Round to one decimal place for display in cards and prose."""
    return round(float(value), 1)


def main() -> None:
    frame = pd.read_csv(CLEAN_DIR / "main.csv", index_col="date", parse_dates=True)

    # "Latest" = last month with a final-demand y/y value (core release month).
    latest_date = frame["ppi_final_demand_yoy"].dropna().index[-1]
    previous_date = frame.loc[:latest_date, "ppi_final_demand_yoy"].dropna().index[-2]
    latest = frame.loc[latest_date]
    previous = frame.loc[previous_date]

    # Keys must match every stats['...'] reference in index.qmd.
    stats = {
        "latest_month": latest_date.strftime("%B %Y"),
        "latest_month_short": latest_date.strftime("%b %Y"),
        "previous_month": previous_date.strftime("%B %Y"),
        "data_current_as_of": (
            f"{latest_date.strftime('%B %Y')} CPI and PPI observations queried on "
            "July 24, 2026"
        ),
        "fred_source_url": "https://fred.stlouisfed.org/",
        "bls_source_url": "https://www.bls.gov/news.release/ppi.nr0.htm",
        "cpi_source_url": "https://www.bls.gov/news.release/cpi.nr0.htm",
        # Final demand PPI
        "ppi_final_demand_mom": r1(latest["ppi_final_demand_mom"]),
        "ppi_final_demand_yoy": r1(latest["ppi_final_demand_yoy"]),
        "ppi_final_demand_ann3": r1(latest["ppi_final_demand_ann3"]),
        "prev_ppi_final_demand_mom": r1(previous["ppi_final_demand_mom"]),
        # Goods stack
        "ppi_final_demand_goods_mom": r1(latest["ppi_final_demand_goods_mom"]),
        "ppi_final_demand_goods_yoy": r1(latest["ppi_final_demand_goods_yoy"]),
        "ppi_final_demand_goods_ann3": r1(latest["ppi_final_demand_goods_ann3"]),
        "ppi_finished_goods_mom": r1(latest["ppi_finished_goods_mom"]),
        "ppi_finished_goods_yoy": r1(latest["ppi_finished_goods_yoy"]),
        "ppi_finished_goods_ann3": r1(latest["ppi_finished_goods_ann3"]),
        "ppi_energy_mom": r1(latest["ppi_energy_mom"]),
        "ppi_energy_yoy": r1(latest["ppi_energy_yoy"]),
        "ppi_energy_ann3": r1(latest["ppi_energy_ann3"]),
        "ppi_foods_mom": r1(latest["ppi_foods_mom"]),
        "ppi_foods_yoy": r1(latest["ppi_foods_yoy"]),
        "ppi_foods_ann3": r1(latest["ppi_foods_ann3"]),
        "ppi_goods_less_food_energy_mom": r1(latest["ppi_goods_less_food_energy_mom"]),
        "ppi_goods_less_food_energy_yoy": r1(latest["ppi_goods_less_food_energy_yoy"]),
        "ppi_goods_less_food_energy_ann3": r1(latest["ppi_goods_less_food_energy_ann3"]),
        # Fed-watched pipeline (ex food, energy, trade)
        "ppi_less_food_energy_trade_mom": r1(latest["ppi_less_food_energy_trade_mom"]),
        "ppi_less_food_energy_trade_prev_mom": r1(previous["ppi_less_food_energy_trade_mom"]),
        "ppi_less_food_energy_trade_yoy": r1(latest["ppi_less_food_energy_trade_yoy"]),
        "ppi_less_food_energy_trade_ann3": r1(latest["ppi_less_food_energy_trade_ann3"]),
        # Trade services (PPITSS) - prose only in this post
        "ppi_trade_services_mom": r1(latest["ppi_trade_services_mom"]),
        "ppi_trade_services_yoy": r1(latest["ppi_trade_services_yoy"]),
        "ppi_trade_services_ann3": r1(latest["ppi_trade_services_ann3"]),
        # CPI comparators
        "cpi_headline_mom": r1(latest["cpi_headline_mom"]),
        "cpi_headline_yoy": r1(latest["cpi_headline_yoy"]),
        "cpi_core_mom": r1(latest["cpi_core_mom"]),
        "cpi_core_yoy": r1(latest["cpi_core_yoy"]),
        "cpi_energy_mom": r1(latest["cpi_energy_mom"]),
        "cpi_energy_yoy": r1(latest["cpi_energy_yoy"]),
        "cpi_energy_ann3": r1(latest["cpi_energy_ann3"]),
        "cpi_core_goods_mom": r1(latest["cpi_core_goods_mom"]),
        "cpi_core_goods_yoy": r1(latest["cpi_core_goods_yoy"]),
        "cpi_core_goods_ann3": r1(latest["cpi_core_goods_ann3"]),
    }

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_DIR / "summary_stats.json", "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
