"""Compute every article value from cleaned data and write summary_stats.json."""

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"


def r1(value):
    return round(float(value), 1)


def r2(value):
    return round(float(value), 2)


def main():
    frame = pd.read_csv(
        CLEAN_DIR / "main.csv", index_col="date", parse_dates=True
    )
    fomc = pd.read_csv(
        CLEAN_DIR / "fomc_sep.csv", index_col="date", parse_dates=True
    )
    daily = pd.read_csv(
        POST_DIR / "data" / "raw" / "fred_daily.csv",
        index_col="date",
        parse_dates=True,
    )

    cpi_dates = frame["headline_yoy"].dropna().index
    latest_date = cpi_dates[-1]
    previous_date = cpi_dates[-2]
    latest = frame.loc[latest_date]
    previous = frame.loc[previous_date]

    payroll_dates = frame["payroll_change_k"].dropna().index
    labor_date = payroll_dates[-1]
    labor = frame.loc[labor_date]

    rates_date = daily[["dgs2", "dgs10"]].dropna(how="all").index[-1]
    rates = daily.loc[:rates_date, ["dgs2", "dgs10"]].ffill().iloc[-1]

    target_2026 = fomc.loc[
        fomc.index.year == 2026, "fed_target_median"
    ].dropna().iloc[-1]
    longer_run = fomc["fed_target_longer_run"].dropna().iloc[-1]

    stats = {
        "latest_month": latest_date.strftime("%B %Y"),
        "latest_month_short": latest_date.strftime("%b %Y"),
        "previous_month": previous_date.strftime("%B %Y"),
        "headline_yoy": r1(latest["headline_yoy"]),
        "prev_headline_yoy": r1(previous["headline_yoy"]),
        "headline_mom": r1(latest["headline_mom"]),
        "core_yoy": r1(latest["core_yoy"]),
        "prev_core_yoy": r1(previous["core_yoy"]),
        "core_mom": r1(latest["core_mom"]),
        "energy_yoy": r1(latest["energy_yoy"]),
        "energy_mom": r1(latest["energy_mom"]),
        "gasoline_mom": r1(latest["gasoline_mom"]),
        "shelter_yoy": r1(latest["shelter_yoy"]),
        "shelter_mom": r1(latest["shelter_mom"]),
        "core_goods_yoy": r1(latest["core_goods_yoy"]),
        "median_cpi_yoy": r1(latest["median_cpi_yoy"]),
        "trimmed_mean_cpi_yoy": r1(latest["trimmed_mean_cpi_yoy"]),
        "sticky_ex_shelter_yoy": r1(latest["sticky_ex_shelter_yoy"]),
        "energy_contrib_mom_pp": r2(latest["contrib_energy_mom_pp"]),
        "shelter_contrib_mom_pp": r2(latest["contrib_shelter_mom_pp"]),
        "other_services_contrib_mom_pp": r2(
            latest["contrib_other_services_mom_pp"]
        ),
        "labor_month": labor_date.strftime("%B %Y"),
        "payroll_latest": int(round(labor["payroll_change_k"])),
        "payroll_3mo_avg": int(
            round(frame.loc[:labor_date, "payroll_change_k"].dropna().tail(3).mean())
        ),
        "unrate_latest": r1(labor["unrate"]),
        "fedfunds_latest": r2(labor["fedfunds"]),
        "dgs2_latest": r2(rates["dgs2"]),
        "dgs10_latest": r2(rates["dgs10"]),
        "curve_10y_2y": r2(rates["dgs10"] - rates["dgs2"]),
        "rates_latest_date": rates_date.strftime("%B %d, %Y"),
        "fomc_median_eoy_2026": r1(target_2026),
        "fomc_longer_run": r1(longer_run),
        "data_current_as_of": (
            f"{latest_date.strftime('%B %Y')} CPI and labor data; "
            f"Treasury data through {rates_date.strftime('%B %d, %Y')}"
        ),
        "fred_source_url": "https://fred.stlouisfed.org/",
        "bls_cpi_source_url": "https://www.bls.gov/news.release/cpi.htm",
        "fomc_source_url": (
            "https://www.federalreserve.gov/monetarypolicy/"
            "fomcprojtabl20260617.htm"
        ),
    }

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_DIR / "summary_stats.json", "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
