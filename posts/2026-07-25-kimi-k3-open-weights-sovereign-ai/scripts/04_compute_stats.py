"""
04_compute_stats.py — Build stats/summary_stats.json for inline prose and cards.

Pipeline order: 01_fetch_data.py → 02_clean_data.py → 04_compute_stats.py
Run from the post folder:  python scripts/04_compute_stats.py

Every number rendered in index.qmd should come from this JSON so the post
stays synchronized with the curated source tables.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = POST_DIR / "data" / "clean"
STATS_DIR = POST_DIR / "stats"
STATS_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    facts = pd.read_csv(CLEAN_DIR / "k3_facts.csv").iloc[0].to_dict()
    timeline = pd.read_csv(CLEAN_DIR / "open_model_timeline.csv", parse_dates=["date"])
    intel = pd.read_csv(CLEAN_DIR / "intelligence_index.csv")
    cost = pd.read_csv(CLEAN_DIR / "cost_per_task.csv")

    # Prior open-weight max before K3 (DeepSeek V4 Pro 1.6T in our table)
    prior = timeline[timeline["model"] != "Kimi K3"]
    open_param_max_prev_t = float(prior["total_params_b"].max() / 1000.0)
    k3_t = float(facts["k3_total_params_t"])
    jump_pct = (k3_t / open_param_max_prev_t - 1.0) * 100.0 if open_param_max_prev_t else None

    stats = {
        "latest_month": "July 2026",
        "latest_month_short": "Jul 2026",
        "data_current_as_of": "07/25/2026",
        "release_note": (
            "Kimi K3 API launched 07/16/2026; full weights targeted by 07/27/2026 "
            "per Moonshot. Benchmarks from Artificial Analysis as of mid-July 2026."
        ),
        # Core K3 facts
        "k3_total_params_t": float(facts["k3_total_params_t"]),
        "k3_active_experts": int(facts["k3_active_experts"]),
        "k3_total_experts": int(facts["k3_total_experts"]),
        "k3_context_tokens_m": float(facts["k3_context_tokens_m"]),
        "k3_aa_intelligence_index": int(facts["k3_aa_intelligence_index"]),
        "fable5_aa_intelligence_index": int(facts["fable5_aa_intelligence_index"]),
        "gpt56_sol_aa_intelligence_index": int(facts["gpt56_sol_aa_intelligence_index"]),
        "opus48_aa_intelligence_index": int(facts["opus48_aa_intelligence_index"]),
        "glm52_aa_intelligence_index": int(facts["glm52_aa_intelligence_index"]),
        "deepseek_v4_pro_aa_intelligence_index": int(facts["deepseek_v4_pro_aa_intelligence_index"]),
        "k3_gdpval_elo": int(facts["k3_gdpval_elo"]),
        "fable5_gdpval_elo": int(facts["fable5_gdpval_elo"]),
        "opus48_gdpval_elo": int(facts["opus48_gdpval_elo"]),
        "k3_aa_briefcase_elo": int(facts["k3_aa_briefcase_elo"]),
        "k3_cost_per_task": float(facts["k3_cost_per_task"]),
        "gpt56_sol_cost_per_task": float(facts["gpt56_sol_cost_per_task"]),
        "opus48_cost_per_task": float(facts["opus48_cost_per_task"]),
        "glm52_cost_per_task": float(facts["glm52_cost_per_task"]),
        "deepseek_v4_pro_cost_per_task": 0.04,
        "k3_input_price_per_m": float(facts["k3_input_price_per_m"]),
        "k3_output_price_per_m": float(facts["k3_output_price_per_m"]),
        "k3_cache_input_price_per_m": float(facts["k3_cache_input_price_per_m"]),
        "k3_api_launch_date": str(facts["k3_api_launch_date"]),
        "k3_weights_target_date": str(facts["k3_weights_target_date"]),
        "k3_token_efficiency_vs_k26_pct": float(facts["k3_token_efficiency_vs_k26_pct"]),
        "browsecomp_1m_score": float(facts["browsecomp_1m_score"]),
        "open_param_max_prev_t": open_param_max_prev_t,
        "open_param_jump_vs_prev_pct": round(jump_pct, 1) if jump_pct is not None else None,
        # Convenience derived
        "k3_vs_fable5_index_gap": int(facts["fable5_aa_intelligence_index"]) - int(facts["k3_aa_intelligence_index"]),
        "k3_vs_fable5_gdpval_elo_gap": int(facts["fable5_gdpval_elo"]) - int(facts["k3_gdpval_elo"]),
        "k3_vs_opus48_gdpval_elo_gap": int(facts["k3_gdpval_elo"]) - int(facts["opus48_gdpval_elo"]),
        "k3_vs_opus48_cost_ratio": round(
            float(facts["opus48_cost_per_task"]) / float(facts["k3_cost_per_task"]), 2
        ),
        "k3_hallucination_rate_pct": float(facts.get("k3_hallucination_rate_pct", 51.0)),
        "k3_accuracy_rate_pct": float(facts.get("k3_accuracy_rate_pct", 46.0)),
        "k26_accuracy_rate_pct": float(facts.get("k26_accuracy_rate_pct", 33.0)),
        "k26_hallucination_rate_pct": float(facts.get("k26_hallucination_rate_pct", 39.0)),
        "fable5_accuracy_rate_pct": float(facts.get("fable5_accuracy_rate_pct", 61.0)),
        "fable5_hallucination_rate_pct": float(facts.get("fable5_hallucination_rate_pct", 54.9)),
        "gpt56_sol_accuracy_rate_pct": float(facts.get("gpt56_sol_accuracy_rate_pct", 59.0)),
        "opus48_hallucination_rate_pct": float(facts.get("opus48_hallucination_rate_pct", 35.9)),
        "k3_aa_omniscience_index": int(facts.get("k3_aa_omniscience_index", 18)),
        "fable5_aa_omniscience_index": int(facts.get("fable5_aa_omniscience_index", 40)),
        "k26_aa_omniscience_index": int(facts.get("k26_aa_omniscience_index", 6)),
        "fable5_aa_briefcase_elo": int(facts.get("fable5_aa_briefcase_elo", 1574)),
        "gpt56_sol_aa_briefcase_elo": int(facts.get("gpt56_sol_aa_briefcase_elo", 1501)),
        "k3_vs_fable5_accuracy_gap_pp": round(
            float(facts.get("fable5_accuracy_rate_pct", 61.0))
            - float(facts.get("k3_accuracy_rate_pct", 46.0)),
            1,
        ),
        "k3_vs_sol_accuracy_gap_pp": round(
            float(facts.get("gpt56_sol_accuracy_rate_pct", 59.0))
            - float(facts.get("k3_accuracy_rate_pct", 46.0)),
            1,
        ),
        "k3_vs_opus48_hallucination_gap_pp": round(
            float(facts.get("k3_hallucination_rate_pct", 51.0))
            - float(facts.get("opus48_hallucination_rate_pct", 35.9)),
            1,
        ),
        "intel_models_n": int(len(intel)),
        "cost_models_n": int(len(cost)),
        "timeline_models_n": int(len(timeline)),
        "pipeline_built_on": date.today().isoformat(),
        "deepseek_v3_total_params_b": 671,
        "deepseek_v3_active_params_b": 37,
        "k2_total_params_b": 1000,
        "k2_active_params_b": 32,
        "k2_active_experts": 8,
        "k2_total_experts": 384,
        "k3_total_params_b": 2800,
        "fable5_aa_briefcase_note": "only Fable 5 ranked higher than K3 at launch",
    }

    out = STATS_DIR / "summary_stats.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote {out} with {len(stats)} keys")


if __name__ == "__main__":
    main()
