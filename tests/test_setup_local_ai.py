import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import setup_local_ai as ccs


class OpenAICompatibleHelpersTest(unittest.TestCase):
    def test_build_openai_compatible_chat_endpoint(self):
        self.assertEqual(
            ccs.build_openai_compatible_chat_endpoint("http://localhost:1234"),
            "http://localhost:1234/v1/chat/completions",
        )
        self.assertEqual(
            ccs.build_openai_compatible_chat_endpoint("http://localhost:1234/v1"),
            "http://localhost:1234/v1/chat/completions",
        )
        self.assertEqual(
            ccs.build_openai_compatible_chat_endpoint("http://localhost:1234/v1/chat/completions"),
            "http://localhost:1234/v1/chat/completions",
        )

    def test_parse_openai_compatible_chat_response(self):
        response = {
            "choices": [
                {"message": {"content": "## Confidence\nHigh"}}
            ]
        }
        self.assertEqual(ccs.parse_openai_compatible_chat_response(response), "## Confidence\nHigh")

    def test_parse_openai_compatible_chat_response_rejects_error_payload(self):
        with self.assertRaises(RuntimeError) as context:
            ccs.parse_openai_compatible_chat_response({"error": {"message": "model not found"}})
        self.assertIn("model not found", str(context.exception))


class PatchResponseValidationTest(unittest.TestCase):
    def make_project_file(self, text):
        temp_dir = tempfile.TemporaryDirectory()
        project_path = Path(temp_dir.name)
        file_path = project_path / "app.py"
        file_path.write_text(text, encoding="utf-8")
        self.addCleanup(temp_dir.cleanup)
        return project_path, file_path

    def test_validate_patch_response_warns_for_noop_diff(self):
        project_path, file_path = self.make_project_file("def f():\n    return 1\n")
        response = """## Confidence
High
## Missing context
None identified
## Files to change
app.py
## Explanation
No-op.
## Suggested patch
```diff
--- app.py
+++ app.py
@@ -1,2 +1,2 @@
-def f():
+def f():
```
## Validation steps
Run it.
## Risks or assumptions
None.
"""
        warnings = ccs.validate_patch_response(response, [file_path], project_path)
        self.assertTrue(any("no-op" in warning for warning in warnings))

    def test_validate_patch_response_warns_for_unknown_diff_path(self):
        project_path, file_path = self.make_project_file("def f():\n    return 1\n")
        response = """## Confidence
High
## Missing context
None identified
## Files to change
other.py
## Explanation
Change other file.
## Suggested patch
```diff
--- other.py
+++ other.py
@@ -1 +1 @@
-old
+new
```
## Validation steps
Run it.
## Risks or assumptions
None.
"""
        warnings = ccs.validate_patch_response(response, [file_path], project_path)
        self.assertTrue(any("未提供上下文" in warning for warning in warnings))

    def test_validate_patch_response_warns_when_primary_error_line_not_touched(self):
        project_path, file_path = self.make_project_file("def f(raw_username):\n    return username.strip()\n")
        response = """## Confidence
High
## Missing context
None identified
## Files to change
app.py
## Explanation
Wrong variable.
## Suggested patch
```diff
--- app.py
+++ app.py
@@ -1,2 +1,2 @@
-def f(raw_username):
+def f(raw_username):
     return username.strip()
```
## Validation steps
Run it.
## Risks or assumptions
None.
"""
        locations = [{
            "file_path": file_path,
            "relative_path": "app.py",
            "line": 2,
            "column": None,
            "raw": "File \"app.py\", line 2",
            "kind": "python_traceback",
        }]
        warnings = ccs.validate_patch_response(response, [file_path], project_path, error_locations=locations)
        self.assertTrue(any("主故障行" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
