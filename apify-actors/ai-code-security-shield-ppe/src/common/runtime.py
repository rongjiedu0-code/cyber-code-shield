"""Run-scoped, durable billing receipts. No production mock or silent SDK fallback."""
import asyncio
import hashlib
import json
import os
from contextlib import aclosing
from datetime import datetime, timezone
from pathlib import Path


class AmbiguousChargeError(RuntimeError):
    pass


class SourceUnavailable(RuntimeError):
    """Every configured upstream failed; a free, labeled fallback is permitted."""


def is_demo_record(item):
    """Conservative billing guard; never erase provenance before inspecting it."""
    return (bool(item.get('is_demo')) or bool(item.get('is_fixture'))
            or str(item.get('source', '')).lower() in {'demo', 'demo_fallback', 'fixture'}
            or item.get('billing_mode') == 'free-demo')


def resolve_input(data, actor_name):
    if not isinstance(data, dict):
        raise ValueError('Actor input must be an object')
    schema_path = Path(__file__).resolve().parents[2] / '.actor/input_schema.json'
    if not data:
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        data = {key: definition['default'] for key, definition in schema['properties'].items()}
    else:
        data = dict(data)
    real_mode = 'audit' if actor_name == 'ai-code-security-shield-ppe' else 'online'
    if os.getenv('OFFLINE_MODE') == '1':
        data['mode'] = 'offline'
    elif data.get('mode') in {'offline', 'demo'}:
        # Legacy Phase 2 prefills cannot accidentally keep a cloud Actor static.
        data['mode'] = real_mode
    else:
        data.setdefault('mode', real_mode)
    return data


