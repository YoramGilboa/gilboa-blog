import json
import tempfile
import unittest
from pathlib import Path

from tools.audit_repository import audit_repository


class AuditRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_post(self, relative: str, figures: tuple[str, ...] = ()) -> set[str]:
        post = self.root / relative
        post.mkdir(parents=True)
        (post / "index.qmd").write_text("---\ntitle: Test\n---\n", encoding="utf-8")

        freeze = self.root / "_freeze" / relative / "index"
        metadata = freeze / "execute-results" / "html.json"
        metadata.parent.mkdir(parents=True)
        markdown = "\n".join(f"![Chart](figure-html/{name})" for name in figures)
        metadata.write_text(json.dumps({"result": {"markdown": markdown}}), encoding="utf-8")
        figure_dir = freeze / "figure-html"
        figure_dir.mkdir(parents=True)
        for name in figures:
            (figure_dir / name).write_bytes(b"png")

        return {
            f"{relative}/index.qmd",
            f"_freeze/{relative}/index/execute-results/html.json",
            *{
                f"_freeze/{relative}/index/figure-html/{name}"
                for name in figures
            },
        }

    def test_valid_source_and_freeze_pair_passes(self):
        tracked = self.add_post("posts/2026-01-01-test-post", ("fig-test-output-1.png",))
        self.assertEqual(audit_repository(self.root, tracked), [])

    def test_orphan_freeze_is_reported(self):
        tracked = self.add_post("posts/2026-01-01-test-post")
        (self.root / "posts/2026-01-01-test-post/index.qmd").unlink()
        findings = audit_repository(self.root, tracked)
        self.assertIn("orphan-freeze", {finding.code for finding in findings})

    def test_draft_without_freeze_is_allowed(self):
        draft = self.root / "posts/drafts/2026-01-01-test-draft"
        draft.mkdir(parents=True)
        (draft / "index.qmd").write_text("---\ndraft: true\n---\n", encoding="utf-8")
        tracked = {"posts/drafts/2026-01-01-test-draft/index.qmd"}
        self.assertEqual(audit_repository(self.root, tracked), [])

    def test_stale_figure_is_reported(self):
        tracked = self.add_post("posts/2026-01-01-test-post", ("fig-test-output-1.png",))
        extra = (
            self.root
            / "_freeze/posts/2026-01-01-test-post/index/figure-html/fig-old-output-1.png"
        )
        extra.write_bytes(b"png")
        tracked.add(extra.relative_to(self.root).as_posix())
        findings = audit_repository(self.root, tracked)
        self.assertIn("stale-freeze-figure", {finding.code for finding in findings})

    def test_generated_tracked_file_is_reported(self):
        tracked = self.add_post("posts/2026-01-01-test-post")
        generated = self.root / "_site/index.html"
        generated.parent.mkdir(parents=True)
        generated.write_text("generated", encoding="utf-8")
        tracked.add("_site/index.html")
        findings = audit_repository(self.root, tracked)
        self.assertIn("tracked-generated", {finding.code for finding in findings})

    def test_legacy_post_path_is_allowed(self):
        tracked = self.add_post("posts/20260501 April FOMC decision")
        self.assertEqual(audit_repository(self.root, tracked), [])


if __name__ == "__main__":
    unittest.main()
