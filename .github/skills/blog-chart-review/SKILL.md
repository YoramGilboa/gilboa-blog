---
name: blog-chart-review
description: Render, screenshot, and visually review every chart and the homepage card against gilboa.blog quality standards. Use after chart changes and before final editorial review.
argument-hint: "<post directory>"
---

# Blog chart review

This is a visual-only gate.

## Workflow

1. Read the post and inventory every `#| label: fig-*` block, caption, and
   chart type.
2. Confirm the matching freeze metadata is current; render if needed.
3. Start `quarto preview --port 4200 --no-browser` with the root `.venv`.
4. Use available browser or IDE preview tools to screenshot every chart at
   normal width and 400px. If screenshot tooling is unavailable, report the
   gate as blocked rather than inferring visual quality from code alone.
5. Check every chart for:
   - label overlap and clipping;
   - legend or annotation occlusion;
   - readable axes and dates;
   - one visible grid on dual-axis charts;
   - readable bar labels and color contrast;
   - endpoint dots and consistent direct-label style;
   - mobile legibility;
   - fragility if values move.
6. Review the homepage listing card for one description, correct categories,
   date/author, and preview image.
7. Confirm frontmatter has `description`, a real `image`, no `subtitle`, and
   lowercase space-separated categories.
8. Search the post and stats script for `# MANUAL:`, `placeholder`, and `TODO`.

## Output

Report each figure as PASS or FAIL with numbered defects and a concrete fix.
Also report mobile, listing-card, frontmatter, and manual-value status. Give an
overall count and do not hand off to final review until all visual checks pass.

Mechanical padding or clipping defects may be fixed directly, followed by a
rerender and complete visual recheck. Do not automatically change subjective
chart type or color choices.
