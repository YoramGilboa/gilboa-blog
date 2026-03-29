"""
02_compute_stats.py
Compute summary statistics for the claims-focused April 3 jobs preview post.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

CLEAN = Path(__file__).resolve().parent.parent / "data" / "clean"
STATS = Path(__file__).resolve().parent.parent / "stats"
STATS.mkdir(parents=True, exist_ok=True)

# ── Initial Claims ───────────────────────────────────────────────────────────

df_icsa = pd.read_csv(CLEAN / "initial_claims.csv", parse_dates=["date"])
df_icsa = df_icsa.dropna(subset=["initial_claims"])

latest = df_icsa.iloc[-1]
prior = df_icsa.iloc[-2]

# Year-over-year
one_yr_ago = df_icsa[df_icsa["date"] <= latest["date"] - pd.Timedelta(days=365)].iloc[-1]

# Since 2023
recent = df_icsa[df_icsa["date"] >= "2023-01-01"]

# Feb spike (weeks of Jan 31 and Feb 7)
feb_spike = df_icsa[(df_icsa["date"] >= "2026-01-31") & (df_icsa["date"] <= "2026-02-07")]

stats = {
    "data_current_as_of": "March 26, 2026",
    "jobs_report_date": "April 3, 2026",

    # Latest initial claims
    "icsa_latest": int(latest["initial_claims"]),
    "icsa_latest_date": latest["date"].strftime("%B %d, %Y"),
    "icsa_latest_week_ending": latest["date"].strftime("%B %d"),
    "icsa_prior": int(prior["initial_claims"]),
    "icsa_prior_date": prior["date"].strftime("%B %d, %Y"),
    "icsa_chg": int(latest["initial_claims"] - prior["initial_claims"]),
    "icsa_4wma": int(round(df_icsa.dropna(subset=["initial_claims_4wma"]).iloc[-1]["initial_claims_4wma"])),

    # Year-over-year
    "icsa_yoy": int(one_yr_ago["initial_claims"]),
    "icsa_yoy_date": one_yr_ago["date"].strftime("%B %d, %Y"),
    "icsa_yoy_chg": int(latest["initial_claims"] - one_yr_ago["initial_claims"]),

    # Feb spike
    "icsa_feb_spike_peak": int(feb_spike["initial_claims"].max()),

    # Since-2023 stats
    "icsa_min_since_2023": int(recent["initial_claims"].min()),
    "icsa_max_since_2023": int(recent["initial_claims"].max()),
    "icsa_mean_since_2023": int(round(recent["initial_claims"].mean())),

    # 4-week MA trend
    "icsa_4wma_8wks_ago": int(round(df_icsa.iloc[-8]["initial_claims_4wma"])),
}

# ── Continuing Claims ────────────────────────────────────────────────────────

df_ccsa = pd.read_csv(CLEAN / "continuing_claims.csv", parse_dates=["date"])
df_ccsa = df_ccsa.dropna(subset=["continuing_claims"])

latest_c = df_ccsa.iloc[-1]
prior_c = df_ccsa.iloc[-2]
one_yr_ago_c = df_ccsa[df_ccsa["date"] <= latest_c["date"] - pd.Timedelta(days=365)].iloc[-1]

recent_c = df_ccsa[df_ccsa["date"] >= "2023-01-01"]

# Find the last time CCSA was this low
lower_before = df_ccsa[(df_ccsa["continuing_claims"] <= latest_c["continuing_claims"])
                        & (df_ccsa["date"] < latest_c["date"])]
if len(lower_before) > 0:
    last_this_low = lower_before.iloc[-1]
    stats["ccsa_last_this_low_date"] = last_this_low["date"].strftime("%B %d, %Y")
else:
    stats["ccsa_last_this_low_date"] = "N/A"

stats.update({
    "ccsa_latest": int(latest_c["continuing_claims"]),
    "ccsa_latest_date": latest_c["date"].strftime("%B %d, %Y"),
    "ccsa_prior": int(prior_c["continuing_claims"]),
    "ccsa_chg": int(latest_c["continuing_claims"] - prior_c["continuing_claims"]),
    "ccsa_4wma": int(round(df_ccsa.dropna(subset=["continuing_claims_4wma"]).iloc[-1]["continuing_claims_4wma"])),

    # Year-over-year
    "ccsa_yoy": int(one_yr_ago_c["continuing_claims"]),
    "ccsa_yoy_chg": int(latest_c["continuing_claims"] - one_yr_ago_c["continuing_claims"]),

    # Since-2023 stats
    "ccsa_min_since_2023": int(recent_c["continuing_claims"].min()),
    "ccsa_max_since_2023": int(recent_c["continuing_claims"].max()),
    "ccsa_mean_since_2023": int(round(recent_c["continuing_claims"].mean())),

    # Insured unemployment rate (from the DOL release PDF)
    "insured_unemployment_rate": 1.2,
})

# ── Write ────────────────────────────────────────────────────────────────────

with open(STATS / "summary_stats.json", "w") as f:
    json.dump(stats, f, indent=2)

print("Summary stats written to:", STATS / "summary_stats.json")
for k, v in stats.items():
    print(f"  {k}: {v}")
