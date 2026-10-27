"""Strict test double: charges and storage are separate failure boundaries."""
import copy
import json
from contextlib import contextmanager, ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


@contextmanager
def simulated_live_sources():
    """Deterministic HTTP boundaries for tests; never imported by production."""
    project = Path(__file__).resolve().parent
    name = json.loads((project / '.actor/actor.json').read_text(encoding='utf-8'))['name']
    with ExitStack() as stack:
        if name == 'startup-pain-point-radar-ppe':
            rows = [dict(source='hackernews', title='Wish there was a tool for manual spreadsheet ' + str(i),
                         text='Manual reconciliation is frustrating and too expensive. A painful workaround.',
                         url='https://example.com/test-live/' + str(i), native_id=str(i), is_fixture=False) for i in range(3)]
            for method in ('hn_items', 'github_items', 'reddit_items'):
                stack.enter_context(patch('src.radar_engine.' + method, return_value=rows))
        if name == 'cn-trend-radar-ppe':
            rows = [dict(title_cn=title, url='https://example.com/test-live/' + str(index), rank=index + 1,
                         raw_heat=100 - index, source='baidu_public_trends',
                         ingestion_endpoint='https://top.baidu.com/api/board')
                    for index, title in enumerate(['无线蓝牙耳机', '便携咖啡杯', '智能手表'])]
            stack.enter_context(patch('src.trend_engine.public_trend_rows', return_value=rows))
        yield


class FakeActor:
    def __init__(self, data=None, max_events=999, store=None):
        self.data = data or {}
        self.max_events = max_events
        self.store = store if store is not None else {}
        self.events = []
        self.items = []
        self.keys = {}
        self.fail_push = False
        self.fail_charge = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_input(self):
        return copy.deepcopy(self.data)

    async def get_value(self, key):
        return copy.deepcopy(self.store.get(key))

    async def set_value(self, key, value):
        self.store[key] = copy.deepcopy(value)

    async def charge(self, event_name, *, idempotency_key, count=1):
        if count != 1:
            raise AssertionError('Every item must charge exactly once')
        if self.fail_charge:
            raise ConnectionError('Response lost after uncertain charge')
        if idempotency_key in self.keys:
            return SimpleNamespace(charged_count=1, event_charge_limit_reached=False)
        if len(self.events) >= self.max_events:
            return SimpleNamespace(charged_count=0, event_charge_limit_reached=True)
        self.keys[idempotency_key] = event_name
        self.events.append({'event_name': event_name, 'idempotency_key': idempotency_key})
        return SimpleNamespace(charged_count=1, event_charge_limit_reached=len(self.events) >= self.max_events)

    async def push_data(self, item):
        if self.fail_push:
            raise ConnectionError('Dataset unavailable')
        self.items.append(copy.deepcopy(item))
