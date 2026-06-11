"""
02_clean_data.py
----------------
Step 2 of the pipeline: turn the raw downloads into the exact tables the
post's charts read.

What this script does, in plain English:
  1. Reads the raw CSV files saved by 01_fetch_data.py.
  2. Converts price INDEX LEVELS into the growth rates people actually talk
     about. A CPI value of 333.98 means nothing to a reader by itself; what
     matters is that it is 4.2% higher than twelve months earlier (the
     "year-over-year" change) or 0.5% higher than last month (the
     "month-over-month" change).
  3. Lines up oil, pump prices, and the CPI gasoline index on one weekly
     timeline and re-expresses each as an index where its January 2026
     average equals 100, so series measured in different units (dollars per
     barrel vs dollars per gallon) can share one chart.
  4. Computes real (inflation-adjusted) wage growth and the Treasury yield
     spread.
  5. Saves everything under data/clean/, one CSV per chart family.

Inputs  (from 01_fetch_data.py):
    data/raw/fred_cpi_raw.csv      monthly CPI index levels
    data/raw/fred_labor_raw.csv    monthly labor series
    data/raw/fred_daily_raw.csv    daily oil and Treasury series
    data/raw/fred_weekly_raw.csv   weekly retail gasoline

Outputs:
    data/clean/cpi_monthly.csv     levels + YoY + MoM for every CPI component
    data/clean/labor_monthly.csv   wage growth, real wage growth, payroll changes
    data/clean/energy_markets.csv  weekly WTI / retail gasoline / CPI gasoline,
                                   plus indexes rebased to the pre-shock baseline
    data/clean/rates_daily.csv     2y, 10y, and the 10y-2y spread

Run from the post folder (after 01_fetch_data.py):
    python scripts/02_clean_data.py
"""

import os

import pandas as pd

RAW = "data/raw"
CLEAN = "data/clean"

# The pre-shock baseline month used to index the energy market series.
# Oil traded in a calm range through January 2026; the Iran-related
# repricing arrived in February. Setting January 2026 = 100 makes every
# later value read directly as "percent of the pre-shock level".
BASELINE_MONTH = "2026-01"


def clean_cpi():
    """Convert CPI index levels into year-over-year and month-over-month rates."""
    df = pd.read_csv(f"{RAW}/fred_cpi_raw.csv", index_col="date", parse_dates=True)

    # Stretch the table onto a complete monthly calendar before computing
    # changes. This matters because October 2025 CPI was never published:
    # on a complete calendar, "12 steps back" is guaranteed to mean "12
    # calendar months back", and any month whose comparison point is the
    # missing October simply comes out blank instead of being silently
    # compared against the wrong month.
    df = df.asfreq("MS")

    # pct_change(12) asks, for every month: how much higher is this value
    # than it was 12 months ago? Multiplying by 100 turns the fraction into
    # a percentage. This is the inflation rate quoted in headlines.
    yoy = df.pct_change(12) * 100
    yoy.columns = [f"{c}_yoy" for c in yoy.columns]

    # pct_change(1) is the same question against last month: the momentum
    # measure that shows turning points sooner than the annual rate.
    mom = df.pct_change(1) * 100
    mom.columns = [f"{c}_mom" for c in mom.columns]

    # Keep levels and both growth rates side by side, and trim the early
    # months that have no year-over-year value (nothing 12 months earlier).
    out = pd.concat([df, yoy, mom], axis=1)
    out = out[out.index >= out["headline_yoy"].first_valid_index()]
    out.to_csv(f"{CLEAN}/cpi_monthly.csv")
    print(f"cpi_monthly.csv: {len(out)} rows, last month {out.index[-1].date()}")
    return out


