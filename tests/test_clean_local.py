import tempfile
import unittest
from pathlib import Path

from tools.clean_local import cleanup_targets, remove_targets


class CleanLocalTests(unittest.TestCase):
    def test_cleanup_preserves_environment_freeze_and_post_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            generated = root / "_site/index.html"
            cache = root / "posts/example/scripts/__pycache__/module.pyc"
            environment = root / ".venv/Lib/site-packages/pkg/__pycache__/pkg.pyc"
            freeze = root / "_freeze/posts/example/index/figure-html/chart.png"
            data = root / "posts/example/data/clean/main.csv"

            for path in (generated, cache, environment, freeze, data):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"x")

            targets = cleanup_targets(root)
            relative = {path.relative_to(root).as_posix() for path in targets}
            self.assertIn("_site", relative)
            self.assertIn("posts/example/scripts/__pycache__", relative)
            self.assertFalse(any(path.startswith(".venv/") for path in relative))
            self.assertFalse(any(path.startswith("_freeze/") for path in relative))
            self.assertNotIn("posts/example/data/clean/main.csv", relative)

            remove_targets(targets)
            self.assertFalse(generated.exists())
            self.assertFalse(cache.exists())
            self.assertTrue(environment.exists())
            self.assertTrue(freeze.exists())
            self.assertTrue(data.exists())


if __name__ == "__main__":
    unittest.main()
