"""
04_compute_stats.py
===================
STEP 3 of the data pipeline.

Writes stats/summary_stats.json. The post reads numbers only from that
file. Growth rates that FRED already publishes at one decimal are copied
through. Rates this project calculates use round-half-up.

BLS constant-dollar wages and private health benefits are copied from
data/raw/manual_prints.json. Those prints are labeled MANUAL in that file
and come from the October 30, 2026 Employment Cost Index release:
https://www.bls.gov/news.release/eci.nr0.htm
The September real-spending phrase is the BEA wording, not a rounded zero:
https://www.bea.gov/news/2026/personal-income-and-outlays-september-2026
"""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
RAW_DIR = POST_DIR / "data" / "raw"
STATS_DIR = POST_DIR / "stats"


def round_half_up(value: float, digits: int) -> float:
    quant = Decimal("1").scaleb(-digits)
    number = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    return float(number)


def one(value: float) -> float:
    return round_half_up(float(value), 1)


def two(value: float) -> float:
    return round_half_up(float(value), 2)


def us_date(stamp: pd.Timestamp) -> str:
    return f"{stamp.month}/{stamp.day}/{stamp.year}"


def quarter_label(stamp: pd.Timestamp) -> str:
    quarter = (stamp.month - 1) // 3 + 1
    return f"Q{quarter} {stamp.year}"


def month_label(stamp: pd.Timestamp) -> str:
    return stamp.strftime("%B %Y")


