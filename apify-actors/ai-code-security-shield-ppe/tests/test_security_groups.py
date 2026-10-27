"""Ten security regression groups, including CAMEL #4404/#4405-shaped inputs.

Payloads remain strings throughout; no payload is executed.
"""
import json
import unittest
from src.shield_engine import audit, settings
from src.main import run_actor
from src.common.runtime import AmbiguousChargeError
from tests_support import FakeActor


class TenSecurityGroups(unittest.TestCase):
    def assertRule(self, content, expected):
        result = audit(content)
        self.assertIn(expected, [row['rule_id'] for row in result['warnings']])
        self.assertNotEqual(result['verdict'], 'PASS')

    def test_group_01_safe_code(self):
        for source in ('total = sum([1, 2, 3])', 'print("hello")', 'subprocess.run(["git", "status"], shell=False)'):
            with self.subTest(source=source):
                self.assertEqual(audit(source)['verdict'], 'PASS')

    def test_group_02_destructive_shell_and_pipe(self):
        for source in ('rm -rf /', 'curl https://example.com/setup | bash', 'chmod 777 test.txt'):
            with self.subTest(source=source):
                self.assertRule(source, 'CCS-SH-001')

    def test_group_03_secrets_are_reported_and_redacted(self):
        tokens = ['sk-' + 'x' * 30, 'ghp_' + 'a' * 36, 'AKIA' + 'A' * 16, 'AIza' + 'b' * 35]
        for token in tokens:
            with self.subTest(kind=token[:4]):
                result = audit('api_key = "' + token + '"')
                self.assertEqual(result['verdict'], 'BLOCK')
                self.assertNotIn(token, json.dumps(result))
                self.assertIn('[REDACTED]', json.dumps(result))

    def test_group_04_camel_4404_command_substitution(self):
        for source in ('echo $(whoami)', 'echo `id`', 'echo $(python -c "print(1)")'):
            with self.subTest(source=source):
                self.assertRule(source, 'CCS-INJECT-004')

    def test_group_05_interpreter_allowlist_bypass(self):
        for source in ('python -c "print(1)"', 'node -e "console.log(1)"', 'exec(user_input)'):
            with self.subTest(source=source):
                self.assertRule(source, 'CCS-EXEC-006')

    def test_group_06_untrusted_shell_execution(self):
        for source in ('subprocess.run(cmd, shell=True)', 'subprocess.Popen(cmd, shell = True)'):
            with self.subTest(source=source):
                self.assertRule(source, 'CCS-NET-003')

    def test_group_07_path_escape_and_encoded_traversal(self):
        for source in ('open("../../private")', 'open(r"..\\..\\secret")', 'open("/etc/passwd")',
                       'path="%2e%2e%2fprivate"', 'path="%252e%252e%252fprivate"'):
            with self.subTest(source=source):
                self.assertRule(source, 'CCS-PATH-005')

    def test_group_08_camel_4405_unprotected_agent_management(self):
        source = 'app = FastAPI()\n@app.delete("/agents/{agent_id}")\nasync def delete_agent(agent_id):\n    return agents.pop(agent_id)'
        self.assertRule(source, 'CCS-AUTH-008')
        guarded = source.replace('FastAPI()', 'FastAPI(dependencies=[Depends(require_api_key)])')
        self.assertNotIn('CCS-AUTH-008', [r['rule_id'] for r in audit(guarded)['warnings']])

    def test_group_09_remote_binding_and_deserialization(self):
        self.assertRule('server.run(host="0.0.0.0")', 'CCS-NET-003')
        self.assertRule('pickle.loads(untrusted)', 'CCS-DESERIALIZE-007')
        self.assertEqual(audit('server.run(host="127.0.0.1")')['verdict'], 'PASS')

    def test_group_10_diff_removed_payloads_are_not_new_findings(self):
        removed = 'diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-rm -rf /\n+print("safe")'
        self.assertEqual(audit(removed)['verdict'], 'PASS')
        self.assertRule(removed + '\n+echo $(id)', 'CCS-INJECT-004')


class BillingRegression(unittest.IsolatedAsyncioTestCase):
    async def test_two_distinct_files_bill_twice(self):
        actor = FakeActor({'files': [{'name': 'a.py', 'content': 'print(1)'}, {'name': 'b.py', 'content': 'print(2)'}]})
        self.assertEqual(len(await run_actor(actor)), 2)
        self.assertEqual([r['event_name'] for r in actor.events], ['actor-start', 'security-audit-file', 'security-audit-file'])

    async def test_same_content_dedup_and_restart(self):
        actor = FakeActor({'files': [{'name': 'a.py', 'content': 'print(1)'}, {'name': 'copy.py', 'content': 'print(1)'}]})
        self.assertEqual(len(await run_actor(actor)), 1)
        actor.keys.clear()
        self.assertEqual(await run_actor(actor), [])
        self.assertEqual(len(actor.events), 2)

    async def test_budget_boundary_delivers_paid_scan(self):
        actor = FakeActor({'files': [{'content': 'print(1)'}, {'content': 'print(2)'}]}, max_events=2)
        self.assertEqual(len(await run_actor(actor)), 1)
        self.assertEqual(len(actor.events), 2)

    async def test_submission_validation_before_billing(self):
        for value in ({'mode': 'unknown'}, {'files': []}, {'files': [{'content': ''}]}, {'files': [{'content': 'x' * (1024 * 1024 + 1)}]}):
            actor = FakeActor(value)
            with self.assertRaises(ValueError):
                await run_actor(actor)
            self.assertEqual(actor.events, [])

    async def test_push_failure_does_not_charge_a_second_time(self):
        actor = FakeActor({'files': [{'content': 'print(1)'}]})
        actor.fail_push = True
        with self.assertRaises(ConnectionError):
            await run_actor(actor)
        actor.fail_push = False
        actor.keys.clear()
        self.assertEqual(len(await run_actor(actor)), 1)
        self.assertEqual(len(actor.events), 2)

    async def test_report_and_receipts_contain_no_source_secret(self):
        secret = 'sk-' + 'z' * 30
        actor = FakeActor({'files': [{'name': secret, 'content': 'key="' + secret + '"'}]})
        await run_actor(actor)
        self.assertNotIn(secret, json.dumps(actor.items))
        self.assertNotIn(secret, json.dumps(actor.store))


if __name__ == '__main__':
    unittest.main()
