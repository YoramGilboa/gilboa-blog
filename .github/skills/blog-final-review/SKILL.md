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
   - time references are consistent (prose dates from stats, US month/day);
   - `##` section titles are unnumbered;
   - conclusions do not overstate the evidence;
   - composite indexes are not treated as winning every subtest when task-level
     gaps exist in the post's data.
2. **Flow**
   - opening, sections, transitions, and conclusion form a linear narrative;
   - adjacent sections are not repetitive;
   - headline and body framing agree;
   - one-off posts include the deliberate-exception frame when required.
3. **Consistency**
   - caveats match methodology and "Note on data";
   - terminology and units are stable;
   - audience implications follow from the analysis;
   - no single-item bullet lists; no bare `{python}` expressions;
   - underperformance peers shown when a "weaker" section exists;
   - `pagetitle:`, `description:`, and `categories:` match
     posts.instructions.md Frontmatter and Categories. If pagetitle copies
     the H1, misses prints, or is outside 50-65 characters (cap 70), or if
     description is jargon-first or too long for a snippet, or if tags fail
     the catalog rules, invoke `blog-seo-tags` then continue. Do not rewrite
     the H1 `title:` here;
   - `title`, `description`, and `pagetitle` are three distinct fields.
     Fail an H1 that uses "X, not Y" when Y is a different kind of claim
     from X.

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
automatic fixes; and identify the next step. Quote `title`, `description`,
`pagetitle`, and `categories` as the title block for human review. If a fix
changed a visual element, require another chart review before final review.