def main() -> None:
    gdp = pd.read_csv(CLEAN_DIR / "gdp_quarterly.csv", index_col="date", parse_dates=True).sort_index()
    pce = pd.read_csv(CLEAN_DIR / "pce_monthly.csv", index_col="date", parse_dates=True).sort_index()
    eci = pd.read_csv(CLEAN_DIR / "eci_quarterly.csv", index_col="date", parse_dates=True).sort_index()
    payems = pd.read_csv(CLEAN_DIR / "labor_payems.csv", index_col="date", parse_dates=True).sort_index()
    claims = pd.read_csv(CLEAN_DIR / "labor_claims.csv", index_col="date", parse_dates=True).sort_index()
    manual = json.loads((RAW_DIR / "manual_prints.json").read_text(encoding="utf-8"))

    latest_q = gdp.index[-1]
    prior_q = gdp.index[-2]
    latest_m = pce.index[-1]
    prior_m = pce.index[-2]
    latest_e = eci.index[-1]

    def q(column: str, row: pd.Timestamp, digits: int = 1) -> float:
        value = float(gdp.loc[row, column])
        return one(value) if digits == 1 else two(value)

    computers = gdp["computers_pp"].dropna()
    prior_max = computers.iloc[:-1].max()
    prior_max_date = computers.iloc[:-1].idxmax()
    price_ann = gdp.loc[gdp.index < "2026-01-01", "computers_price_ann"].dropna()
    negative_share = float((price_ann.loc["1990-01-01":"2025-10-01"] < 0).mean() * 100.0)

    stats = {
        "data_current_as_of": "10/30/2026",
        "release_note": "The GDP advance estimate and the September personal income report were released on 10/29/2026. The Employment Cost Index was released on 10/30/2026.",
        "gdp_release_date": "10/29/2026",
        "pce_release_date": "10/29/2026",
        "eci_release_date": "10/30/2026",
        "payroll_release_date": "10/2/2026",
        "next_gdp_date": "11/25/2026",
        "latest_quarter": quarter_label(latest_q),
        "prior_quarter": quarter_label(prior_q),
        "quarter_span": "July, August, and September 2026",
        "latest_month": month_label(latest_m),
        "prior_month": month_label(prior_m),
        "claims_week": us_date(claims.index[-1]),
        "gdp_saar": q("gdp_saar", latest_q),
        "gdp_saar_prior": q("gdp_saar", prior_q),
        "pdfp_saar": q("pdfp_saar", latest_q),
        "pdfp_saar_prior": q("pdfp_saar", prior_q),
        "final_sales_saar": q("final_sales_saar", latest_q),
        "final_sales_saar_prior": q("final_sales_saar", prior_q),
        "pce_saar": q("pce_saar", latest_q),
        "pce_saar_prior": q("pce_saar", prior_q),
        "equipment_saar": q("equipment_saar", latest_q),
        "equipment_saar_prior": q("equipment_saar", prior_q),
        "ip_saar": q("ip_saar", latest_q),
        "ip_saar_prior": q("ip_saar", prior_q),
        "nonres_saar": q("nonres_saar", latest_q),
        "nonres_saar_prior": q("nonres_saar", prior_q),
        "structures_saar": q("structures_saar", latest_q),
        "residential_saar": q("residential_saar", latest_q),
        "residential_saar_prior": q("residential_saar", prior_q),
        "imports_saar": q("imports_saar", latest_q),
        "imports_saar_prior": q("imports_saar", prior_q),
        "exports_saar": q("exports_saar", latest_q),
        "exports_saar_prior": q("exports_saar", prior_q),
        "government_saar": q("government_saar", latest_q),
        "federal_saar": q("federal_saar", latest_q),
        "defense_saar": q("defense_saar", latest_q),
        "nondefense_saar": q("nondefense_saar", latest_q),
        "info_equip_saar": q("info_equip_saar", latest_q),
        "computers_saar": q("computers_saar", latest_q),
        "real_dpi_saar": q("real_dpi_saar", latest_q),
        "real_dpi_saar_prior": q("real_dpi_saar", prior_q),
        "pce_pp": q("pce_pp", latest_q, 2),
        "pce_pp_prior": q("pce_pp", prior_q, 2),
        "equipment_pp": q("equipment_pp", latest_q, 2),
        "equipment_pp_prior": q("equipment_pp", prior_q, 2),
        "ip_pp": q("ip_pp", latest_q, 2),
        "structures_pp": q("structures_pp", latest_q, 2),
        "residential_pp": q("residential_pp", latest_q, 2),
        "inventories_pp": q("inventories_pp", latest_q, 2),
        "inventories_pp_prior": q("inventories_pp", prior_q, 2),
        "net_exports_pp": q("net_exports_pp", latest_q, 2),
        "net_exports_pp_prior": q("net_exports_pp", prior_q, 2),
        "imports_pp": q("imports_pp", latest_q, 2),
        "imports_pp_prior": q("imports_pp", prior_q, 2),
        "exports_pp": q("exports_pp", latest_q, 2),
        "government_pp": q("government_pp", latest_q, 2),
        "government_pp_prior": q("government_pp", prior_q, 2),
        "federal_pp": q("federal_pp", latest_q, 2),
        "nondefense_pp": q("nondefense_pp", latest_q, 2),
        "computers_pp": q("computers_pp", latest_q, 2),
        "computers_pp_prior": q("computers_pp", prior_q, 2),
        "info_equip_pp": q("info_equip_pp", latest_q, 2),
        "info_equip_pp_prior": q("info_equip_pp", prior_q, 2),
        "software_pp": q("software_pp", latest_q, 2),
        "equipment_ip_pp": two(gdp.loc[latest_q, "equipment_ip_pp"]),
        "contribution_sum": two(
            float(gdp.loc[latest_q, "pce_pp"])
            + float(gdp.loc[latest_q, "equipment_ip_pp"])
            + float(gdp.loc[latest_q, "structures_pp"])
            + float(gdp.loc[latest_q, "residential_pp"])
            + float(gdp.loc[latest_q, "inventories_pp"])
            + float(gdp.loc[latest_q, "net_exports_pp"])
            + float(gdp.loc[latest_q, "government_pp"])
        ),
        "pce_price_ann": one(gdp.loc[latest_q, "pce_price_ann"]),
        "pce_price_ann_prior": one(gdp.loc[prior_q, "pce_price_ann"]),
        "core_price_saar": q("core_price_saar", latest_q),
        "core_price_saar_prior": q("core_price_saar", prior_q),
        "computers_price_ann": one(gdp.loc[latest_q, "computers_price_ann"]),
        "computers_price_ann_prior": one(gdp.loc[prior_q, "computers_price_ann"]),
        "info_price_ann": one(gdp.loc[latest_q, "info_price_ann"]),
        "computers_price_negative_share": one(negative_share),
        "computers_pp_start": quarter_label(computers.index[0]),
        "computers_pp_prior_max": two(float(prior_max)),
        "computers_pp_prior_max_quarter": quarter_label(prior_max_date),
        "computers_pp_is_record": bool(float(computers.iloc[-1]) > float(prior_max)),
        "computers_record_phrase": (
            "larger than every earlier quarter in this series"
            if float(computers.iloc[-1]) > float(prior_max)
            else "inside the range of earlier quarters in this series"
        ),
        "pce_mom": one(pce.loc[latest_m, "pce_mom"]),
        "pce_mom_prior": one(pce.loc[prior_m, "pce_mom"]),
        "pce_yoy": one(pce.loc[latest_m, "pce_yoy"]),
        "pce_yoy_prior": one(pce.loc[prior_m, "pce_yoy"]),
        "pce_mom_hundredths": two(pce.loc[latest_m, "pce_mom"]),
        "pce_dropout_mom_hundredths": two(pce.loc[latest_m - pd.DateOffset(years=1), "pce_mom"]),
        "pce_yoy_hundredths": two(pce.loc[latest_m, "pce_yoy"]),
        "pce_yoy_prior_hundredths": two(pce.loc[prior_m, "pce_yoy"]),
        "core_mom": one(pce.loc[latest_m, "core_mom"]),
        "core_yoy": one(pce.loc[latest_m, "core_yoy"]),
        "core_yoy_prior": one(pce.loc[prior_m, "core_yoy"]),
        "real_pce_mom": one(pce.loc[latest_m, "real_pce_mom"]),
        "real_pce_mom_phrase": manual["real_pce_mom_phrase"],
        "real_pce_dollar": one(pce.loc[latest_m, "real_pce_dollar"]),
        "real_dpi_mom": one(pce.loc[latest_m, "real_dpi_mom"]),
        "saving_rate": one(pce.loc[latest_m, "saving"]),
        "saving_rate_prior": one(pce.loc[prior_m, "saving"]),
        "income_mom": one(pce.loc[latest_m, "income_mom"]),
        "dpi_mom": one(pce.loc[latest_m, "dpi_mom"]),
        "nominal_pce_mom": one(pce.loc[latest_m, "nominal_pce_mom"]),
        "income_dollar": one(pce.loc[latest_m, "income_dollar"]),
        "dpi_dollar": one(pce.loc[latest_m, "dpi_dollar"]),
        "nominal_pce_dollar": one(pce.loc[latest_m, "nominal_pce_dollar"]),
        "eci_comp_qoq": one(eci.loc[latest_e, "comp_qoq"]),
        "eci_wages_qoq": one(eci.loc[latest_e, "wages_qoq"]),
        "eci_benefits_qoq": one(eci.loc[latest_e, "benefits_qoq"]),
        "eci_comp_yoy": one(eci.loc[latest_e, "comp_yoy"]),
        "eci_wages_yoy": one(eci.loc[latest_e, "wages_yoy"]),
        "eci_benefits_yoy": one(eci.loc[latest_e, "benefits_yoy"]),
        "eci_wages_real_yoy": one(manual["eci_wages_real_private_yoy"]),
        "eci_private_health_yoy": one(manual["eci_private_health_yoy"]),
        "wage_minus_pce": one(eci.loc[latest_e, "wage_minus_pce"]),
        "jolts_date": manual["jolts_date"],
        "jobs_date": manual["jobs_date"],
        "cpi_date": manual["cpi_date"],
        "ppi_date": manual["ppi_date"],
        "payroll_change": int(round_half_up(float(payems["payems_change"].iloc[-1]), 0)),
        "claims_latest": int(round_half_up(float(claims["initial_claims"].iloc[-1]), 0)),
    }

    required_locks = {
        "gdp_saar": 3.4,
        "pdfp_saar": 4.9,
        "equipment_saar": 20.9,
        "computers_pp": 0.72,
        "info_equip_pp": 0.86,
        "imports_saar": 19.7,
        "net_exports_pp": -3.32,
        "inventories_pp": 1.61,
        "saving_rate": 3.8,
        "pce_yoy": 3.6,
        "core_yoy": 3.1,
        "payroll_change": 29,
        "claims_latest": 194000,
        "eci_comp_qoq": 0.8,
        "eci_wages_yoy": 3.1,
        "pce_price_ann": 2.1,
    }
    for key, expected in required_locks.items():
        if stats[key] != expected:
            raise RuntimeError(f"{key} is {stats[key]}, expected {expected}.")

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    (STATS_DIR / "summary_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(stats)} stats keys.")


if __name__ == "__main__":
    main()
