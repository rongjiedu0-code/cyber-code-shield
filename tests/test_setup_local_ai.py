import argparse
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import setup_local_ai as ccs


class PatchPromptTest(unittest.TestCase):
    def test_patch_prompt_includes_ascii_only_guidance(self):
        prompt = ccs.build_patch_prompt(
            "suggest_patch",
            "# Project context",
            "Add ASCII-only username validation",
            "## File: app.py\n\n```text\npass\n```",
        )
        self.assertIn("ASCII-only", prompt)
        self.assertIn("islower()", prompt)
        self.assertIn("isalpha()", prompt)
        self.assertIn("isalnum()", prompt)


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


class PolicyWarningsTest(unittest.TestCase):
    def make_project_file(self, relative_path="app.py", text="def f():\n    return 1\n"):
        temp_dir = tempfile.TemporaryDirectory()
        project_path = Path(temp_dir.name)
        file_path = project_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")
        self.addCleanup(temp_dir.cleanup)
        return project_path, file_path

    def warning_codes(self, warnings):
        return {warning["code"] for warning in warnings}

    def warning_by_code(self, warnings, code):
        return next(warning for warning in warnings if warning["code"] == code)

    def test_clean_patch_has_no_policy_warnings(self):
        project_path, file_path = self.make_project_file()
        response = """```diff
--- app.py
+++ app.py
@@ -1,2 +1,2 @@
 def f():
-    return 1
+    return 2
```"""
        self.assertEqual(ccs.detect_policy_warnings(response, [file_path], project_path), [])

    def test_dependency_change_warning(self):
        project_path, file_path = self.make_project_file("requirements.txt", "")
        response = """```diff
--- requirements.txt
+++ requirements.txt
@@ -0,0 +1 @@
+requests==2.32.0
```"""
        warnings = ccs.detect_policy_warnings(response, [file_path], project_path)
        self.assertIn("DEPENDENCY_CHANGE", self.warning_codes(warnings))
        self.assertEqual(self.warning_by_code(warnings, "DEPENDENCY_CHANGE")["severity"], "review")

    def test_network_call_warning(self):
        project_path, file_path = self.make_project_file()
        response = """```diff
--- app.py
+++ app.py
@@ -1 +1,2 @@
+response = requests.get(url)
```"""
        warnings = ccs.detect_policy_warnings(response, [file_path], project_path)
        self.assertIn("NETWORK_CALL", self.warning_codes(warnings))
        self.assertEqual(self.warning_by_code(warnings, "NETWORK_CALL")["severity"], "high")

    def test_shell_execution_warning(self):
        project_path, file_path = self.make_project_file()
        response = """```diff
--- app.py
+++ app.py
@@ -1 +1,2 @@
+subprocess.run(command)
```"""
        warnings = ccs.detect_policy_warnings(response, [file_path], project_path)
        self.assertIn("SHELL_EXECUTION", self.warning_codes(warnings))
        self.assertEqual(self.warning_by_code(warnings, "SHELL_EXECUTION")["severity"], "high")

    def test_secret_file_warning(self):
        project_path, file_path = self.make_project_file(".env", "")
        response = """```diff
--- .env
+++ .env
@@ -0,0 +1 @@
+TOKEN=value
```"""
        warnings = ccs.detect_policy_warnings(response, [file_path], project_path)
        self.assertIn("SECRET_OR_ENV_FILE", self.warning_codes(warnings))
        self.assertEqual(self.warning_by_code(warnings, "SECRET_OR_ENV_FILE")["severity"], "high")

    def test_ci_cd_warning(self):
        project_path, file_path = self.make_project_file(".github/workflows/ci.yml", "")
        response = """```diff
--- .github/workflows/ci.yml
+++ .github/workflows/ci.yml
@@ -0,0 +1 @@
+name: ci
```"""
        warnings = ccs.detect_policy_warnings(response, [file_path], project_path)
        self.assertIn("CI_CD_CHANGE", self.warning_codes(warnings))
        self.assertEqual(self.warning_by_code(warnings, "CI_CD_CHANGE")["severity"], "review")

    def test_sensitive_area_warning(self):
        project_path, file_path = self.make_project_file("src/auth/login.py", "")
        response = """```diff
--- src/auth/login.py
+++ src/auth/login.py
@@ -0,0 +1 @@
+def login(): pass
```"""
        warnings = ccs.detect_policy_warnings(response, [file_path], project_path)
        self.assertIn("SENSITIVE_AREA", self.warning_codes(warnings))
        self.assertEqual(self.warning_by_code(warnings, "SENSITIVE_AREA")["severity"], "review")

    def test_enterprise_strict_escalates_review_warnings(self):
        project_path, file_path = self.make_project_file("requirements.txt", "")
        response = """```diff
--- requirements.txt
+++ requirements.txt
@@ -0,0 +1 @@
+requests==2.32.0
```"""
        warnings = ccs.detect_policy_warnings(response, [file_path], project_path, policy_profile="enterprise-strict")
        self.assertEqual(self.warning_by_code(warnings, "DEPENDENCY_CHANGE")["severity"], "high")
        self.assertIn("ENTERPRISE_REVIEW_REQUIRED", self.warning_codes(warnings))

    def test_china_privacy_profile_detects_privacy_and_cloud_signals(self):
        project_path, file_path = self.make_project_file()
        response = """```diff
--- app.py
+++ app.py
@@ -0,0 +1,3 @@
+logger.info(user.email)
+client = OpenAI()
+print("手机号", phone)
```"""
        warnings = ccs.detect_policy_warnings(response, [file_path], project_path, policy_profile="china-privacy")
        self.assertIn("PRIVACY_DATA_FLOW", self.warning_codes(warnings))
        self.assertIn("LOGGING_OR_TELEMETRY", self.warning_codes(warnings))
        self.assertIn("CLOUD_PROVIDER_OR_EGRESS", self.warning_codes(warnings))

    def test_supply_chain_profile_detects_package_scripts(self):
        project_path, file_path = self.make_project_file("package.json", "{}")
        response = """```diff
--- package.json
+++ package.json
@@ -1 +1,5 @@
+{
+  "scripts": {
+    "postinstall": "node scripts/install.js"
+  }
+}
```"""
        warnings = ccs.detect_policy_warnings(response, [file_path], project_path, policy_profile="supply-chain")
        self.assertEqual(self.warning_by_code(warnings, "DEPENDENCY_CHANGE")["severity"], "high")
        self.assertIn("PACKAGE_SCRIPT_CHANGE", self.warning_codes(warnings))

    def test_rendered_report_includes_compliance_and_policy_sections(self):
        project_path, file_path = self.make_project_file()
        rendered = ccs.render_patch_suggestion(
            "suggest_patch",
            project_path,
            {"chat_model": "local", "api_base": "http://localhost:11434", "inference_provider": "ollama", "model_tier": "deep"},
            [file_path],
            "## Confidence\nHigh",
            "Fix bug",
            True,
            180,
            800,
            validation_warnings=[],
            policy_warnings=[ccs.make_policy_warning("NETWORK_CALL", "review", "Network call")],
            policy_warnings_enabled=True,
        )
        self.assertIn("## Compliance evidence", rendered)
        self.assertIn("## Policy warnings", rendered)
        self.assertIn("Report ID: `ccs-patch-", rendered)
        self.assertIn("Prompt SHA-256: `unavailable`", rendered)
        self.assertIn("Model response SHA-256:", rendered)
        self.assertIn("sha256=", rendered)
        self.assertIn("Policy warning count: `1`", rendered)
        self.assertIn("Model tier: `deep`", rendered)
        self.assertIn("Policy profile: `basic`", rendered)
        self.assertIn("not formal compliance certifications", rendered)

    def test_rendered_report_records_disabled_policy_scan(self):
        project_path, file_path = self.make_project_file()
        rendered = ccs.render_patch_suggestion(
            "suggest_patch",
            project_path,
            {"chat_model": "local", "api_base": "http://localhost:11434", "inference_provider": "ollama", "model_tier": "custom"},
            [file_path],
            "## Confidence\nHigh",
            "Fix bug",
            True,
            180,
            800,
            validation_warnings=[],
            policy_warnings=[],
            policy_warnings_enabled=False,
        )
        self.assertIn("Policy scan status: `disabled`", rendered)
        self.assertIn("Policy warning scan disabled by user", rendered)

    def test_rendered_report_records_selected_policy_profile(self):
        project_path, file_path = self.make_project_file()
        rendered = ccs.render_patch_suggestion(
            "suggest_patch",
            project_path,
            {"chat_model": "local", "api_base": "http://localhost:11434", "inference_provider": "ollama", "model_tier": "custom"},
            [file_path],
            "## Confidence\nHigh",
            "Fix bug",
            True,
            180,
            800,
            policy_profile="enterprise-strict",
        )
        self.assertIn("Policy profile: `enterprise-strict`", rendered)
        self.assertIn("Enterprise Strict", rendered)


