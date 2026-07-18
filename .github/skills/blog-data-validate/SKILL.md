---
name: blog-data-validate
description: Validate FRED series and BEA NIPA tables for identity, availability, frequency, and freshness. Use before creating or changing a post data pipeline.
argument-hint: "<post path or series identifiers>"
---

# Blog data validation

## Inputs

Accept either a post directory containing `scripts/01_fetch_data.py` or a list
of FRED series IDs and BEA table codes.

## Workflow

1. Extract every external identifier and expected frequency.
2. Require `FRED_API_KEY` for FRED metadata and observations. If absent, report
   the registration URL and stop the FRED check clearly.
3. For each FRED series:
   - call `get_series_info`;
   - fetch observations;
   - report official title, frequency, units, and latest non-null date;
   - mark invalid identifiers `INVALID`;
   - mark unexpectedly old data `STALE`.
4. For each BEA table:
   - require `BEA_API_KEY`;
   - call the BEA Data API with the expected dataset and frequency;
   - reject API error payloads and empty results;
   - report table identity and latest period.
5. When overlapping FRED and BEA measures exist, compare their latest values
   and flag differences above 0.1 percentage point.
6. Suggest alternatives for invalid FRED IDs using `fred.search`.

## Output

Return a compact table with status, identifier, official description,
frequency, and latest date. Summarize counts of `VALID`, `STALE`, and `INVALID`.
Do not write fetch code until all required identifiers are valid and freshness
is understood.

Useful registration URLs:

- FRED: https://fred.stlouisfed.org/docs/api/api_key.html
- BEA: https://apps.bea.gov/api/signup/
