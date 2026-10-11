"""
04_compute_stats.py
===================
STEP 3 of the data pipeline (script 03 is not used).

What this script does
---------------------
Reads the cleaned rates and writes stats/summary_stats.json. The post
reads every number from that file. Nothing in index.qmd is typed by hand.

Rounding
--------
BEA's published monthly and quarterly prints are shown to one decimal.
This script rounds half up. A FRED rate may differ in the second decimal.
If the rounded value is more than 0.05 percentage point from the BEA
print, the script stops instead of guessing.

Latest month
------------
The latest monthly row must be August 2026. The previous month is July.
The latest quarter must be 2026 Q2 on the September 30 vintage.
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

AUGUST = pd.Timestamp("2026-08-01")
JULY = pd.Timestamp("2026-07-01")
AUGUST_PRIOR = pd.Timestamp("2025-08-01")
Q1 = pd.Timestamp("2026-01-01")
Q2 = pd.Timestamp("2026-04-01")
ENERGY_WINDOW_START = pd.Timestamp("2025-09-01")

# Official September 30 prints. Checks, not substitutes for the FRED rates.
LOCKED_AUGUST = {
    "headline_mom": 0.3,
    "headline_yoy": 3.4,
    "core_mom": 0.2,
    "core_yoy": 3.0,
    "real_pce_mom": 0.6,
    "nominal_pce_mom": 0.9,
    "personal_income_mom": 0.2,
    "nominal_dpi_mom": 0.3,
    "real_dpi_mom": 0.0,
    "saving_rate": 4.1,
}
LOCKED_JULY_CURRENT = {
    "july_headline_mom": 0.1,
    "july_core_mom": 0.1,
    "july_real_pce_mom": 0.1,
    "july_real_dpi_mom": 0.3,
    "july_core_yoy": 3.0,
    "july_headline_yoy": 3.4,
}


def round1(value: float) -> float:
    """One decimal, half up, matching a BEA table rather than banker's rounding."""
    return _round_to(value, "0.1")


def round2(value: float) -> float:
    """Two decimals, half up. Used where one decimal hides a real difference."""
    return _round_to(value, "0.01")


def _round_to(value: float, places: str) -> float:
    quantized = Decimal(str(round(float(value), 6))).quantize(
        Decimal(places),
        rounding=ROUND_HALF_UP,
    )
    return float(quantized)


def require_close(name: str, computed: float, locked: float) -> float:
    """Return the rounded rate, or stop when it misses the BEA print."""
    rounded = round1(computed)
    if abs(rounded - locked) > 0.05:
        raise RuntimeError(
            f"{name} rounded to {rounded}, but the BEA print is {locked}. "
            "Do not substitute the brief for the file."
        )
    return locked


def month_name(ts: pd.Timestamp) -> str:
    """US month and year, for example March 2026."""
    return f"{ts.strftime('%B')} {ts.year}"


