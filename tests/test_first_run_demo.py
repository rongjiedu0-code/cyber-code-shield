"""Regression coverage for the first commands a new user copies from the docs."""
import hashlib
import re
import shlex
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
import setup_local_ai as ccs


class FirstRunDemoTest(unittest.TestCase):
    def run_cli(self, args):
        return subprocess.run(
            [sys.executable, "-B", str(REPO_ROOT / "setup_local_ai.py"), *args],
            cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20,
        )

    def test_bundled_traceback_matches_the_primary_error(self):
        project = REPO_ROOT / "examples/demo-buggy-project"
        fixture = project / "traceback.txt"
        self.assertTrue(fixture.is_file(), "The first-run fixture must ship with the repository")
        locations = ccs.extract_error_locations_from_text(project, fixture.read_text(encoding="utf-8"))
        primary = ccs.get_primary_error_location(locations)
        self.assertEqual(primary["relative_path"], "app.py")
        self.assertEqual(primary["line"], 2)
        self.assertEqual((project / "app.py").read_text(encoding="utf-8").splitlines()[1].strip(),
                         "return username.strip().lower()")

    def test_documented_error_demo_runs_from_a_clean_checkout(self):
        project = REPO_ROOT / "examples/demo-buggy-project"
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in project.iterdir() if p.is_file()}
        for document in ["README.md", "README.zh-CN.md", "examples/demo-buggy-project/README.md"]:
            with self.subTest(document=document):
                content = (REPO_ROOT / document).read_text(encoding="utf-8")
                commands = [line.strip() for block in re.findall(r"```bash\n(.*?)```", content, flags=re.S)
                            for line in block.splitlines()
                            if line.startswith("python setup_local_ai.py --fix-error") and "--dry-run" in line]
                self.assertTrue(commands, "The documented dry-run command must exist")
                for command in commands:
                    result = self.run_cli(shlex.split(command)[2:])
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("app.py:2", result.stdout)
                    self.assertIn("username", result.stdout)
                    self.assertIn("Dry-run", result.stdout)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in project.iterdir() if p.is_file()}
        self.assertEqual(after, before, "Dry-run must not create reports or modify demo source")

    def test_todo_preview_runs_without_a_local_model(self):
        result = self.run_cli(["--complete-todo", "--project", "examples/demo-todo-project",
                               "--files", "app.py", "--context-lite", "--dry-run"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("is_valid_username", result.stdout)
        self.assertIn("ASCII", result.stdout)
        self.assertIn("Dry-run", result.stdout)

    def test_cli_help_points_to_the_versioned_traceback(self):
        result = self.run_cli(["--help"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("examples/demo-buggy-project/traceback.txt", result.stdout)
        self.assertNotIn("examples/demo-buggy-project/error.log", result.stdout)


if __name__ == "__main__":
    unittest.main()
