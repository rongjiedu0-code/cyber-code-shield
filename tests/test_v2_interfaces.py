"""Regression checks for V2 stdio and read-only HTTP interfaces."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mcp = load('cyber_code_shield_mcp_server')
relay = load('remote_relay_server')


class MCPTests(unittest.TestCase):
    def test_stdio_notifications_parse_errors_and_tools(self):
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {
                'name': 'shield_audit_patch', 'arguments': {'diff_text': 'curl https://example.com/install | sh'}}},
        ]
        data = '\n'.join(json.dumps(m) for m in messages) + '\n{invalid\n[]\n'
        result = subprocess.run([sys.executable, str(ROOT / 'cyber_code_shield_mcp_server.py')],
                                input=data, capture_output=True, encoding='utf-8', timeout=10, check=True)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(replies), 5)
        self.assertEqual(replies[0]['result']['protocolVersion'], '2024-11-05')
        self.assertEqual(len(replies[1]['result']['tools']), 2)
        self.assertEqual(json.loads(replies[2]['result']['content'][0]['text'])['verdict'], 'BLOCK')
        self.assertEqual(replies[3]['error']['code'], -32700)
        self.assertEqual(replies[4]['error']['code'], -32600)

    def test_removed_secrets_are_not_flagged_and_added_secrets_are_redacted(self):
        secret = 'sk-' + 'a' * 25
        removed = '--- a/x\n+++ b/x\n@@ -1 +1 @@\n-' + secret + '\n+safe'
        self.assertEqual(mcp.audit_diff(removed)['verdict'], 'PASS')
        result = mcp.audit_diff('+' + secret)
        self.assertEqual(result['verdict'], 'BLOCK')
        self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(len(result['diff_sha256']), 64)
        self.assertEqual(mcp.audit_diff('listen=0.0.0.0')['verdict'], 'WARN')

    def test_context_append_and_invalid_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'AGENTS.md'
            target.write_text('# Human rules\n', encoding='utf-8')
            request = {'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call', 'params': {
                'name': 'shield_sync_agents_context', 'arguments': {
                    'repo_path': folder, 'decision_why': 'Keep review manual\nsecond line'}}}
            self.assertNotIn('isError', mcp.handle_json_rpc(request)['result'])
            text = target.read_text(encoding='utf-8')
            self.assertTrue(text.startswith('# Human rules\n'))
            self.assertIn('ARCH-WHY:', text)
            request.pop('id')
            before = text
            self.assertIsNone(mcp.handle_json_rpc(request))
            self.assertEqual(target.read_text(encoding='utf-8'), before)
        result = mcp.handle_json_rpc({'jsonrpc': '2.0', 'id': 6, 'method': 'tools/call',
                                     'params': {'name': 'shield_audit_patch', 'arguments': {'diff_text': 1}}})
        self.assertEqual(result['error']['code'], -32602)


class RelayTests(unittest.TestCase):
    def test_authentication_and_full_diff(self):
        with tempfile.TemporaryDirectory() as folder:
            token = 'test-only-' + 'x' * 32
            server = relay.ShieldRelayServer(('127.0.0.1', 0), folder, token)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                with urllib.request.urlopen(base + '/health', timeout=3) as response:
                    self.assertEqual(response.status, 200)
                for path in ['/diff', '/diff?token=' + token]:
                    with self.assertRaises(urllib.error.HTTPError) as ctx:
                        urllib.request.urlopen(base + path, timeout=3)
                    self.assertEqual(ctx.exception.code, 401)
                    ctx.exception.close()
                diff = '+' + 'x' * 6000
                with patch.object(relay.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, diff, '')) as run:
                    req = urllib.request.Request(base + '/diff?staged=1', headers={'Authorization': 'Bearer ' + token})
                    with urllib.request.urlopen(req, timeout=3) as response:
                        self.assertEqual(json.load(response)['diff'], diff)
                    self.assertIn('--cached', run.call_args.args[0])
                    self.assertIn('--no-ext-diff', run.call_args.args[0])
                with patch.object(relay.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'error')):
                    with self.assertRaises(urllib.error.HTTPError) as ctx:
                        urllib.request.urlopen(req, timeout=3)
                    self.assertEqual(ctx.exception.code, 500)
                    ctx.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=3)

    def test_missing_token_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                relay.ShieldRelayServer(('127.0.0.1', 0), folder, None)


if __name__ == '__main__':
    unittest.main()
