"""
04_compute_stats.py
-------------------
Step 3 of the pipeline: compute every number the post displays and save them
in one file, stats/summary_stats.json.

What this script does, in plain English:
  1. Reads the cleaned tables produced by 02_clean_data.py.
  2. Pulls out, or calculates, each headline figure the article quotes: the
     latest inflation rates, how much energy contributed to them, how the
     current shock compares with 2008 and 2022, where oil peaked, what real
     wages are doing, and where interest rates stand.
  3. Writes them all into a single JSON file (a simple list of named
     values). The article itself never contains a typed-in number: every
     figure in the text is pulled live from this file, so the prose can
     never drift out of sync with the data.

Almost everything here is computed from the data. The only exceptions are
values that exist in no machine-readable feed, each marked with a MANUAL
comment naming its primary source. Per the publishing checklist, every
MANUAL value must be confirmed against its source before the post ships.

Run from the post folder (after 01 and 02):
    python scripts/04_compute_stats.py
"""

import json
import os

import pandas as pd

CLEAN = "data/clean"
OUT = "stats/summary_stats.json"

# MANUAL: CPI relative-importance weights, percent of the all-items basket,
# from the BLS relative importance tables (December 2025 values, rounded).
# https://www.bls.gov/cpi/tables/relative-importance/home.htm
# In plain terms: of every dollar the average household spends, BLS estimates
# about 6.5 cents go to energy, 36.4 cents to shelter, and so on. These
# weights are used only for the approximate contribution chart (Figure 3).
WEIGHTS = {
    "energy": 6.5,
    "shelter": 36.4,
    "food": 14.3,
    "core_goods": 18.5,
}


def r1(x):
    """Round to 1 decimal place, e.g. 4.17 -> 4.2 (how rates are quoted)."""
    return round(float(x), 1)


def r2(x):
    """Round to 2 decimal places, used for dollar amounts and yields."""
    return round(float(x), 2)


