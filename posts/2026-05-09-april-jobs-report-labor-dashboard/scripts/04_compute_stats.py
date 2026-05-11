"""
Compute the single source of truth for all numbers used in this post.

The April 2026 Employment Situation press release is the canonical source for
the headline payroll change, the unemployment rate, the average hourly earnings
level and percent changes, the household-survey employment change, and the
sector-by-sector month-over-month industry detail. Those values are recorded
here as constants and written to stats/summary_stats.json so that the .qmd
prose, the executive-summary cards, and the figures all reference the same
file. Edit this script (not the markdown) to update any number.

Usage (from the post directory):
  python scripts/04_compute_stats.py
"""

from __future__ import annotations

import json
from pathlib import Path


STATS = {
    "report_month": "April 2026",
    "release_date": "May 8, 2026",
    "data_current_as_of": "May 8, 2026",

    # Establishment survey headline (BLS Table B-1)
    "payroll_april": 115,
    "payroll_consensus": 180,
    "payroll_march_revised": 185,
    "payroll_feb_revision": -23,

    # Unemployment rate (BLS Table A-1)
    "unrate_april": 4.3,
    "unrate_march": 4.3,

    # Household survey (BLS Table A-1)
    "household_emp_change_april": -226,

    # Wages (BLS Table B-3)
    "ahe_level": 37.41,
    "ahe_mom_pct": 0.2,
    "ahe_prodnonsup_mom_pct": 0.3,

    # Selected industry detail (BLS Table B-1, thousands of jobs)
    "sector_health_care": 37,
    "sector_transport_warehouse": 30,
    "sector_retail": 22,
    "sector_federal_gov": -9,
    "sector_information": -13,

    # Forward calendar
    "fomc_window": "May 6 to 7, 2026",
    "next_cpi_release": "May 12, 2026",

    # Company-specific reference for the Spirit Airlines bankruptcy theorizing
    # in the sectoral and What-it-means sections. Headcount is approximate
    # public-domain order of magnitude as of late 2024 / early 2025.
    "spirit_airlines_employees": 13000,
    "spirit_airlines_filing_month": "May 2026",
}


def main() -> int:
    out = Path(__file__).resolve().parent.parent / "stats" / "summary_stats.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(STATS, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(STATS)} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