class PatchAuditReportTest(unittest.TestCase):
    def make_project_file(self, relative_path="app.py", text="secret = 'local-only'\n"):
        temp_dir = tempfile.TemporaryDirectory()
        project_path = Path(temp_dir.name)
        file_path = project_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")
        self.addCleanup(temp_dir.cleanup)
        return project_path, file_path

    def test_hash_text_sha256_is_stable(self):
        self.assertEqual(
            ccs.hash_text_sha256("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )
        self.assertNotIn("abc", ccs.hash_text_sha256("abc"))

    def test_collect_reviewed_file_hashes_uses_relative_paths(self):
        text = "secret = 'local-only'\n"
        project_path, file_path = self.make_project_file(text=text)
        reviewed_files = ccs.collect_reviewed_file_hashes(project_path, [file_path])
        self.assertEqual(reviewed_files[0]["path"], "app.py")
        file_bytes = file_path.read_bytes()
        self.assertEqual(reviewed_files[0]["sha256"], hashlib.sha256(file_bytes).hexdigest())
        self.assertEqual(reviewed_files[0]["size_bytes"], len(file_bytes))
        self.assertNotIn("local-only", json.dumps(reviewed_files, ensure_ascii=False))

    def test_build_patch_report_data_contains_audit_fields(self):
        project_path, file_path = self.make_project_file()
        report = ccs.build_patch_report_data(
            "suggest_patch",
            project_path,
            {"chat_model": "local", "api_base": "http://localhost:11434", "inference_provider": "ollama", "model_tier": "deep"},
            [file_path],
            "## Confidence\nHigh",
            "Fix bug",
            True,
            180,
            800,
            prompt_text="# Relevant file snippets\nsecret = 'local-only'",
            validation_warnings=["warn"],
            policy_warnings=[ccs.make_policy_warning("NETWORK_CALL", "high", "Network call")],
        )
        self.assertEqual(report["schema_version"], "cyber-code-shield.patch-report.v1")
        self.assertTrue(report["report_id"].startswith("ccs-patch-"))
        self.assertEqual(report["audit"]["prompt_sha256"], ccs.hash_text_sha256("# Relevant file snippets\nsecret = 'local-only'"))
        self.assertEqual(report["audit"]["model_response_sha256"], ccs.hash_text_sha256("## Confidence\nHigh"))
        self.assertEqual(report["audit"]["reviewed_files"][0]["path"], "app.py")
        self.assertEqual(report["audit"]["policy_warning_count"], 1)
        self.assertEqual(report["policy"]["profile"], "basic")
        self.assertEqual(report["audit"]["policy_profile"], "basic")

    def test_build_patch_report_data_records_selected_policy_profile(self):
        project_path, file_path = self.make_project_file()
        report = ccs.build_patch_report_data(
            "suggest_patch",
            project_path,
            {"chat_model": "local", "api_base": "http://localhost:11434", "inference_provider": "ollama", "model_tier": "deep"},
            [file_path],
            "## Confidence\nHigh",
            "Fix bug",
            True,
            180,
            800,
            policy_profile="supply-chain",
        )
        self.assertEqual(report["policy"]["profile"], "supply-chain")
        self.assertEqual(report["audit"]["policy_profile"], "supply-chain")
        self.assertIn("not formal compliance certifications", report["policy"]["disclaimer"])

    def test_render_patch_report_json_excludes_internal_prompt_text(self):
        project_path, file_path = self.make_project_file()
        prompt = "# Relevant file snippets\nsecret = 'local-only'"
        report = ccs.build_patch_report_data(
            "suggest_patch",
            project_path,
            {"chat_model": "local", "api_base": "http://localhost:11434", "inference_provider": "ollama", "model_tier": "custom"},
            [file_path],
            "## Confidence\nHigh",
            "Fix bug",
            True,
            180,
            800,
            prompt_text=prompt,
        )
        rendered = ccs.render_patch_report_by_format(report, "json")
        parsed = json.loads(rendered)
        self.assertEqual(parsed["report_id"], report["report_id"])
        self.assertEqual(parsed["audit"]["prompt_sha256"], ccs.hash_text_sha256(prompt))
        self.assertEqual(parsed["audit"]["model_response_sha256"], ccs.hash_text_sha256("## Confidence\nHigh"))
        self.assertEqual(parsed["audit"]["reviewed_files"][0]["path"], "app.py")
        self.assertNotIn("# Relevant file snippets", rendered)

    def test_default_json_patch_output_path_uses_json_extension(self):
        project_path = Path("/project")
        output_path = ccs.get_default_patch_output_path(project_path, "suggest_patch", "json")
        self.assertEqual(output_path.suffix, ".json")
        self.assertIn("CYBER_CODE_SHIELD_PATCH_SUGGEST_PATCH_", output_path.name)

    def test_parser_accepts_patch_report_format(self):
        args = ccs.build_parser().parse_args([
            "--suggest-patch",
            "--project",
            ".",
            "--task",
            "x",
            "--patch-report-format",
            "json",
        ])
        self.assertEqual(args.patch_report_format, "json")

    def test_parser_accepts_policy_profile_and_report_bundle(self):
        args = ccs.build_parser().parse_args([
            "--suggest-patch",
            "--project",
            ".",
            "--task",
            "x",
            "--policy-profile",
            "enterprise-strict",
            "--report-bundle",
            "--bundle-output",
            "bundle-dir",
        ])
        self.assertEqual(args.policy_profile, "enterprise-strict")
        self.assertTrue(args.report_bundle)
        self.assertEqual(args.bundle_output, "bundle-dir")

    def test_parser_rejects_invalid_policy_profile(self):
        with self.assertRaises(SystemExit):
            ccs.build_parser().parse_args([
                "--suggest-patch",
                "--project",
                ".",
                "--task",
                "x",
                "--policy-profile",
                "invalid",
            ])


class ReportBundleTest(unittest.TestCase):
    def make_patch_report(self):
        temp_dir = tempfile.TemporaryDirectory()
        project_path = Path(temp_dir.name)
        file_path = project_path / "app.py"
        file_path.write_text("secret = 'local-only'\n", encoding="utf-8")
        self.addCleanup(temp_dir.cleanup)
        report = ccs.build_patch_report_data(
            "suggest_patch",
            project_path,
            {"chat_model": "local", "api_base": "http://localhost:11434", "inference_provider": "ollama", "model_tier": "custom"},
            [file_path],
            "## Confidence\nHigh",
            "Fix bug",
            True,
            180,
            800,
            validation_warnings=["warn"],
            policy_warnings=[ccs.make_policy_warning("NETWORK_CALL", "high", "Network call")],
            policy_profile="enterprise-strict",
        )
        return project_path, report

    def test_write_report_bundle_creates_expected_artifacts(self):
        project_path, report = self.make_patch_report()
        bundle_dir = project_path / "bundle"
        environment_summary = {"schema_version": "cyber-code-shield.environment-summary.v1", "api_base_is_local": True}
        manifest = ccs.write_report_bundle(bundle_dir, report, environment_summary)
        expected_files = {
            "report.md",
            "report.json",
            "reviewed-files.json",
            "policy-warnings.json",
            "validation-warnings.json",
            "environment-summary.json",
            "manifest.json",
        }
        self.assertEqual({path.name for path in bundle_dir.iterdir()}, expected_files)
        self.assertFalse(manifest["source_files_modified_automatically"])
        self.assertEqual(manifest["report_id"], report["report_id"])
        self.assertEqual({artifact["path"] for artifact in manifest["artifacts"]}, expected_files - {"manifest.json"})
        for artifact in manifest["artifacts"]:
            text = (bundle_dir / artifact["path"]).read_text(encoding="utf-8")
            self.assertEqual(artifact["sha256"], ccs.hash_text_sha256(text))
        reviewed_files_text = (bundle_dir / "reviewed-files.json").read_text(encoding="utf-8")
        self.assertIn("sha256", reviewed_files_text)
        self.assertNotIn("local-only", reviewed_files_text)
        policy_warnings = json.loads((bundle_dir / "policy-warnings.json").read_text(encoding="utf-8"))
        self.assertEqual(policy_warnings["policy"]["profile"], "enterprise-strict")
        validation_warnings = json.loads((bundle_dir / "validation-warnings.json").read_text(encoding="utf-8"))
        self.assertEqual(validation_warnings["response_warning_count"], 1)

    def test_write_report_bundle_rejects_existing_directory(self):
        project_path, report = self.make_patch_report()
        bundle_dir = project_path / "bundle"
        bundle_dir.mkdir()
        with self.assertRaises(FileExistsError):
            ccs.write_report_bundle(bundle_dir, report, {"schema_version": "x"})


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

    def test_validate_patch_response_does_not_warn_when_todo_is_only_removed(self):
        project_path, file_path = self.make_project_file("def f():\n    # TODO: implement\n    pass\n")
        response = """## Confidence
High
## Missing context
None identified
## Files to change
app.py
## Explanation
Implement it.
## Suggested patch
```diff
--- app.py
+++ app.py
@@ -1,3 +1,2 @@
 def f():
-    # TODO: implement
-    pass
+    return 1
```
## Validation steps
Run it.
## Risks or assumptions
None.
"""
        warnings = ccs.validate_patch_response(response, [file_path], project_path)
        self.assertFalse(any("占位内容" in warning for warning in warnings))

    def test_validate_patch_response_warns_for_ascii_constraint_with_unicode_check(self):
        project_path, file_path = self.make_project_file("def valid(username):\n    pass\n")
        response = """## Confidence
High
## Missing context
None identified
## Files to change
app.py
## Explanation
Implement ASCII validation.
## Suggested patch
```diff
--- app.py
+++ app.py
@@ -1,2 +1,5 @@
 def valid(username):
-    pass
+    # ASCII only usernames.
+    return all(char.islower() or char.isdigit() or char == "_" for char in username)
```
## Validation steps
Run it.
## Risks or assumptions
None.
"""
        warnings = ccs.validate_patch_response(response, [file_path], project_path)
        self.assertTrue(any("ASCII-only" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
