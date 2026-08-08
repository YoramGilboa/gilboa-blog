"""Clean the official FRED and ADP downloads into chart-ready tables."""

from pathlib import Path

import pandas as pd


POST_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = POST_DIR / "data" / "raw"
CLEAN_DIR = POST_DIR / "data" / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)


def clean_fred() -> None:
    fred = pd.read_csv(RAW_DIR / "fred_series.csv", parse_dates=["date"])
    monthly_ids = [
        "PAYEMS",
        "USPRIV",
        "ADPMNUSNERSA",
        "ADPMINDEDHLTNERSA",
        "USEHS",
        "CES6561000001",
        "CES6562000001",
        "CES6562000101",
        "CES6562400001",
        "UNRATE",
        "CIVPART",
        "CES0500000003",
    ]
    monthly = (
        fred[fred["series_id"].isin(monthly_ids)]
        .pivot(index="date", columns="series_id", values="value")
        .sort_index()
    )
    for series_id in ["ADPMNUSNERSA", "ADPMINDEDHLTNERSA"]:
        monthly[series_id] = monthly[series_id] / 1000
    monthly.to_csv(CLEAN_DIR / "labor_monthly.csv")

    claims = (
        fred[fred["series_id"].eq("ICSA")][["date", "value"]]
        .rename(columns={"value": "initial_claims"})
        .sort_values("date")
    )
    claims["claims_4wk_avg"] = claims["initial_claims"].rolling(4).mean()
    claims.to_csv(CLEAN_DIR / "claims_weekly.csv", index=False)


def clean_adp() -> None:
    ner = pd.read_csv(RAW_DIR / "adp_ner" / "ADP_NER_history.csv", parse_dates=["date"])
    ner = ner[ner["timestep"].eq("M")].copy()
    ner = ner.sort_values(["agg_RIS", "category", "date"])
    ner["employment_k"] = ner["NER_SA"] / 1000
    ner["monthly_change_k"] = ner.groupby(["agg_RIS", "category"])["employment_k"].diff()

    national = ner[
        (ner["agg_RIS"].eq("National")) & (ner["category"].eq("U.S."))
    ].sort_values("date")
    national[["date", "employment_k", "monthly_change_k"]].to_csv(
        CLEAN_DIR / "adp_national.csv", index=False
    )

    industries = ner[ner["agg_RIS"].eq("Industry")].sort_values(["category", "date"])
    industries[["date", "category", "employment_k", "monthly_change_k"]].to_csv(
        CLEAN_DIR / "adp_industry.csv", index=False
    )

    pay = pd.read_csv(RAW_DIR / "adp_pay" / "ADP_PAY_history.csv", parse_dates=["date"])
    mobility = pay[pay["agg"].eq("Worker Type")].copy()
    mobility = mobility.rename(
        columns={
            "category": "worker_type",
            "median pay change": "median_pay_change_pct",
            "median annual pay": "median_annual_pay",
        }
    )
    mobility[["date", "worker_type", "median_pay_change_pct", "median_annual_pay"]].to_csv(
        CLEAN_DIR / "adp_pay_mobility.csv", index=False
    )


def main() -> None:
    clean_fred()
    clean_adp()
    print("Wrote four chart-ready cleaned data files.")


if __name__ == "__main__":
    main()