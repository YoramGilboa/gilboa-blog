"""
02_clean_data.py — Normalize curated raw tables for charts and stats.

Pipeline order: 01_fetch_data.py → 02_clean_data.py → 04_compute_stats.py
Run from the post folder:  python scripts/02_clean_data.py

Canonical definitions used in this post (not macro m/m rates):
  - total_params_b: total stored parameters in billions
  - total_params_t: total parameters in trillions (params_b / 1000)
  - score: Artificial Analysis Intelligence Index points (unitless)
  - elo: Elo rating on GDPval-AA v2 (unitless)
  - cost_usd: USD cost per Artificial Analysis Intelligence Index task
  - control scores: ordinal 0-3 teaching rubric (see access_control.csv)

Chart code only plots cleaned columns; it does not re-derive formulas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)


def clean_timeline() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "open_model_timeline.csv", parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["total_params_t"] = df["total_params_b"] / 1000.0
    df["label"] = df["model"]
    df.to_csv(CLEAN_DIR / "open_model_timeline.csv", index=False)
    return df


def clean_moe() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "moe_params.csv")
    # For bar chart: use active_params_b when known; for K3 use expert fraction
    # only in prose. Chart shows total_params_b and active where available.
    df["active_share_pct"] = None
    mask = df["active_params_b"].notna()
    df.loc[mask, "active_share_pct"] = (
        df.loc[mask, "active_params_b"] / df.loc[mask, "total_params_b"] * 100.0
    )
    expert_mask = df["active_experts"].notna() & df["total_experts"].notna()
    df.loc[expert_mask, "expert_active_share_pct"] = (
        df.loc[expert_mask, "active_experts"] / df.loc[expert_mask, "total_experts"] * 100.0
    )
    df.to_csv(CLEAN_DIR / "moe_params.csv", index=False)
    return df


def clean_intelligence() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "intelligence_index.csv")
    # Sort ascending for barh (top of chart = highest score after reordering in plot)
    df = df.sort_values("score", ascending=True).reset_index(drop=True)
    df.to_csv(CLEAN_DIR / "intelligence_index.csv", index=False)
    return df


def clean_gdpval() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "gdpval_elo.csv")
    df = df.sort_values("elo", ascending=True).reset_index(drop=True)
    df.to_csv(CLEAN_DIR / "gdpval_elo.csv", index=False)
    return df


def clean_cost() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "cost_per_task.csv")
    # Sort so cheapest appears at top of barh when ascending=True in plot order
    df = df.sort_values("cost_usd", ascending=False).reset_index(drop=True)
    df.to_csv(CLEAN_DIR / "cost_per_task.csv", index=False)
    return df


def clean_cost_quality() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "cost_quality.csv")
    df.to_csv(CLEAN_DIR / "cost_quality.csv", index=False)
    return df


def clean_access() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "access_control.csv")
    df.to_csv(CLEAN_DIR / "access_control.csv", index=False)
    return df


def clean_facts() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "k3_facts.csv")
    df.to_csv(CLEAN_DIR / "k3_facts.csv", index=False)
    return df


def main() -> None:
    clean_timeline()
    clean_moe()
    clean_intelligence()
    clean_gdpval()
    clean_cost()
    clean_cost_quality()
    clean_access()
    clean_facts()
    print(f"Wrote clean CSVs to {CLEAN_DIR}")


if __name__ == "__main__":
    main()
