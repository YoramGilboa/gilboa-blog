---
description: Start a new gilboa.blog post using the blog-post-create skill
---

Follow the **blog-post-create** skill in `.github/skills/blog-post-create/SKILL.md`
end-to-end. Do not improvise your own workflow.

Standing constraints (do not ask me about these again):
- Create branch `post/YYYY-MM-DD-slug` before touching any file.
- Copy `posts/drafts/_template/` to `posts/drafts/YYYY-MM-DD-slug/`.
- Keep `draft: true` until I explicitly approve.
- Merge to `main` and publish ONLY after I say "good to go" or "approved".
- Run blog-data-validate before building the pipeline, blog-seo-tags after
  the draft exists, blog-chart-review after charts, blog-final-review before
  presenting to me.
- At human review, show title (H1), description (dek), pagetitle, and tags.
- Report absolute paths for every file you create or move.

Post brief (I will fill this in):

TOPIC: ${input:topic}

LOCKED FACTS
- <official prints go here — do not invent numbers>

FILES TO TOUCH
- index.qmd, scripts/, figures/ under the new draft folder only

TONE / AUDIENCE
- Neutral, high-school-graduate readable, per posts.instructions.md