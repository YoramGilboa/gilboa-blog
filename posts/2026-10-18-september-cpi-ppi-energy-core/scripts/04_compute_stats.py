"""
04_compute_stats.py
===================
STEP 3 of the data pipeline.

What this script does
---------------------
Reads the cleaned rates and writes stats/summary_stats.json. The Quarto post
reads numbers only from that file.

Rounding
--------
One-decimal keys use round-half-up, matching the published BLS tenths.
Hundredths keys are the year-rate arithmetic. They are not a second rounding
of the one-decimal prints.

# MANUAL: PPI gasoline and the retail-fuel margin are single lines in the
# October 15, 2026 PPI news release. They are not FRED series in this post.
# https://www.bls.gov/news.release/archives/ppi_10152026.htm
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
SEP = pd.Timestamp("2026-09-01")
AUG = pd.Timestamp("2026-08-01")
JUL = pd.Timestamp("2026-07-01")
PRIOR_YEAR = pd.Timestamp("2025-09-01")
WINDOW_START = pd.Timestamp("2026-01-01")


def rh(value: float, places: str) -> float:
    """Round half away from zero and return a JSON number."""
    return float(Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP))


def month_name(stamp: pd.Timestamp) -> str:
    return f"{stamp.strftime('%B')} {stamp.year}"


def extreme(series: pd.Series, how: str) -> tuple[float, pd.Timestamp]:
    window = series.loc[WINDOW_START:AUG].dropna()
    if window.empty:
        raise RuntimeError("The January-to-August 2026 window is empty.")
    stamp = window.idxmin() if how == "min" else window.idxmax()
    return float(window.loc[stamp]), pd.Timestamp(stamp)


def main() -> None:
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    cpi = pd.read_csv(CLEAN_DIR / "cpi_monthly.csv", index_col="date", parse_dates=True)
    ppi = pd.read_csv(CLEAN_DIR / "ppi_monthly.csv", index_col="date", parse_dates=True)
    contributions = pd.read_csv(CLEAN_DIR / "contributions_september.csv")
    manual = pd.read_csv(RAW_DIR / "bls_ppi_manual_prints.csv").set_index("key")["value"]
    funds = pd.read_csv(RAW_DIR / "fred_funds_daily.csv", index_col="date", parse_dates=True)
    funds = funds.loc[: pd.Timestamp("2026-10-17")].dropna(how="any")
    if funds.empty:
        raise RuntimeError("No federal funds target is available through 10/17/2026.")

    def effect(component: str) -> float:
        row = contributions.loc[contributions["component"] == component, "effect_pp"]
        return float(row.iloc[0])

    headline_yoy_now = float(cpi.loc[SEP, "headline_yoy"])
    headline_yoy_prior = float(cpi.loc[AUG, "headline_yoy"])
    core_yoy_now = float(cpi.loc[SEP, "core_yoy"])
    core_yoy_prior = float(cpi.loc[AUG, "core_yoy"])
    headline_nsa_now = float(cpi.loc[SEP, "headline_nsa_mom"])
    headline_nsa_drop = float(cpi.loc[PRIOR_YEAR, "headline_nsa_mom"])
    core_nsa_now = float(cpi.loc[SEP, "core_nsa_mom"])
    core_nsa_drop = float(cpi.loc[PRIOR_YEAR, "core_nsa_mom"])

    fd_mom = ppi["ppi_fd_mom"].dropna()
    earlier_fd = fd_mom.loc[:AUG]
    fd_hit = earlier_fd[earlier_fd.map(lambda value: rh(value, "0.1")) >= 1.3]
    if fd_hit.empty or pd.Timestamp(fd_hit.index[-1]) != pd.Timestamp("2022-03-01"):
        raise RuntimeError("PPI final-demand month is not the largest since March 2022.")
    fd_yoy = ppi["ppi_fd_yoy"].dropna()
    earlier_yoy = fd_yoy.loc[:AUG]
    yoy_hit = earlier_yoy[earlier_yoy.map(lambda value: rh(value, "0.1")) >= 6.3]
    if yoy_hit.empty or pd.Timestamp(yoy_hit.index[-1]) != pd.Timestamp("2022-12-01"):
        raise RuntimeError("PPI final-demand year rate is not the largest since December 2022.")

    core_low, core_low_month = extreme(cpi["core_yoy"], "min")
    core_high, core_high_month = extreme(cpi["core_yoy"], "max")
    services_low, services_low_month = extreme(cpi["services_yoy"], "min")
    services_high, services_high_month = extreme(cpi["services_yoy"], "max")
    gasoline_effect = effect("gasoline")
    headline_print = 0.6
    plotted = contributions[contributions["plot"] == 1]

    levels = pd.read_csv(RAW_DIR / "fred_cpi_monthly.csv", index_col="date", parse_dates=True)
    gap_rows = levels.loc["2021-01-01":SEP, ["headline_sa", "core_sa", "energy_sa"]]
    gap_months = sorted(
        {
            stamp.strftime("%Y-%m")
            for stamp, row in gap_rows.iterrows()
            if row.isna().any()
        }
    )

    stats = {
        "latest_month": month_name(SEP),
        "prior_month": month_name(AUG),
        "july_month": month_name(JUL),
        "window_start_month": month_name(WINDOW_START),
        "dropout_month": month_name(PRIOR_YEAR),
        "data_current_as_of": "10/15/2026",
        "release_note": "Figures use the CPI vintage of 10/14/2026 and the PPI vintage of 10/15/2026.",
        "cpi_release_date": "10/14/2026",
        "ppi_release_date": "10/15/2026",
        "fomc_statement_date": "10/28/2026",
        "fomc_statement_time": "2:00 p.m. ET",
        "fomc_has_sep": False,
        "pce_gdp_date": "10/29/2026",
        "next_cpi_date": "11/10/2026",
        "next_cpi_time": "8:30 a.m. ET",
        "fred_gap_months": ", ".join(gap_months) if gap_months else "none",
        "chart_end_month": month_name(SEP),
        "headline_mom": rh(cpi.loc[SEP, "headline_mom"], "0.1"),
        "headline_yoy": rh(headline_yoy_now, "0.1"),
        "headline_mom_prior": rh(cpi.loc[AUG, "headline_mom"], "0.1"),
        "headline_yoy_prior": rh(headline_yoy_prior, "0.1"),
        "core_mom": rh(cpi.loc[SEP, "core_mom"], "0.1"),
        "core_yoy": rh(core_yoy_now, "0.1"),
        "core_mom_prior": rh(cpi.loc[AUG, "core_mom"], "0.1"),
        "core_yoy_prior": rh(core_yoy_prior, "0.1"),
        "gasoline_mom": rh(cpi.loc[SEP, "gasoline_mom"], "0.1"),
        "gasoline_nsa_mom": rh(cpi.loc[SEP, "gasoline_nsa_mom"], "0.1"),
        "gasoline_yoy": rh(cpi.loc[SEP, "gasoline_yoy"], "0.1"),
        "energy_mom": rh(cpi.loc[SEP, "energy_mom"], "0.1"),
        "energy_mom_prior": rh(cpi.loc[AUG, "energy_mom"], "0.1"),
        "energy_yoy": rh(cpi.loc[SEP, "energy_yoy"], "0.1"),
        "food_mom": rh(cpi.loc[SEP, "food_mom"], "0.1"),
        "food_yoy": rh(cpi.loc[SEP, "food_yoy"], "0.1"),
        "shelter_mom": rh(cpi.loc[SEP, "shelter_mom"], "0.1"),
        "shelter_mom_prior": rh(cpi.loc[AUG, "shelter_mom"], "0.1"),
        "shelter_yoy": rh(cpi.loc[SEP, "shelter_yoy"], "0.1"),
        "headline_yoy_hundredths": rh(headline_yoy_now, "0.01"),
        "headline_yoy_prior_hundredths": rh(headline_yoy_prior, "0.01"),
        "headline_yoy_change_pp": rh(headline_yoy_now - headline_yoy_prior, "0.01"),
        "headline_mom_hundredths": rh(headline_nsa_now, "0.01"),
        "headline_dropout_mom_hundredths": rh(headline_nsa_drop, "0.01"),
        "headline_dropout_sa_mom": rh(float(cpi.loc[PRIOR_YEAR, "headline_mom"]), "0.1"),
        "core_yoy_hundredths": rh(core_yoy_now, "0.01"),
        "core_yoy_prior_hundredths": rh(core_yoy_prior, "0.01"),
        "core_yoy_change_pp": rh(core_yoy_now - core_yoy_prior, "0.01"),
        "core_mom_hundredths": rh(core_nsa_now, "0.01"),
        "core_dropout_mom_hundredths": rh(core_nsa_drop, "0.01"),
        "ppi_fd_mom": rh(ppi.loc[SEP, "ppi_fd_mom"], "0.1"),
        "ppi_fd_yoy": rh(ppi.loc[SEP, "ppi_fd_yoy"], "0.1"),
        "ppi_fd_mom_prior": rh(ppi.loc[AUG, "ppi_fd_mom"], "0.1"),
        "ppi_fd_mom_july": rh(ppi.loc[JUL, "ppi_fd_mom"], "0.1"),
        "ppi_fd_largest_since_mom": rh(float(fd_hit.iloc[-1]), "0.1"),
        "ppi_fd_largest_since_month": month_name(pd.Timestamp(fd_hit.index[-1])),
        "ppi_fd_largest_since_yoy": rh(float(yoy_hit.iloc[-1]), "0.1"),
        "ppi_fd_largest_since_yoy_month": month_name(pd.Timestamp(yoy_hit.index[-1])),
        "ppi_goods_mom": rh(ppi.loc[SEP, "ppi_goods_mom"], "0.1"),
        "ppi_services_mom": rh(ppi.loc[SEP, "ppi_services_mom"], "0.1"),
        "ppi_energy_mom": rh(ppi.loc[SEP, "ppi_energy_mom"], "0.1"),
        "ppi_foods_mom": rh(ppi.loc[SEP, "ppi_foods_mom"], "0.1"),
        "ppi_core_goods_mom": rh(ppi.loc[SEP, "ppi_core_goods_mom"], "0.1"),
        "ppi_gasoline_mom": rh(float(manual["ppi_gasoline_mom"]), "0.1"),
        "ppi_xfood_energy_trade_mom": rh(ppi.loc[SEP, "ppi_x_mom"], "0.1"),
        "ppi_xfood_energy_trade_mom_prior": rh(ppi.loc[AUG, "ppi_x_mom"], "0.1"),
        "ppi_xfood_energy_trade_yoy": rh(ppi.loc[SEP, "ppi_x_yoy"], "0.1"),
        "ppi_fuels_retailing_margin_mom": rh(float(manual["ppi_fuels_retailing_margin_mom"]), "0.1"),
        "ppi_energy_share_phrase": "over 80%",
        "ppi_gasoline_share_phrase": "half",
        "ppi_goods_record_phrase": "the largest increase since the goods index began in December 2009",
        "contrib_energy_pp": effect("energy"),
        "contrib_food_pp": effect("food"),
        "contrib_core_pp": effect("core"),
        "contrib_gasoline_pp": gasoline_effect,
        "contrib_effect_sum_pp": rh(float(plotted["effect_pp"].sum()), "0.001"),
        "gasoline_share_of_headline_pct": rh(100 * gasoline_effect / headline_print, "0.1"),
        "contrib_unit": "percentage points",
        "contrib_source": "BLS Table 6",
        "services_yoy": rh(cpi.loc[SEP, "services_yoy"], "0.1"),
        "core_yoy_low": rh(core_low, "0.1"),
        "core_yoy_low_month": month_name(core_low_month),
        "core_yoy_high": rh(core_high, "0.1"),
        "core_yoy_high_month": month_name(core_high_month),
        "services_yoy_low": rh(services_low, "0.1"),
        "services_yoy_low_month": month_name(services_low_month),
        "services_yoy_high": rh(services_high, "0.1"),
        "services_yoy_high_month": month_name(services_high_month),
        "core_firmer_than_prior_low": bool(core_yoy_now > core_low),
        "funds_target_low": rh(float(funds["funds_lower"].iloc[-1]), "0.01"),
        "funds_target_high": rh(float(funds["funds_upper"].iloc[-1]), "0.01"),
        "funds_as_of": funds.index[-1].strftime("%m/%d/%Y").lstrip("0").replace("/0", "/"),
    }

    destination = STATS_DIR / "summary_stats.json"
    destination.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")
    print(f"Core year-rate low since January 2026: {stats['core_yoy_low']} in {stats['core_yoy_low_month']}")
    print(f"Services year-rate low: {stats['services_yoy_low']} in {stats['services_yoy_low_month']}")


if __name__ == "__main__":
    main()
