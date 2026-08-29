"""
03_visualizations.py
====================
STEP 3 of the data pipeline.

Saves the five post figures under figures/. The same plots are also drawn
inside index.qmd so readers can expand the code. Rate formulas live in
02_clean_data.py; this script only plots those columns.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

POST_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = POST_DIR / "data" / "clean"
FIG_DIR = POST_DIR / "figures"

COLORS = {
    "headline": "#e76f51",
    "core": "#1f4e79",
    "target": "#2a9d8f",
    "neutral": "#4a4a4a",
    "light": "#b0b0b0",
}

TWO_PCT_MONTHLY = 0.16515198  # (1.02)^(1/12) - 1, as percent ~ 0.17


def setup_style() -> None:
    plt.rcParams.update({
        "font.family": "Calibri",
        "font.size": 10,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "axes.linewidth": 0.5,
        "lines.linewidth": 1.8,
        "figure.facecolor": "white",
        "axes.facecolor": "#fafafa",
    })


def extend_xlim(ax, index, pad_frac: float = 0.12) -> None:
    span = index[-1] - index[0]
    ax.set_xlim(index[0], index[-1] + span * pad_frac)


def chart_yoy(df: pd.DataFrame) -> None:
    plot = df.loc["2023-01-01":, ["pce_headline_yoy", "pce_core_yoy"]].dropna()
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    ax.plot(plot.index, plot["pce_headline_yoy"], color=COLORS["headline"], linewidth=1.9)
    ax.plot(plot.index, plot["pce_core_yoy"], color=COLORS["core"], linewidth=1.9)
    ax.axhline(2.0, color=COLORS["target"], linestyle="--", linewidth=1.0, alpha=0.7)
    ax.text(plot.index[4], 2.12, "Fed 2% target", color=COLORS["target"], fontsize=8, alpha=0.85)

    shock = pd.Timestamp("2026-04-01")
    if shock in plot.index:
        ax.annotate(
            "Spring 2026\nenergy shock",
            xy=(shock, float(plot.loc[shock, "pce_headline_yoy"])),
            xytext=(shock - pd.Timedelta(days=200), float(plot["pce_headline_yoy"].max()) - 0.4),
            fontsize=8,
            color=COLORS["headline"],
            arrowprops=dict(arrowstyle="->", color=COLORS["light"], lw=0.8),
            bbox=dict(facecolor="#fafafa", edgecolor="none", alpha=0.9, pad=2.0),
            zorder=5,
        )

    last = plot.iloc[-1]
    ax.scatter(plot.index[-1], last["pce_headline_yoy"], s=40, color=COLORS["headline"],
               edgecolors="white", linewidth=0.8, zorder=5)
    ax.scatter(plot.index[-1], last["pce_core_yoy"], s=40, color=COLORS["core"],
               edgecolors="white", linewidth=0.8, zorder=5)
    ax.text(plot.index[-1], last["pce_headline_yoy"],
            f"  Headline {last['pce_headline_yoy']:.1f}%",
            color=COLORS["headline"], fontsize=8, fontweight="bold", va="center")
    ax.text(plot.index[-1], last["pce_core_yoy"] - 0.18,
            f"  Core {last['pce_core_yoy']:.1f}%",
            color=COLORS["core"], fontsize=8, fontweight="bold", va="top")

    extend_xlim(ax, plot.index, 0.16)
    ax.set_title("PCE Inflation Held Above the Fed's 2% Target", fontweight="bold")
    ax.set_ylabel("Year-over-year (%)")
    ax.set_xlabel("Month")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()
    fig.savefig(FIG_DIR / "pce-headline-core-yoy.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_monthly(df: pd.DataFrame) -> None:
    cols = ["pce_headline_mom", "pce_core_mom"]
    plot = df.loc[:, cols].dropna().iloc[-12:]
    x = range(len(plot))
    width = 0.38
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    ax.bar([i - width / 2 for i in x], plot["pce_headline_mom"], width=width,
           color=COLORS["headline"], edgecolor="white", label="Headline PCE")
    ax.bar([i + width / 2 for i in x], plot["pce_core_mom"], width=width,
           color=COLORS["core"], edgecolor="white", label="Core PCE")
    ax.axhline(TWO_PCT_MONTHLY, color=COLORS["target"], linestyle="--", linewidth=1.0)
    ax.text(
        0.02, 0.92,
        "Dashed line: 0.17% monthly pace that compounds to 2%",
        color=COLORS["target"], fontsize=8, transform=ax.transAxes,
    )
    ax.axhline(0, color=COLORS["neutral"], linewidth=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels([d.strftime("%b\n%Y") for d in plot.index])
    ax.set_title("July's 0.2% Monthly Prints Still Sit Above a 2% Path", fontweight="bold")
    ax.set_ylabel("Month-over-month (%)")
    ax.set_xlabel("Month")
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "pce-monthly-pace.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_spending(df: pd.DataFrame) -> None:
    plot = df.loc["2023-01-01":, ["real_pce_yoy", "saving_rate"]].dropna()
    fig, ax1 = plt.subplots(figsize=(8.0, 4.6))
    ax2 = ax1.twinx()
    ax2.grid(False)
    ax2.spines["top"].set_visible(False)
    ax1.plot(plot.index, plot["real_pce_yoy"], color=COLORS["target"], linewidth=1.9,
             label="Real PCE YoY")
    ax2.plot(plot.index, plot["saving_rate"], color=COLORS["core"], linewidth=1.8,
             label="Saving rate")
    july = pd.Timestamp("2026-07-01")
    if july in plot.index:
        ax2.scatter(july, plot.loc[july, "saving_rate"], s=40, color=COLORS["core"],
                    edgecolors="white", linewidth=0.8, zorder=5)
        ax2.text(july, plot.loc[july, "saving_rate"],
                 f"  July saving rate {plot.loc[july, 'saving_rate']:.1f}%",
                 color=COLORS["core"], fontsize=8, fontweight="bold", va="center")
    extend_xlim(ax1, plot.index, 0.22)
    ax1.set_title("Real Spending Stayed Soft as Households Saved 3.0% of DPI", fontweight="bold")
    ax1.set_ylabel("Real PCE, year-over-year (%)", color=COLORS["target"])
    ax2.set_ylabel("Personal saving rate (% of DPI)", color=COLORS["core"])
    ax1.set_xlabel("Month")
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()
    fig.savefig(FIG_DIR / "real-pce-saving.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_labor(df: pd.DataFrame) -> None:
    plot = df.loc["2025-01-01":"2026-07-01", ["payroll_change_k", "unrate"]].dropna()
    fig, ax1 = plt.subplots(figsize=(8.0, 4.6))
    ax2 = ax1.twinx()
    ax2.grid(False)
    ax2.spines["top"].set_visible(False)
    colors = [COLORS["target"] if v >= 0 else COLORS["headline"] for v in plot["payroll_change_k"]]
    ax1.bar(plot.index, plot["payroll_change_k"], width=20, color=colors, alpha=0.7, edgecolor="white")
    ax2.plot(plot.index, plot["unrate"], color=COLORS["core"], linewidth=1.9)
    ax1.axhline(0, color=COLORS["neutral"], linewidth=0.8)
    july = pd.Timestamp("2026-07-01")
    if july in plot.index:
        val = float(plot.loc[july, "payroll_change_k"])
        ax1.scatter(july, val, s=40, color=COLORS["headline"], edgecolors="white",
                    linewidth=0.8, zorder=5)
        ax1.text(july, val, f"  July {val:+.0f}k", color=COLORS["headline"],
                 fontsize=8, fontweight="bold", va="center")
    extend_xlim(ax1, plot.index, 0.12)
    ax1.set_title("July Payrolls Fell 23,000 with Unemployment Still Near 4.1%", fontweight="bold")
    ax1.set_ylabel("Monthly payroll change (thousands)")
    ax2.set_ylabel("Unemployment rate (%)", color=COLORS["core"])
    ax1.set_xlabel("Month")
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    plt.tight_layout()
    fig.savefig(FIG_DIR / "labor-dashboard.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def chart_policy(df: pd.DataFrame) -> None:
    plot = df.loc["2023-01-01":, ["fed_target_upper", "pce_core_yoy"]].dropna()
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    ax.fill_between(
        plot.index,
        plot["fed_target_upper"],
        plot["pce_core_yoy"],
        color=COLORS["light"],
        alpha=0.35,
        label="Gap (not a model of r*)",
    )
    ax.plot(plot.index, plot["fed_target_upper"], color=COLORS["core"], linewidth=1.9,
            label="Fed funds upper bound")
    ax.plot(plot.index, plot["pce_core_yoy"], color=COLORS["headline"], linewidth=1.9,
            label="Core PCE YoY")
    last = plot.iloc[-1]
    ax.scatter(plot.index[-1], last["fed_target_upper"], s=40, color=COLORS["core"],
               edgecolors="white", linewidth=0.8, zorder=5)
    ax.scatter(plot.index[-1], last["pce_core_yoy"], s=40, color=COLORS["headline"],
               edgecolors="white", linewidth=0.8, zorder=5)
    ax.text(plot.index[-1], last["fed_target_upper"],
            f"  Funds {last['fed_target_upper']:.2f}%",
            color=COLORS["core"], fontsize=8, fontweight="bold", va="center")
    ax.text(plot.index[-1], last["pce_core_yoy"],
            f"  Core {last['pce_core_yoy']:.1f}%",
            color=COLORS["headline"], fontsize=8, fontweight="bold", va="center")
    extend_xlim(ax, plot.index, 0.16)
    ax.set_title("Policy Rate Ceiling versus Core PCE (Not an r* Model)", fontweight="bold")
    ax.set_ylabel("Percent")
    ax.set_xlabel("Month")
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fed-funds-core-pce.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    setup_style()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CLEAN_DIR / "main.csv", index_col="date", parse_dates=True).sort_index()
    chart_yoy(df)
    chart_monthly(df)
    chart_spending(df)
    chart_labor(df)
    chart_policy(df)
    print("Wrote five PNGs in", FIG_DIR)


if __name__ == "__main__":
    main()
