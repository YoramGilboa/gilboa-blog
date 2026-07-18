---
name: blog-final-review
description: Perform the final non-visual editorial and analytical review of a rendered gilboa.blog post and write its PASS or FAIL status artifact. Use after visual chart review passes.
argument-hint: "<post directory>"
---

# Blog final review

## Preconditions

- the post renders successfully;
- `blog-chart-review` passes;
- `stats/summary_stats.json` is current.

## Review

Read `index.qmd`, summary stats, and pipeline scripts needed for traceability.

Evaluate:

1. **Accuracy**
   - claims match computed values and direction;
   - time references are consistent;
   - conclusions do not overstate the evidence.
2. **Flow**
   - opening, sections, transitions, and conclusion form a linear narrative;
   - adjacent sections are not repetitive;
   - headline and body framing agree.
3. **Consistency**
   - caveats match methodology;
   - terminology and units are stable;
   - audience implications follow from the analysis.

Apply only low-risk wording, transition, and terminology fixes directly. Do
not auto-fix high-impact analytical issues; return FAIL with remediation.

## Status artifact

Write `stats/final_review_status.json` on every run:

```json
{
  "status": "PASS",
  "reviewed_at": "2026-06-27T12:34:56Z",
  "reviewer": "blog-final-review",
  "notes": "Short summary of checks and fixes."
}
```

Use `FAIL` when required work remains.

## Output

Report status plus one-line accuracy, flow, and consistency results; list
automatic fixes; and identify the next step. If a fix changed a visual element,
require another chart review before final review.