def main() -> None:
    monthly = pd.read_csv(CLEAN_DIR / "pce_monthly.csv", index_col="date", parse_dates=True)
    quarterly = pd.read_csv(CLEAN_DIR / "gdp_quarterly.csv", index_col="date", parse_dates=True)
    manual = json.loads((RAW_DIR / "manual_priors.json").read_text(encoding="utf-8"))

    if AUGUST not in monthly.index or JULY not in monthly.index or AUGUST_PRIOR not in monthly.index:
        raise RuntimeError("July 2026, August 2026, or August 2025 is missing from the cleaned monthly file.")
    if Q1 not in quarterly.index or Q2 not in quarterly.index:
        raise RuntimeError("2026 Q1 or Q2 is missing from the cleaned quarterly file.")

    august = monthly.loc[AUGUST]
    july = monthly.loc[JULY]
    august_prior = monthly.loc[AUGUST_PRIOR]
    q2 = quarterly.loc[Q2]
    h_aug_mom_hundredths = round2(float(august["pce_price_mom"]))
    h_aug25_mom_hundredths = round2(float(august_prior["pce_price_mom"]))
    h_yoy_step_hundredths = round2(h_aug_mom_hundredths - h_aug25_mom_hundredths)

    prices = pd.read_csv(CLEAN_DIR / "pce_price_monthly.csv", index_col="date", parse_dates=True)
    energy_window = prices.loc[ENERGY_WINDOW_START:AUGUST, "energy_price_mom"].dropna()
    if energy_window.empty:
        raise RuntimeError("The twelve-month energy window is empty.")
    energy_high_at = energy_window.idxmax()
    energy_low_at = energy_window.idxmin()

    indexes = pd.read_csv(CLEAN_DIR / "real_indexes.csv", index_col="date", parse_dates=True)
    if AUGUST not in indexes.index:
        raise RuntimeError("August 2026 is missing from the real index file.")

    stats: dict[str, object] = {
        "latest_month": "August 2026",
        "latest_month_short": "August",
        "data_current_as_of": "9/30/2026",
        "release_date": "9/30/2026",
        "setup_date": "9/26/2026",
        "release_note": "August personal income and outlays, and the second-quarter third estimate, both released 9/30/2026.",
        "headline_mom": require_close("headline_mom", august["pce_price_mom"], LOCKED_AUGUST["headline_mom"]),
        "headline_yoy": require_close("headline_yoy", august["pce_price_yoy"], LOCKED_AUGUST["headline_yoy"]),
        "core_mom": require_close("core_mom", august["core_price_mom"], LOCKED_AUGUST["core_mom"]),
        "core_yoy": require_close("core_yoy", august["core_price_yoy"], LOCKED_AUGUST["core_yoy"]),
        "real_pce_mom": require_close("real_pce_mom", august["real_pce_mom"], LOCKED_AUGUST["real_pce_mom"]),
        "nominal_pce_mom": require_close("nominal_pce_mom", august["nominal_pce_mom"], LOCKED_AUGUST["nominal_pce_mom"]),
        "personal_income_mom": require_close(
            "personal_income_mom", august["personal_income_mom"], LOCKED_AUGUST["personal_income_mom"]
        ),
        "nominal_dpi_mom": require_close(
            "nominal_dpi_mom", august["disposable_pi_mom"], LOCKED_AUGUST["nominal_dpi_mom"]
        ),
        "real_dpi_mom": require_close("real_dpi_mom", august["real_dpi_mom"], LOCKED_AUGUST["real_dpi_mom"]),
        "saving_rate": require_close("saving_rate", august["saving_rate"], LOCKED_AUGUST["saving_rate"]),
        "saving_rate_july": round1(july["saving_rate"]),
        "july_headline_mom": require_close(
            "july_headline_mom", july["pce_price_mom"], LOCKED_JULY_CURRENT["july_headline_mom"]
        ),
        "july_core_mom": require_close(
            "july_core_mom", july["core_price_mom"], LOCKED_JULY_CURRENT["july_core_mom"]
        ),
        "july_real_pce_mom": require_close(
            "july_real_pce_mom", july["real_pce_mom"], LOCKED_JULY_CURRENT["july_real_pce_mom"]
        ),
        "july_real_dpi_mom": require_close(
            "july_real_dpi_mom", july["real_dpi_mom"], LOCKED_JULY_CURRENT["july_real_dpi_mom"]
        ),
        "july_headline_yoy": require_close(
            "july_headline_yoy", july["pce_price_yoy"], LOCKED_JULY_CURRENT["july_headline_yoy"]
        ),
        "july_core_yoy": require_close(
            "july_core_yoy", july["core_price_yoy"], LOCKED_JULY_CURRENT["july_core_yoy"]
        ),
        "july_headline_yoy_prior": manual["july_headline_yoy_prior"],
        "july_core_yoy_prior": manual["july_core_yoy_prior"],
        "july_headline_yoy_hundredths": round2(july["pce_price_yoy"]),
        "july_core_yoy_hundredths": round2(july["core_price_yoy"]),
        "headline_yoy_hundredths": round2(august["pce_price_yoy"]),
        "core_yoy_hundredths": round2(august["core_price_yoy"]),
        "aug_prior_year": month_name(AUGUST_PRIOR),
        "h_aug_mom_hundredths": h_aug_mom_hundredths,
        "h_aug25_mom_hundredths": h_aug25_mom_hundredths,
        "h_yoy_step_hundredths": h_yoy_step_hundredths,
        "july_real_pce_mom_prior": manual["july_real_pce_mom_prior"],
        "july_saving_rate_prior": manual["july_saving_rate_prior"],
        "food_mom": round1(august["food_price_mom"]),
        "energy_mom": round1(august["energy_price_mom"]),
        "energy_window_high": round1(float(energy_window.loc[energy_high_at])),
        "energy_window_low": round1(float(energy_window.loc[energy_low_at])),
        "energy_high_month": month_name(energy_high_at),
        "energy_low_month": month_name(energy_low_at),
        "core_3m_annualized": round1(august["core_3m"]),
        "q2_gdp_third": require_close("q2_gdp_third", q2["gdp_saar"], 2.2),
        "q2_gdp_second": manual["q2_gdp_second"],
        "q2_gdp_advance": manual["q2_gdp_advance"],
        "q2_gdp_revision_pp": manual["q2_gdp_revision_pp"],
        "q1_gdp": require_close("q1_gdp", float(quarterly.loc[Q1, "gdp_saar"]), 2.5),
        "q1_gdp_revision_pp": manual["q1_gdp_revision_pp"],
        "q2_pdfp_third": require_close("q2_pdfp_third", q2["pdfp_saar"], 4.6),
        "q2_pdfp_second": manual["q2_pdfp_second"],
        "q2_pdfp_advance": manual["q2_pdfp_advance"],
        "q2_pdfp_revision_pp": manual["q2_pdfp_revision_pp"],
        "q2_gdi_third": manual["q2_gdi_third"],
        "q2_gdi_second": manual["q2_gdi_second"],
        "q2_gdi_revision_pp": manual["q2_gdi_revision_pp"],
        "q2_pce_price_saar": manual["q2_pce_price_saar"],
        "q2_pce_price_saar_prior": manual["q2_pce_price_saar_prior"],
        "q2_core_price_saar": manual["q2_core_price_saar"],
        "q2_core_price_saar_prior": manual["q2_core_price_saar_prior"],
        "q2_price_revision_pp": manual["q2_price_revision_pp"],
        "personal_income_billion": manual["personal_income_billion"],
        "dpi_billion": manual["dpi_billion"],
        "nominal_pce_billion": manual["nominal_pce_billion"],
        "real_pce_billion": manual["real_pce_billion"],
        "goods_pce_billion": manual["goods_pce_billion"],
        "services_pce_billion": manual["services_pce_billion"],
        "fed_target": manual["fed_target"],
        "funds_low": manual["funds_low"],
        "funds_high": manual["funds_high"],
        "sep_dot_2026": manual["sep_dot_2026"],
        "dots_one_more": manual["dots_one_more"],
        "dots_total": manual["dots_total"],
        "next_cpi_date": manual["next_cpi_date"],
        "next_ppi_date": manual["next_ppi_date"],
        "next_fomc_date": manual["next_fomc_date"],
        "next_bea_date": manual["next_bea_date"],
        "annual_update_start": "January 2021",
        "gdp_update_window": "the first quarter of 2021 through the first quarter of 2026",
        "reference_year": manual["reference_year"],
        "chart_start_yoy": "January 2023",
        "chart_end_month": "August 2026",
        "prior_month": month_name(JULY),
        "prior_month_short": JULY.strftime("%B"),
        "index_base": "January 2024",
        "real_pce_index": round1(float(indexes.loc[AUGUST, "real_pce_index"])),
        "real_dpi_index": round1(float(indexes.loc[AUGUST, "real_dpi_index"])),
        "fomc_decision_date": manual["fomc_decision_date"],
    }

    mich_row = monthly["mich"].dropna()
    if mich_row.empty:
        raise RuntimeError("Michigan inflation expectation is missing.")
    mich_date = mich_row.index.max()
    stats["mich_year_ahead"] = round1(mich_row.loc[mich_date])
    stats["mich_as_of"] = f"{mich_date.month}/{mich_date.year}"

    STATS_DIR.mkdir(parents=True, exist_ok=True)
    (STATS_DIR / "summary_stats.json").write_text(
        json.dumps(stats, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(stats)} stats keys. August core y/y={stats['core_yoy']}.")
    print(f"Michigan {stats['mich_as_of']} = {stats['mich_year_ahead']}")
    print(
        f"Energy window {stats['energy_window_low']} ({stats['energy_low_month']}) "
        f"to {stats['energy_window_high']} ({stats['energy_high_month']})."
    )
    print(
        f"Indexes real PCE {stats['real_pce_index']}, real income {stats['real_dpi_index']}. "
        f"Q1 GDP {stats['q1_gdp']}."
    )


if __name__ == "__main__":
    main()
