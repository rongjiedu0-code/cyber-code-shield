"""Mandatory real-SDK integration tests: no skips and no cloud billing."""
import importlib.metadata
import inspect
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
EVENTS = {'startup-pain-point-radar-ppe': 'pain-point-extracted',
          'ai-code-security-shield-ppe': 'security-audit-file',
          'cn-trend-radar-ppe': 'trend-item-extracted'}


class RealSDKTests(unittest.TestCase):
    def invoke(self, budget='100', pricing=None, input_data='example', offline=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = Path(directory.name)
        kv = storage / 'key_value_stores/default'
        kv.mkdir(parents=True)
        if input_data == 'example':
            input_data = json.loads((PROJECT / 'example_input.json').read_text(encoding='utf-8'))
        if input_data is not None:
            (kv / 'INPUT.json').write_text(json.dumps(input_data), encoding='utf-8')
        env = {key: value for key, value in os.environ.items()
               if not key.upper().startswith(('APIFY_', 'ACTOR_', 'CRAWLEE_'))}
        env.update(ACTOR_TEST_PAY_PER_EVENT='true', APIFY_LOCAL_STORAGE_DIR=str(storage),
                   APIFY_PURGE_ON_START='false', ACTOR_MAX_TOTAL_CHARGE_USD=budget,
                   PYTHONUTF8='1', PYTHONIOENCODING='utf-8', OFFLINE_MODE='1' if offline else '0')
        if pricing is not None:
            env.update(APIFY_ACTOR_PRICING_INFO=json.dumps(pricing), APIFY_CHARGED_ACTOR_EVENT_COUNTS='{"actor-start": 0}')
        started = time.perf_counter()
        result = subprocess.run([sys.executable, '-c', 'from tests_support import simulated_live_sources; from src.main import main;\nwith simulated_live_sources(): main()'.replace('\\n', '\n')], cwd=PROJECT, env=env,
                                capture_output=True, text=True, encoding='utf-8', timeout=90)
        result.elapsed_seconds = time.perf_counter() - started
        jsons = [json.loads(p.read_text(encoding='utf-8')) for p in storage.rglob('*.json')]
        charges = [x for x in jsons if isinstance(x, dict) and 'event_name' in x]
        items = [x for x in jsons if isinstance(x, dict) and 'id' in x and x['id'].startswith(('pp_', 'audit_', 'trend_'))]
        return result, charges, items

    def test_real_sdk_explicit_offline_has_three_free_demo_rows_under_ten_seconds(self):
        result, charges, items = self.invoke(input_data=None, offline=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(items), 3)
        self.assertLess(result.elapsed_seconds, 10)
        self.assertTrue(all(row['is_demo'] and row['is_fixture'] for row in items))
        self.assertTrue(all(row['billing_mode'] == 'free-demo' for row in items))
        self.assertEqual([row for row in charges if row['event_price_usd'] > 0], [])

    def test_real_sdk_prefilled_console_input_matches_dataset_schema(self):
        schema = json.loads((PROJECT / '.actor/input_schema.json').read_text(encoding='utf-8'))
        prefilled = {key: value['prefill'] for key, value in schema['properties'].items()}
        result, charges, items = self.invoke(input_data=prefilled)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(items), 3)
        from jsonschema import validate
        dataset_schema = json.loads((PROJECT / '.actor/dataset_schema.json').read_text(encoding='utf-8'))
        for row in items:
            validate(row, dataset_schema['fields'])
        self.assertTrue(all(not row['is_demo'] for row in items))
        self.assertEqual(len([row for row in charges if row['event_price_usd'] > 0]), 4)

    def test_sdk_version_and_idempotency_signature(self):
        self.assertEqual(importlib.metadata.version('apify'), '4.1.0')
        from apify import Actor
        self.assertIn('idempotency_key', inspect.signature(Actor.charge).parameters)

    def test_real_sdk_local_events_match_delivered_results(self):
        result, charges, items = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        paid = [x for x in charges if x['event_price_usd'] > 0]
        self.assertEqual(paid[0]['event_name'], 'actor-start')
        self.assertEqual(len(paid), len(items) + 1)
        self.assertTrue(items)
        self.assertTrue(all(x['idempotency_key'] for x in paid))

    def test_real_sdk_budget_exactly_one_result_is_delivered(self):
        result, charges, items = self.invoke('2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(items), 1)
        paid = [x for x in charges if x['event_price_usd'] > 0]
        self.assertEqual([x['event_name'] for x in paid], ['actor-start', EVENTS[PROJECT.name]])

    def test_real_sdk_zero_budget_has_no_charge_or_output(self):
        result, charges, items = self.invoke('0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(charges, [])
        self.assertEqual(items, [])

    def test_real_sdk_cheaper_result_is_affordable_after_start(self):
        pricing = json.loads((PROJECT / 'pricing.suggested.json').read_text(encoding='utf-8'))
        pricing['pricingPerEvent']['actorChargeEvents']['apify-default-dataset-item'] = {
            'eventTitle': 'Free output', 'eventPriceUsd': 0}
        unit_price = pricing['pricingPerEvent']['actorChargeEvents'][EVENTS[PROJECT.name]]['eventPriceUsd']
        from decimal import Decimal
        result, charges, items = self.invoke(str(Decimal('0.02') + Decimal(str(unit_price))), pricing)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(items), 1)

    def test_real_sdk_misconfigured_double_billing_fails_before_charge(self):
        pricing = json.loads((PROJECT / 'pricing.suggested.json').read_text(encoding='utf-8'))
        pricing['pricingPerEvent']['actorChargeEvents']['apify-default-dataset-item'] = {
            'eventTitle': 'Extra output charge', 'eventPriceUsd': 0.01}
        result, charges, items = self.invoke('100', pricing)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Default dataset event must be free', result.stderr)
        self.assertEqual(charges, [])
        self.assertEqual(items, [])


if __name__ == '__main__':
    unittest.main()
