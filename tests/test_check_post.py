import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import check_post


class CheckPostTests(unittest.TestCase):
    def test_missing_canonical_html_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "posts/drafts/2026-11-14-test/index.qmd"
            source.parent.mkdir(parents=True)
            source.write_text("---\ndraft: true\n---\n", encoding="utf-8")
            (source.parent / "index.html").write_text("Not canonical", encoding="utf-8")
            issues, warnings = check_post.add_rendered_output_checks(root, source.relative_to(root).as_posix(), source)
            self.assertEqual(len(issues), 1)
            self.assertEqual(warnings, [])

    def test_draft_render_routes_output_and_freeze_without_changing_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            relative = "posts/drafts/2026-11-14-test/index.qmd"
            post = (root / relative).parent
            post.mkdir(parents=True)
            original = b"project:\n  render: ['!posts/drafts/**']\n"
            (root / "_quarto.yml").write_bytes(original)
            (root / "styles.css").write_text("body {}", encoding="utf-8")
            (root / "favicon.png").write_bytes(b"png")
            (root / "index.qmd").write_text("Home", encoding="utf-8")
            config = {"project": {}, "website": {"favicon": "favicon.png", "site-url": "https://gilboa.blog", "navbar": {"left": [{"href": "index.qmd", "text": "Home"}], "right": [{"href": "index.xml"}]}}, "format": {"html": {"css": ["styles.css"]}}}

            def command(args, **kwargs):
                output = json.dumps({"config": config}) if args[:2] == ["quarto", "inspect"] else ""
                return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

            def render(args, **kwargs):
                local = json.loads((post / "_quarto.yml").read_text(encoding="utf-8"))
                self.assertEqual(local["project"]["render"], ["index.qmd"])
                self.assertEqual(local["website"]["draft-mode"], "unlinked")
                self.assertEqual(local["website"]["favicon"], "../../../favicon.png")
                self.assertEqual(local["format"]["html"]["css"], ["../../../styles.css"])
                self.assertEqual(local["website"]["site-url"], "https://gilboa.blog/posts/drafts/2026-11-14-test")
                self.assertEqual(local["website"]["navbar"]["left"][0]["href"], "https://gilboa.blog/")
                self.assertEqual(local["website"]["navbar"]["right"][0]["href"], "https://gilboa.blog/index.xml")
                output = Path(local["project"]["output-dir"])
                output.mkdir(parents=True)
                (output / "index.html").write_text("<h1>Draft</h1>", encoding="utf-8")
                freeze = post / "_freeze/index/execute-results"
                freeze.mkdir(parents=True)
                (freeze / "html.json").write_text("{}", encoding="utf-8")
                return subprocess.CompletedProcess(args, 0)

            with patch.object(check_post, "run_cmd", side_effect=command), patch.object(check_post.subprocess, "run", side_effect=render):
                self.assertEqual(check_post.run_render(root, relative), 0)
            self.assertEqual((root / "_quarto.yml").read_bytes(), original)
            self.assertTrue(check_post.rendered_html_path(root, relative).is_file())
            self.assertTrue((root / "_freeze/posts/drafts/2026-11-14-test/index/execute-results/html.json").is_file())
            self.assertFalse((post / "_quarto.yml").exists())
            self.assertFalse((post / "_freeze").exists())
            self.assertFalse((post / ".review-site").exists())
            self.assertEqual((root / "_site/styles.css").read_text(encoding="utf-8"), "body {}")

    def test_failed_draft_render_cleans_temporary_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            relative = "posts/drafts/2026-11-14-test/index.qmd"
            post = (root / relative).parent
            post.mkdir(parents=True)
            with patch.object(check_post, "run_cmd", return_value=subprocess.CompletedProcess([], 0, stdout="", stderr="")), patch.object(check_post, "draft_project_config", return_value={"project": {}}), patch.object(check_post.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)):
                self.assertEqual(check_post.run_render(root, relative), 1)
            self.assertFalse((post / "_quarto.yml").exists())


if __name__ == "__main__":
    unittest.main()