def stable_id(prefix, *parts):
    payload = json.dumps(parts, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    return prefix + hashlib.sha256(payload.encode('utf-8')).hexdigest()


def integer(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer in [{minimum}, {maximum}]')
    return value


def string_list(value, name, max_count=20):
    if not isinstance(value, list) or not 1 <= len(value) <= max_count:
        raise ValueError(f'{name} must contain 1-{max_count} strings')
    if any(not isinstance(x, str) or not x.strip() or len(x) > 500 for x in value):
        raise ValueError(f'{name}: nonempty strings of at most 500 characters required')
    return list(dict.fromkeys(x.strip() for x in value))


class ReceiptLedger:
    """Sequential writer only. Receipts last for the Actor run, beyond SDK's 180s cache.

    Persist intent BEFORE charging. An uncertain response fails closed after a restart.
    Dataset push and KV write cannot be atomic: a crash between them may duplicate
    an output row, but recovery does not bill that row again. Consumers dedup on id.
    """
    def __init__(self, actor):
        self.actor = actor
        self.state = None

    async def load(self):
        run_id = os.getenv('ACTOR_RUN_ID', 'local')
        stored = await self.actor.get_value('PPE_RECEIPTS_V1')
        if stored is not None and (not isinstance(stored, dict) or stored.get('version') != 1):
            raise ValueError('Invalid PPE receipt store')
        self.state = stored if stored and stored.get('run_id') == run_id else {
            'version': 1, 'run_id': run_id, 'entries': {}}

    async def save(self):
        # Do not persist source code or secrets; store only hashes/status.
        await self.actor.set_value('PPE_RECEIPTS_V1', self.state)

    async def authorize(self, event, key):
        ledger_key = event + ':' + key
        receipt = self.state['entries'].get(ledger_key)
        if receipt:
            if receipt['status'] == 'pending':
                raise AmbiguousChargeError('Uncertain previous charge; reconcile receipt ' + ledger_key)
            return receipt['status'], receipt['limit_reached']
        self.state['entries'][ledger_key] = {'status': 'pending'}
        await self.save()
        result = await self.actor.charge(event_name=event, count=1, idempotency_key=key)
        if result.charged_count != 1:
            self.state['entries'].pop(ledger_key)
            await self.save()
            if not result.event_charge_limit_reached:
                raise RuntimeError('PPE charge returned zero without a budget limit; check event pricing')
            return 'denied', True
        self.state['entries'][ledger_key] = {
            'status': 'charged', 'limit_reached': bool(result.event_charge_limit_reached)}
        await self.save()
        return 'charged', bool(result.event_charge_limit_reached)

    async def deliver(self, event, item):
        if is_demo_record(item):
            raise ValueError('Billing guard: demo/fixture records cannot enter the charging ledger')
        status, limit = await self.authorize(event, item['id'])
        if status == 'denied':
            return False, True
        if status == 'pushed':
            return False, limit
        await self.actor.push_data(item)
        self.state['entries'][event + ':' + item['id']]['status'] = 'pushed'
        await self.save()
        return True, limit


async def execute(actor, settings, collector, event, actor_name, fallback_collector=None):
    """Live first. Initialize billing only after the first real result exists.

    Offline/all-source-failed fallback bypasses Actor.charge entirely, including
    actor-start. A successful empty feed remains empty, not invented demo data.
    """
    async with actor:
        config = settings(resolve_input(await actor.get_input() or {}, actor_name))
        manager = actor.get_charging_manager() if hasattr(actor, 'get_charging_manager') else None
        pricing = manager.get_pricing_info() if manager else None
        if pricing:
            if pricing.per_event_prices.get('apify-default-dataset-item', 0) != 0:
                raise ValueError('Default dataset event must be free; use only explicit per-item billing')
        ledger = None
        output = []
        free_ids = set()
        custom_charges = 0
        fallback_reason = None
        offline = os.getenv('OFFLINE_MODE') == '1'

        async def push_free(item, reason, demo=True):
            if item['id'] in free_ids:
                return
            free_ids.add(item['id'])
            if demo:
                item = dict(item, original_source=item.get('source'), source='demo_fallback',
                            is_demo=True, is_fixture=True, data_mode='demo', billing_mode='free-demo',
                            fallback_reason=reason, demo_notice='Bundled fallback example, not live data. No Actor.charge call is made.')
            else:
                item = dict(item, is_demo=False, data_mode=config['mode'], billing_mode='unmonetized')
            await actor.push_data(item)
            output.append(item)

        async def fallback(reason):
            if fallback_collector is None:
                raise SourceUnavailable('No fallback collector configured')
            demo_config = dict(config, mode='offline', maxItems=min(3, config['maxItems']))
            async with aclosing(fallback_collector(demo_config)) as items:
                async for item in items:
                    await push_free(item, reason)

        if offline:
            fallback_reason = 'OFFLINE_MODE=1'
            await fallback(fallback_reason)
        else:
            try:
                async with aclosing(collector(config)) as items:
                    async for item in items:
                        # This guard comes BEFORE both startup and item charging.
                        if is_demo_record(item):
                            await push_free(item, 'record explicitly marked as demo/fixture')
                            continue
                        if pricing and not pricing.is_pay_per_event:
                            await push_free(item, 'PPE not configured', demo=False)
                            continue
                        if ledger is None:
                            if pricing:
                                for name in ('actor-start', event):
                                    if pricing.per_event_prices.get(name, 0) <= 0:
                                        raise ValueError('Missing positive flat price for event: ' + name)
                            ledger = ReceiptLedger(actor)
                            await ledger.load()
                            status, _ = await ledger.authorize('actor-start', stable_id('start_', actor_name))
                            if status == 'denied':
                                break
                            if status == 'charged':
                                custom_charges += 1
                            if manager and manager.calculate_max_event_charge_count_within_limit(event) == 0:
                                break
                        item = dict(item, is_demo=False, is_fixture=False, data_mode=config['mode'], billing_mode='ppe')
                        pushed, stop = await ledger.deliver(event, item)
                        if pushed:
                            custom_charges += 1
                            output.append(item)
                        if stop:
                            break
            except SourceUnavailable as exc:
                if output:
                    raise
                fallback_reason = str(exc)
                await fallback(fallback_reason)
        await actor.set_value('RUN_SUMMARY', {
            'actor': actor_name, 'mode': config.get('mode', 'audit'),
            'pushed_this_attempt': len(output),
            'real_results': sum(not item.get('is_demo') for item in output),
            'demo_results': sum(bool(item.get('is_demo')) for item in output),
            'custom_events_this_attempt': custom_charges,
            'fallback_reason': fallback_reason,
            'completed_at': datetime.now(timezone.utc).isoformat()})
        return output


def entrypoint(runner):
    if os.getenv('ACTOR_TEST_PAY_PER_EVENT', '').lower() == 'true' and os.getenv('APIFY_IS_AT_HOME', '').lower() not in {'true', '1'}:
        # SDK local defaults also price synthetic Dataset writes at $1. Explicit
        # free Dataset pricing avoids double counting and paid-but-dropped rows.
        if 'APIFY_ACTOR_PRICING_INFO' not in os.environ:
            project = Path(__file__).resolve().parents[2]
            pricing = json.loads((project / 'pricing.suggested.json').read_text(encoding='utf-8'))
            events = pricing['pricingPerEvent']['actorChargeEvents']
            for definition in events.values():
                definition['eventPriceUsd'] = 1.0
            events['apify-default-dataset-item'] = {
                'eventTitle': 'Dataset output (free)', 'eventPriceUsd': 0.0}
            os.environ['APIFY_ACTOR_PRICING_INFO'] = json.dumps(pricing)
            os.environ['APIFY_CHARGED_ACTOR_EVENT_COUNTS'] = '{"actor-start": 0}'
    from apify import Actor
    # Production always uses the real SDK. Local dry-run requires its official flag.
    if not Actor.is_at_home() and os.getenv('ACTOR_TEST_PAY_PER_EVENT', '').lower() != 'true':
        raise RuntimeError('Local run: set ACTOR_TEST_PAY_PER_EVENT=true; use examples/offline input')
    asyncio.run(runner(Actor))
