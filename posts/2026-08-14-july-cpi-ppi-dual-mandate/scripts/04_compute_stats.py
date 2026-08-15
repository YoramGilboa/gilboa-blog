"""Compute the summary values used in the July CPI/PPI post prose and cards."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"


def r1(value: float) -> float:
    return round(float(value), 1)


def r0(value: float) -> float:
    return round(float(value), 0)


def main() -> None:
    frame = pd.read_csv(CLEAN_DIR / "main.csv", index_col="date", parse_dates=True)
    latest_date = frame["cpi_headline_release_yoy"].dropna().index[-1]
    previous_date = frame.loc[:latest_date, "cpi_headline_release_yoy"].dropna().index[-2]

    latest = frame.loc[latest_date]
    previous = frame.loc[previous_date]

    # MANUAL: July 2026 PPI monthly component values from the BLS release.
    # Source: https://www.bls.gov/news.release/ppi.nr0.htm
    ppi_final_demand_mom = 0.0
    ppi_final_demand_goods_mom = -0.7
    ppi_final_demand_services_mom = 0.2
    ppi_less_food_energy_trade_mom = 0.4
    ppi_energy_mom = -3.1

    # MANUAL: July 2026 motor-vehicle-insurance CPI month-over-month change.
    # Source: https://www.bls.gov/news.release/cpi.nr0.htm
    motor_vehicle_insurance_mom = -0.3

    stats = {
        "latest_month": latest_date.strftime("%B %Y"),
        "latest_month_short": latest_date.strftime("%b %Y"),
        "previous_month": previous_date.strftime("%B %Y"),
        "data_current_as_of": "08/14/2026",
        "cpi_release_date": "08/12/2026",
        "ppi_release_date": "08/13/2026",
        "jobs_post_date": "2026-08-07",
        "next_ppi_date": "09/10/2026",
        "next_cpi_date": "09/11/2026",
        "next_jobs_date": "09/04/2026",
        "next_fomc_dates": "09/15/2026-09/16/2026",
        "jackson_hole_timing": "late August 2026",
        "cpi_headline_mom": r1(latest["cpi_headline_mom"]),
        "cpi_headline_yoy": r1(latest["cpi_headline_release_yoy"]),
        "cpi_headline_prev_yoy": r1(previous["cpi_headline_release_yoy"]),
        "cpi_core_mom": r1(latest["cpi_core_mom"]),
        "cpi_core_yoy": r1(latest["cpi_core_release_yoy"]),
        "cpi_core_prev_yoy": r1(previous["cpi_core_release_yoy"]),
        "cpi_energy_mom": r1(latest["cpi_energy_mom"]),
        "cpi_energy_yoy": r1(latest["cpi_energy_yoy"]),
        "cpi_food_mom": r1(latest["cpi_food_mom"]),
        "cpi_food_yoy": r1(latest["cpi_food_yoy"]),
        "cpi_shelter_mom": r1(latest["cpi_shelter_mom"]),
        "cpi_shelter_yoy": r1(latest["cpi_shelter_yoy"]),
        "cpi_core_goods_mom": r1(latest["cpi_core_goods_mom"]),
        "cpi_core_goods_yoy": r1(latest["cpi_core_goods_yoy"]),
        "cpi_medical_services_mom": r1(latest["cpi_medical_services_mom"]),
        "cpi_medical_services_yoy": r1(latest["cpi_medical_services_yoy"]),
        "contrib_energy_mom_pp": r1(latest["contrib_energy_mom_pp"]),
        "contrib_food_mom_pp": r1(latest["contrib_food_mom_pp"]),
        "contrib_core_goods_mom_pp": r1(latest["contrib_core_goods_mom_pp"]),
        "contrib_shelter_mom_pp": r1(latest["contrib_shelter_mom_pp"]),
        "contrib_other_services_mom_pp": r1(latest["contrib_other_services_mom_pp"]),
        "ppi_final_demand_mom": ppi_final_demand_mom,
        "ppi_final_demand_yoy": r1(latest["ppi_final_demand_yoy"]),
        "ppi_final_demand_prev_yoy": r1(previous["ppi_final_demand_yoy"]),
        "ppi_final_demand_goods_mom": ppi_final_demand_goods_mom,
        "ppi_final_demand_goods_yoy": r1(latest["ppi_final_demand_goods_yoy"]),
        "ppi_final_demand_services_mom": ppi_final_demand_services_mom,
        "ppi_final_demand_services_yoy": r1(latest["ppi_final_demand_services_yoy"]),
        "ppi_less_food_energy_trade_mom": ppi_less_food_energy_trade_mom,
        "ppi_less_food_energy_trade_yoy": r1(latest["ppi_less_food_energy_trade_yoy"]),
        "ppi_energy_mom": ppi_energy_mom,
        "ppi_energy_yoy": r1(latest["ppi_energy_yoy"]),
        "real_ahe_yoy": r1(latest["real_ahe_yoy"]),
        "real_ahe_prev_yoy": r1(previous["real_ahe_yoy"]),
        "nominal_ahe_yoy": r1(latest["ahe_total_private_yoy"]),
        "nominal_ahe_prev_yoy": r1(previous["ahe_total_private_yoy"]),
        "july_payroll_k": r0(latest["payroll_change_k"]),
        "payroll_three_month_avg_k": r0(latest["payroll_three_month_avg_k"]),
        "unrate": r1(latest["unrate"]),
        "civpart": r1(latest["civpart"]),
        "fed_target_upper": r1(frame["fed_target_upper"].dropna().iloc[-1]),
        "fed_target_lower": r1(frame["fed_target_lower"].dropna().iloc[-1]),
        "motor_vehicle_insurance_mom": motor_vehicle_insurance_mom,
    }

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_DIR / "summary_stats.json", "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()