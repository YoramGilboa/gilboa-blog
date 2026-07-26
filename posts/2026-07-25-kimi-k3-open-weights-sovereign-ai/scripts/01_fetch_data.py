"""
01_fetch_data.py — Build curated raw datasets for the Kimi K3 / open-weights post.

Pipeline order: 01_fetch_data.py → 02_clean_data.py → 04_compute_stats.py
Run from the post folder:  python scripts/01_fetch_data.py

This post does not use FRED. Values are compiled from public, citable sources
(Moonshot Kimi K3 tech blog, Artificial Analysis Kimi K3 write-up, and
widely reported open-model release sizes). See data/raw/sources.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POST_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = POST_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── Source manifest (documentation for reproducibility) ──
SOURCES = {
    "moonshot_k3_blog": {
        "title": "Kimi K3: Open Frontier Intelligence",
        "url": "https://www.kimi.com/blog/kimi-k3",
        "used_for": [
            "2.8T parameters",
            "896 experts / 16 active (MoE)",
            "1M context",
            "API launch 2026-07-16",
            "weights target by 2026-07-27",
            "API pricing $0.30 cache / $3 input / $15 output per MTok",
            "BrowseComp 90.4 with 1M context (blog footnotes)",
        ],
    },
    "artificial_analysis_k3": {
        "title": "Kimi K3 achieves #3 in the Artificial Analysis Intelligence Index",
        "url": "https://artificialanalysis.ai/articles/kimi-k3-achieves-3-in-the-artificial-analysis-intelligence-index-comparable-to-opus-4-8-and-gpt-5-5",
        "used_for": [
            "AA Intelligence Index: K3=57; peers cited in secondary write-ups",
            "GDPval-AA v2 Elo: K3=1668, Fable 5=1760, Opus 4.8=1600",
            "AA-Briefcase Elo: K3=1547",
            "Cost per AA task: K3=$0.94, GPT-5.6 Sol=$1.04, Opus 4.8=$1.80, GLM-5.2=$0.32",
            "Open peers: GLM-5.2 Index 51 (753B), DeepSeek V4 Pro Index 44 (1.6T)",
            "Token efficiency: ~21% fewer output tokens vs K2.6",
        ],
    },
    "model_releases": {
        "title": "Public open-weight release announcements (compiled)",
        "url": "multiple",
        "used_for": [
            "Llama 3.1 405B (Meta, 2024-07)",
            "DeepSeek-V3 671B (2024-12)",
            "Qwen2.5-72B dense reference (2024-09)",
            "DeepSeek-R1 671B (2025-01)",
            "Kimi K2 ~1T (2025-09)",
            "DeepSeek-V3.2 685B (2025-12)",
            "DeepSeek V4 Pro 1.6T (2026)",
            "GLM-5.2 753B (2026)",
            "Kimi K3 2.8T (2026-07)",
        ],
    },
    "notes": [
        "Intelligence Index point estimates for Fable 5 (~60), GPT-5.6 Sol (~59), Opus 4.8 (~56) come from Artificial Analysis coverage summarized in secondary technical write-ups aligned with the AA article.",
        "Access-control scores in access_control.csv are a transparent ordinal rubric for teaching (0-3), not a published benchmark.",
        "Active parameter counts for MoE models are approximate public figures; K3 active params use Moonshot's 16/896 expert activation narrative rather than an exact active-billion figure when not published.",
    ],
}


def write_timeline() -> None:
    """Open-weight model total-parameter milestones (public announcements)."""
    rows = [
        {"date": "2024-07-23", "model": "Llama 3.1 405B", "lab": "Meta", "total_params_b": 405, "open_weight": 1},
        {"date": "2024-09-19", "model": "Qwen2.5-72B", "lab": "Alibaba", "total_params_b": 72, "open_weight": 1},
        {"date": "2024-12-26", "model": "DeepSeek-V3", "lab": "DeepSeek", "total_params_b": 671, "open_weight": 1},
        {"date": "2025-01-20", "model": "DeepSeek-R1", "lab": "DeepSeek", "total_params_b": 671, "open_weight": 1},
        {"date": "2025-09-02", "model": "Kimi K2", "lab": "Moonshot", "total_params_b": 1000, "open_weight": 1},
        {"date": "2025-12-01", "model": "DeepSeek-V3.2", "lab": "DeepSeek", "total_params_b": 685, "open_weight": 1},
        {"date": "2026-04-15", "model": "DeepSeek V4 Pro", "lab": "DeepSeek", "total_params_b": 1600, "open_weight": 1},
        {"date": "2026-06-01", "model": "GLM-5.2", "lab": "Zhipu", "total_params_b": 753, "open_weight": 1},
        {"date": "2026-07-16", "model": "Kimi K3", "lab": "Moonshot", "total_params_b": 2800, "open_weight": 1},
    ]
    pd.DataFrame(rows).to_csv(RAW_DIR / "open_model_timeline.csv", index=False)


def write_moe() -> None:
    """Total parameters and approximate active parameters for large MoE models."""
    # active_params_b is approximate where labs publish activated size.
    # For K3, Moonshot published expert counts (16 of 896) rather than active-B;
    # we leave active_params_b as null and store expert counts separately.
    rows = [
        {"model": "DeepSeek-V3", "total_params_b": 671, "active_params_b": 37, "total_experts": None, "active_experts": None},
        {"model": "Kimi K2", "total_params_b": 1000, "active_params_b": 32, "total_experts": 384, "active_experts": 8},
        {"model": "DeepSeek V4 Pro", "total_params_b": 1600, "active_params_b": 49, "total_experts": None, "active_experts": None},
        {"model": "Kimi K3", "total_params_b": 2800, "active_params_b": None, "total_experts": 896, "active_experts": 16},
    ]
    pd.DataFrame(rows).to_csv(RAW_DIR / "moe_params.csv", index=False)


def write_intelligence() -> None:
    """Artificial Analysis Intelligence Index (approximate published points)."""
    rows = [
        {"model": "Claude Fable 5", "score": 60, "access": "closed"},
        {"model": "GPT-5.6 Sol", "score": 59, "access": "closed"},
        {"model": "Kimi K3", "score": 57, "access": "open_weights"},
        {"model": "Claude Opus 4.8", "score": 56, "access": "closed"},
        {"model": "GLM-5.2", "score": 51, "access": "open_weights"},
        {"model": "DeepSeek V4 Pro", "score": 44, "access": "open_weights"},
    ]
    pd.DataFrame(rows).to_csv(RAW_DIR / "intelligence_index.csv", index=False)


def write_gdpval() -> None:
    rows = [
        {"model": "Claude Fable 5", "elo": 1760, "access": "closed"},
        {"model": "Kimi K3", "elo": 1668, "access": "open_weights"},
        {"model": "Claude Opus 4.8", "elo": 1600, "access": "closed"},
        {"model": "GLM-5.2", "elo": 1514, "access": "open_weights"},
        {"model": "GPT-5.5", "elo": 1494, "access": "closed"},
    ]
    pd.DataFrame(rows).to_csv(RAW_DIR / "gdpval_elo.csv", index=False)


def write_cost() -> None:
    rows = [
        {"model": "DeepSeek V4 Pro", "cost_usd": 0.04, "access": "open_weights"},
        {"model": "GLM-5.2", "cost_usd": 0.32, "access": "open_weights"},
        {"model": "Kimi K3", "cost_usd": 0.94, "access": "open_weights"},
        {"model": "GPT-5.6 Sol", "cost_usd": 1.04, "access": "closed"},
        {"model": "Claude Opus 4.8", "cost_usd": 1.80, "access": "closed"},
    ]
    pd.DataFrame(rows).to_csv(RAW_DIR / "cost_per_task.csv", index=False)


def write_cost_quality() -> None:
    """Cost per AA task vs Intelligence Index for models with both published."""
    rows = [
        {"model": "DeepSeek V4 Pro", "cost_usd": 0.04, "aa_index": 44, "access": "open_weights"},
        {"model": "GLM-5.2", "cost_usd": 0.32, "aa_index": 51, "access": "open_weights"},
        {"model": "Kimi K3", "cost_usd": 0.94, "aa_index": 57, "access": "open_weights"},
        {"model": "GPT-5.6 Sol", "cost_usd": 1.04, "aa_index": 59, "access": "closed"},
        {"model": "Claude Opus 4.8", "cost_usd": 1.80, "aa_index": 56, "access": "closed"},
        {"model": "Claude Fable 5", "cost_usd": None, "aa_index": 60, "access": "closed"},
    ]
    pd.DataFrame(rows).to_csv(RAW_DIR / "cost_quality.csv", index=False)


def write_access_control() -> None:
    """
    Teaching rubric (0-3) for what a buyer controls under each access model.
    Not a published benchmark — labeled as such in the post.
    0 = little/no local control; 3 = full local control.
    Dimensions:
      data_privacy: whether prompts/data stay on infrastructure you choose
      customization: ability to fine-tune or deeply adapt the model
      auditability: ability to inspect weights/code
      continuity: independence from a vendor turning off the API
    """
    rows = [
        {"dimension": "Data privacy", "closed_api": 1, "open_weights": 3, "full_open_source": 3},
        {"dimension": "Customization", "closed_api": 1, "open_weights": 3, "full_open_source": 3},
        {"dimension": "Auditability", "closed_api": 0, "open_weights": 2, "full_open_source": 3},
        {"dimension": "Continuity", "closed_api": 1, "open_weights": 3, "full_open_source": 3},
    ]
    pd.DataFrame(rows).to_csv(RAW_DIR / "access_control.csv", index=False)


def write_k3_facts() -> None:
    """Single-row key facts for stats computation."""
    facts = {
        "k3_total_params_t": 2.8,
        "k3_active_experts": 16,
        "k3_total_experts": 896,
        "k3_context_tokens_m": 1.0,
        "k3_aa_intelligence_index": 57,
        "fable5_aa_intelligence_index": 60,
        "gpt56_sol_aa_intelligence_index": 59,
        "opus48_aa_intelligence_index": 56,
        "glm52_aa_intelligence_index": 51,
        "deepseek_v4_pro_aa_intelligence_index": 44,
        "k3_gdpval_elo": 1668,
        "fable5_gdpval_elo": 1760,
        "opus48_gdpval_elo": 1600,
        "k3_aa_briefcase_elo": 1547,
        "k3_cost_per_task": 0.94,
        "gpt56_sol_cost_per_task": 1.04,
        "opus48_cost_per_task": 1.80,
        "glm52_cost_per_task": 0.32,
        "k3_input_price_per_m": 3.0,
        "k3_output_price_per_m": 15.0,
        "k3_cache_input_price_per_m": 0.30,
        "k3_api_launch_date": "07/16/2026",
        "k3_weights_target_date": "07/27/2026",
        "k3_token_efficiency_vs_k26_pct": 21.0,
        "browsecomp_1m_score": 90.4,
        "open_param_max_prev_t": 1.6,
        "k3_hallucination_rate_pct": 51.0,
        "k3_accuracy_rate_pct": 46.0,
        "k26_accuracy_rate_pct": 33.0,
        "k26_hallucination_rate_pct": 39.0,
        "fable5_accuracy_rate_pct": 61.0,
        "fable5_hallucination_rate_pct": 54.9,
        "gpt56_sol_accuracy_rate_pct": 59.0,
        "opus48_hallucination_rate_pct": 35.9,
        "k3_aa_omniscience_index": 18,
        "fable5_aa_omniscience_index": 40,
        "k26_aa_omniscience_index": 6,
        "fable5_aa_briefcase_elo": 1574,
        "gpt56_sol_aa_briefcase_elo": 1501,
    }
    pd.DataFrame([facts]).to_csv(RAW_DIR / "k3_facts.csv", index=False)


def main() -> None:
    write_timeline()
    write_moe()
    write_intelligence()
    write_gdpval()
    write_cost()
    write_cost_quality()
    write_access_control()
    write_k3_facts()
    with open(RAW_DIR / "sources.json", "w", encoding="utf-8") as f:
        json.dump(SOURCES, f, indent=2)
    print(f"Wrote raw CSVs and sources.json to {RAW_DIR}")


if __name__ == "__main__":
    main()