def clean_labor(cpi):
    """Compute wage growth and inflation-adjusted (real) wage growth."""
    df = pd.read_csv(f"{RAW}/fred_labor_raw.csv", index_col="date", parse_dates=True)
    df = df.asfreq("MS")  # same complete-calendar rule as the CPI table

    df["ahe_yoy"] = df["ahe"].pct_change(12) * 100   # wage growth vs a year ago
    df["ahe_mom"] = df["ahe"].pct_change(1) * 100    # wage growth vs last month
    df["payroll_chg"] = df["payems"].diff()          # jobs added each month

    # Real wage growth asks: after inflation, is an hour of work buying more
    # or less than a year ago? Dividing the wage by the price level gives
    # purchasing power; the year-over-year change of THAT ratio is the exact
    # answer. (The common shortcut, wage growth minus inflation, is only an
    # approximation and drifts when inflation runs hot.)
    headline = cpi["headline"].reindex(df.index)
    real_ahe = df["ahe"] / headline
    df["real_ahe_yoy"] = real_ahe.pct_change(12) * 100

    out = df.dropna(subset=["ahe_yoy"])
    out.to_csv(f"{CLEAN}/labor_monthly.csv")
    print(f"labor_monthly.csv: {len(out)} rows, last month {out.index[-1].date()}")
    return out


def clean_energy_markets(cpi):
    """Put oil, pump prices, and CPI gasoline on one comparable weekly timeline."""
    daily = pd.read_csv(f"{RAW}/fred_daily_raw.csv", index_col="date", parse_dates=True)
    weekly = pd.read_csv(f"{RAW}/fred_weekly_raw.csv", index_col="date", parse_dates=True)

    # The three series arrive at three different speeds: oil is daily, pump
    # prices are weekly, the CPI gasoline index is monthly. To draw them on
    # one chart, everything is snapped to a common Friday-to-Friday weekly
    # grid, taking the latest value available within each week. Forward-fill
    # (ffill) carries the last known value across short gaps such as
    # holidays, so no week shows a spurious blank.
    wti = daily["wti"].resample("W-FRI").last()
    gas = weekly["gas_retail"].resample("W-FRI").last()
    m = pd.concat([wti, gas], axis=1).ffill().dropna()

    # The monthly CPI gasoline index is carried forward within each month,
    # which is why it appears as steps on the chart: the official index
    # only moves once a month, with a lag. That visual lag is the point.
    cpi_gas = cpi["gasoline"].resample("W-FRI").ffill()
    m["cpi_gasoline"] = cpi_gas.reindex(m.index).ffill()

    # Rebase each series so its January 2026 average equals 100. A reading
    # of 158 then means "58% above the pre-shock level", regardless of
    # whether the underlying unit is $/barrel, $/gallon, or an index.
    base = m.loc[BASELINE_MONTH].mean()
    for col in ["wti", "gas_retail", "cpi_gasoline"]:
        m[f"{col}_idx"] = m[col] / base[col] * 100

    m.to_csv(f"{CLEAN}/energy_markets.csv")
    print(f"energy_markets.csv: {len(m)} rows, last week {m.index[-1].date()}")
    return m


def clean_rates():
    """Compute the 10-year minus 2-year Treasury spread, in basis points."""
    daily = pd.read_csv(f"{RAW}/fred_daily_raw.csv", index_col="date", parse_dates=True)
    out = daily[["dgs2", "dgs10"]].dropna().copy()

    # The spread between long and short Treasury yields is a classic gauge
    # of the bond market's outlook. Multiplying by 100 converts percentage
    # points into basis points, the unit rate-watchers quote (1bp = 0.01%).
    out["spread_bps"] = (out["dgs10"] - out["dgs2"]) * 100
    out.to_csv(f"{CLEAN}/rates_daily.csv")
    print(f"rates_daily.csv: {len(out)} rows, last day {out.index[-1].date()}")
    return out


def main():
    os.makedirs(CLEAN, exist_ok=True)
    cpi = clean_cpi()
    clean_labor(cpi)
    clean_energy_markets(cpi)
    clean_rates()


if __name__ == "__main__":
    main()
