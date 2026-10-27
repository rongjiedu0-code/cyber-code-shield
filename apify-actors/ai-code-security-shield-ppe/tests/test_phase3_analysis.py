import unittest
from src.shield_engine import audit, settings


class ActualAnalysisTests(unittest.TestCase):
    def test_default_inputs_are_really_parsed_and_scanned(self):
        config = settings({'mode': 'audit'})
        reports = [audit(file['content']) for file in config['files']]
        self.assertEqual(len(reports), 3)
        self.assertTrue(all(report['ast_parse_status'] == 'parsed' for report in reports))
        self.assertTrue(all(report['total_warnings'] > 0 for report in reports))

    def test_shell_keyword_ast_detection_and_cwe(self):
        report = audit('import subprocess\nsubprocess.run(command,\n shell=True)')
        self.assertIn('CWE-78', report['cwe_ids'])
        self.assertNotIn('CWE-200', report['cwe_ids'])
        self.assertIn('CCS-AST-009', [finding['rule_id'] for finding in report['warnings']])

    def test_constructed_path_read_has_ast_finding(self):
        report = audit('from pathlib import Path\n(Path(root) / requested_path).read_text()')
        self.assertIn('CWE-22', report['cwe_ids'])
        self.assertIn('CCS-AST-010', [finding['rule_id'] for finding in report['warnings']])

    def test_missing_route_auth_maps_to_cwe306(self):
        report = audit('app=FastAPI()\n@app.delete("/agents/{id}")\ndef delete(id):\n return agents.pop(id)')
        self.assertIn('CWE-306', report['cwe_ids'])

    def test_no_unverified_cve_identifier_is_fabricated(self):
        report = audit('eval(user_input)')
        self.assertEqual(report['cve_ids'], [])
        self.assertIn('No CVE asserted', report['cve_match_status'])

    def test_safe_snippet_has_no_false_cwe_claim(self):
        report = audit('total = sum([1, 2, 3])')
        self.assertEqual(report['cwe_ids'], [])
        self.assertEqual(report['verdict'], 'PASS')