def main():
    # Load the four cleaned tables. Each has dates as rows and series as
    # columns; .iloc[-1] means "the most recent row" and .iloc[-2] the one
    # before it, which is how "this month vs last month" values are read.
    cpi = pd.read_csv(f"{CLEAN}/cpi_monthly.csv", index_col="date", parse_dates=True)
    labor = pd.read_csv(f"{CLEAN}/labor_monthly.csv", index_col="date", parse_dates=True)
    energy = pd.read_csv(f"{CLEAN}/energy_markets.csv", index_col="date", parse_dates=True)
    rates = pd.read_csv(f"{CLEAN}/rates_daily.csv", index_col="date", parse_dates=True)

    last = cpi.iloc[-1]       # May 2026, the month this post is about
    prev = cpi.iloc[-2]       # April 2026, the comparison month
    latest_month = cpi.index[-1].strftime("%B %Y")
    previous_month = cpi.index[-2].strftime("%B %Y")

    stats = {
        "latest_month": latest_month,
        "previous_month": previous_month,
    }

    # ------------------------------------------------------------------
    # Inflation rates. For every CPI component the post mentions, store
    # four numbers: this month's annual rate (yoy), this month's monthly
    # rate (mom), and both rates for the prior month (prev_), so the text
    # can say things like "+4.2%, up from +3.8%".
    # ------------------------------------------------------------------
    for comp in ["headline", "core", "energy", "gasoline", "shelter", "food",
                 "core_goods", "core_services"]:
        stats[f"{comp}_yoy"] = r1(last[f"{comp}_yoy"])
        stats[f"{comp}_mom"] = r1(last[f"{comp}_mom"])
        stats[f"prev_{comp}_yoy"] = r1(prev[f"{comp}_yoy"])
        stats[f"prev_{comp}_mom"] = r1(prev[f"{comp}_mom"])

    # The headline-minus-core gap: a simple, weight-free way to measure how
    # much of total inflation is coming from the volatile food and energy
    # categories. When the gap is wide, the shock is concentrated there.
    stats["headline_core_gap"] = r1(last["headline_yoy"] - last["core_yoy"])

    # ------------------------------------------------------------------
    # Approximate contributions to the headline rate (Figure 3, top panel).
    # The idea: a category that is 6.5% of spending and rose 23% contributed
    # roughly 6.5% x 23% = 1.5 percentage points to total inflation.
    # The leftover ("residual") bucket absorbs everything not listed plus
    # rounding error, so the bars always sum exactly to the headline rate.
    # ------------------------------------------------------------------
    contribs = {}
    for comp, w in WEIGHTS.items():
        contribs[comp] = round(w / 100 * last[f"{comp}_yoy"], 2)
    contribs["residual"] = round(last["headline_yoy"] - sum(contribs.values()), 2)
    stats["contrib_energy_pp"] = contribs["energy"]
    stats["contrib_shelter_pp"] = contribs["shelter"]
    stats["contrib_food_pp"] = contribs["food"]
    stats["contrib_core_goods_pp"] = contribs["core_goods"]
    stats["contrib_residual_pp"] = contribs["residual"]
    stats["energy_contribution_share"] = int(round(contribs["energy"] / last["headline_yoy"] * 100))
    stats["weights"] = WEIGHTS

    # ------------------------------------------------------------------
    # Historical energy-shock comparisons (Figure 3, bottom panel). For
    # each episode window, find the highest annual energy inflation rate,
    # the month it happened, and how wide the headline-core gap got. These
    # are computed from the full CPI history rather than typed from memory.
    # ------------------------------------------------------------------
    for name, lo, hi in [("2008", "2007-01-01", "2009-12-01"),
                         ("2022", "2021-01-01", "2023-06-01"),
                         ("current", "2025-06-01", cpi.index[-1])]:
        window = cpi.loc[lo:hi, "energy_yoy"]
        stats[f"energy_peak_{name}"] = r1(window.max())
        stats[f"energy_peak_{name}_month"] = window.idxmax().strftime("%B %Y")
        gap_window = (cpi["headline_yoy"] - cpi["core_yoy"]).loc[lo:hi]
        stats[f"gap_peak_{name}"] = r1(gap_window.max())

    # ------------------------------------------------------------------
    # Energy market levels and the shock window. These come from the RAW
    # daily and weekly files, not the Friday-snapped chart table, so every
    # date reported is a real observation date rather than a week label.
    # ------------------------------------------------------------------
    daily_raw = pd.read_csv("data/raw/fred_daily_raw.csv", index_col="date", parse_dates=True)
    weekly_raw = pd.read_csv("data/raw/fred_weekly_raw.csv", index_col="date", parse_dates=True)

    wti = daily_raw["wti"].dropna()
    stats["wti_latest"] = r1(wti.iloc[-1])
    stats["wti_latest_date"] = wti.index[-1].strftime("%B %d, %Y")
    shock = wti.loc["2026-01-01":]                      # the 2026 trading days
    stats["wti_peak_2026"] = r1(shock.max())            # highest close of 2026
    stats["wti_peak_2026_date"] = shock.idxmax().strftime("%B %d, %Y")
    stats["wti_jan_2026_avg"] = r1(wti.loc["2026-01"].mean())  # pre-shock level
    stats["wti_peak_pct_vs_jan"] = r1((shock.max() / wti.loc["2026-01"].mean() - 1) * 100)
    stats["days_above_100"] = int((shock > 100).sum())  # trading days over $100

    gas = weekly_raw["gas_retail"].dropna()
    stats["gas_retail_latest"] = r2(gas.iloc[-1])
    stats["gas_retail_latest_date"] = gas.index[-1].strftime("%B %d, %Y")
    stats["gas_retail_jan_2026_avg"] = r2(gas.loc["2026-01"].mean())
    stats["gas_retail_pct_vs_jan"] = r1((gas.iloc[-1] / gas.loc["2026-01"].mean() - 1) * 100)

    # ------------------------------------------------------------------
    # Labor market: job growth, unemployment, and the real-wage arithmetic
    # that section 4 is built on.
    # ------------------------------------------------------------------
    llast = labor.iloc[-1]
    stats["labor_month"] = labor.index[-1].strftime("%B %Y")
    stats["payroll_latest"] = int(llast["payroll_chg"])          # jobs added, thousands
    stats["payroll_3mo_avg"] = int(round(labor["payroll_chg"].tail(3).mean()))
    stats["unrate_latest"] = r1(llast["unrate"])
    stats["ahe_yoy"] = r1(llast["ahe_yoy"])                      # nominal wage growth
    stats["ahe_mom"] = r1(llast["ahe_mom"])
    stats["real_ahe_yoy"] = r1(llast["real_ahe_yoy"])            # after inflation
    stats["prev_real_ahe_yoy"] = r1(labor["real_ahe_yoy"].iloc[-2])
    # How many of the last 12 months had negative real wage growth.
    stats["neg_real_wage_months_12m"] = int((labor["real_ahe_yoy"].tail(12) < 0).sum())

    # ------------------------------------------------------------------
    # Treasury yields and the yield curve (Figure 5, bottom panel).
    # ------------------------------------------------------------------
    rlast = rates.iloc[-1]
    stats["dgs2_latest"] = r2(rlast["dgs2"])
    stats["dgs10_latest"] = r2(rlast["dgs10"])
    stats["spread_latest_bps"] = int(round(rlast["spread_bps"]))
    stats["rates_latest_date"] = rates.index[-1].strftime("%B %d, %Y")

    # The Fed's current target range, read from the official daily series
    # rather than typed in, so a surprise rate move can never go stale here.
    tgt = daily_raw[["fedtarl", "fedtaru"]].dropna().iloc[-1]
    stats["target_lower"] = r2(tgt["fedtarl"])
    stats["target_upper"] = r2(tgt["fedtaru"])
    stats["target_range"] = f"{tgt['fedtarl']:.2f}-{tgt['fedtaru']:.2f}"
    stats["target_midpoint"] = r2((tgt["fedtarl"] + tgt["fedtaru"]) / 2)

    # MANUAL: FOMC dot plot medians and interquartile range from the March
    # 2026 Summary of Economic Projections. The "dot plot" is the chart the
    # Fed publishes quarterly showing where each policymaker expects rates
    # to be at each year-end; the median dot is the committee's center.
    # https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
    # These match the values used in the April 2026 FOMC preview post.
    stats["dot_median_eoy2026"] = 3.375
    stats["dot_median_eoy2027"] = 3.125
    stats["dot_median_eoy2028"] = 3.125
    stats["dot_iqr_lo_2026"] = 3.125
    stats["dot_iqr_hi_2026"] = 3.625

    # MANUAL: market-implied federal funds path approximated from the CME
    # FedWatch tool, June 12, 2026 reading. FedWatch infers, from futures
    # prices, where traders collectively expect the Fed's rate to land.
    # Author approximation; confirm at
    # https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html
    # before publishing.
    stats["market_implied_eoy2026"] = 3.55
    stats["market_implied_eoy2027"] = 3.30
    stats["june_hold_prob_pct"] = 93

    # MANUAL: calendar dates from the BLS release schedule and the Federal
    # Reserve meeting calendar.
    # https://www.bls.gov/schedule/news_release/cpi.htm
    # https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
    stats["release_date"] = "June 10, 2026"
    stats["next_cpi_release"] = "July 14, 2026"
    stats["fomc_window"] = "June 16-17, 2026"

    stats["data_current_as_of"] = (
        f"{latest_month} CPI (BLS release: {stats['release_date']}); "
        f"market data through {stats['wti_latest_date']}"
    )
    stats["source_url"] = "https://www.bls.gov/news.release/cpi.htm"

    # Save everything as JSON and echo it to the screen so the values can
    # be eyeballed against the official release before the post ships.
    os.makedirs("stats", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote {len(stats)} keys to {OUT}")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
