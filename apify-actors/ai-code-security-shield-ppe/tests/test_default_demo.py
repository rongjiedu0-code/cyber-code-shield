"""Demo fee hard-lock, default live policy, explicit offline, and fallback boundaries."""
import os
import unittest
from unittest.mock import patch
from src.main import run_actor
from src.common.runtime import execute, ReceiptLedger, SourceUnavailable
from tests_support import FakeActor, simulated_live_sources


class LivePolicyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.enterContext(patch.dict(os.environ, {'OFFLINE_MODE': '0'}))
        self.enterContext(simulated_live_sources())

    async def test_zero_input_defaults_to_real_collection_or_analysis(self):
        actor = FakeActor()
        rows = await run_actor(actor)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(not row['is_demo'] and not row['is_fixture'] for row in rows))
        self.assertEqual(len(actor.events), 4)

    async def test_explicit_offline_never_calls_charge_or_network(self):
        actor = FakeActor()
        actor.fail_charge = True
        with patch.dict(os.environ, {'OFFLINE_MODE': '1'}), patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('offline used network')):
            rows = await run_actor(actor)
        self.assertEqual(len(rows), 3)
        self.assertEqual(actor.events, [])
        self.assertTrue(all(row['source'] == 'demo_fallback' and row['is_demo'] for row in rows))

    async def test_old_demo_prefill_does_not_disable_live_in_cloud(self):
        actor = FakeActor({'mode': 'demo'})
        with patch.dict(os.environ, {'APIFY_IS_AT_HOME': '1', 'OFFLINE_MODE': '0'}):
            rows = await run_actor(actor)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(not row['is_demo'] for row in rows))

    async def test_offline_flag_is_explicit_even_in_cloud(self):
        actor = FakeActor()
        with patch.dict(os.environ, {'APIFY_IS_AT_HOME': '1', 'OFFLINE_MODE': '1'}):
            rows = await run_actor(actor)
        self.assertTrue(all(row['is_demo'] for row in rows))
        self.assertEqual(actor.events, [])

    async def test_every_demo_marker_is_guarded_before_startup_fee(self):
        for marker in ({'is_demo': True}, {'source': 'demo_fallback'}, {'is_fixture': True}, {'billing_mode': 'free-demo'}):
            with self.subTest(marker=marker):
                actor = FakeActor()
                actor.fail_charge = True
                async def rows(config):
                    yield dict(id='test-demo', **marker)
                output = await execute(actor, lambda data: {'mode': 'online', 'maxItems': 3}, rows, 'result', 'test')
                self.assertEqual(len(output), 1)
                self.assertEqual(actor.events, [])
                self.assertTrue(output[0]['is_demo'])

    async def test_ledger_cannot_charge_a_demo_even_if_called_directly(self):
        actor = FakeActor()
        ledger = ReceiptLedger(actor)
        await ledger.load()
        with self.assertRaises(ValueError):
            await ledger.deliver('result', {'id': 'test-demo', 'is_demo': True})
        self.assertEqual(actor.events, [])

    async def test_mixed_stream_charges_only_real_record(self):
        actor = FakeActor()
        async def rows(config):
            yield {'id': 'demo', 'is_demo': True}
            yield {'id': 'real', 'source': 'actual_source'}
            yield {'id': 'demo-2', 'source': 'demo_fallback'}
        output = await execute(actor, lambda data: {'mode': 'online', 'maxItems': 3}, rows, 'result', 'test')
        self.assertEqual(len(output), 3)
        self.assertEqual([event['event_name'] for event in actor.events], ['actor-start', 'result'])
        self.assertEqual(actor.events[-1]['idempotency_key'], 'real')

    async def test_total_source_failure_uses_free_fallback_without_startup_charge(self):
        actor = FakeActor()
        async def failed(config):
            raise SourceUnavailable('all upstreams failed')
            yield
        async def fallback(config):
            yield {'id': 'fallback'}
        output = await execute(actor, lambda data: {'mode': 'online', 'maxItems': 3}, failed, 'result', 'test', fallback)
        self.assertTrue(output[0]['is_demo'])
        self.assertEqual(actor.events, [])

    async def test_programming_errors_are_not_hidden_as_fallback(self):
        actor = FakeActor()
        async def broken(config):
            raise TypeError('implementation bug')
            yield
        with self.assertRaises(TypeError):
            await execute(actor, lambda data: {'mode': 'online', 'maxItems': 3}, broken, 'result', 'test')
        self.assertEqual(actor.events, [])

    async def test_successful_empty_source_is_not_invented_demo(self):
        actor = FakeActor()
        async def empty(config):
            if False:
                yield
        async def forbidden(config):
            raise AssertionError('unexpected fallback')
            yield
        self.assertEqual(await execute(actor, lambda data: {'mode': 'online', 'maxItems': 3}, empty, 'result', 'test', forbidden), [])
        self.assertEqual(actor.events, [])
