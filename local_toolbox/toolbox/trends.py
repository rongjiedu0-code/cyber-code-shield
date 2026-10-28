from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from statistics import median
from urllib.parse import urlencode
from .common import integer, money
from .urls import fetch_json, clean_url

ENDPOINTS = {
    '百度': 'https://top.baidu.com/api/board?platform=wise&tab=realtime',
    '哔哩哔哩': 'https://s.search.bilibili.com/main/hotword',
    '今日头条': 'https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc',
}


def baidu_words(value):
    if isinstance(value, list):
        for item in value:
            yield from baidu_words(item)
    elif isinstance(value, dict):
        if isinstance(value.get('word'), str) and not value.get('isTop'):
            yield value
        for key in ('data', 'cards', 'content'):
            if key in value:
                yield from baidu_words(value[key])


def parse_trends(source, payload):
    if not isinstance(payload, dict):
        raise ValueError('趋势返回格式错误')
    if source == '百度':
        if payload.get('success') is not True or not isinstance(payload.get('data'), dict):
            raise ValueError('百度接口暂不可用')
        entries = list(baidu_words(payload))
    elif source == '哔哩哔哩':
        entries = payload.get('list')
        if entries is None:
            entries = (payload.get('data') or {}).get('trending', {}).get('list')
        if payload.get('code', 0) != 0 or not isinstance(entries, list):
            raise ValueError('哔哩哔哩接口暂不可用')
    elif source == '今日头条':
        entries = payload.get('data')
        if not isinstance(entries, list):
            raise ValueError('头条接口暂不可用')
    else:
        raise ValueError('未知来源')
    rows = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        title = item.get('word') or item.get('keyword') or item.get('show_name') or item.get('Title')
        if not isinstance(title, str) or not title.strip():
            continue
        rank = len(rows)+1
        base = {'百度': 'https://www.baidu.com/s?', '哔哩哔哩': 'https://search.bilibili.com/all?',
                '今日头条': 'https://www.toutiao.com/search/?'}[source]
        url = item.get('Url') or base + urlencode({'wd' if source == '百度' else 'keyword': title})
        rows.append({'热词': title.strip(), '排名': rank, '热度线索分': max(0, 100-(rank-1)*2),
            '来源': source, '来源链接': clean_url(url), '采集时间': datetime.now(timezone.utc).isoformat(),
            '说明': '公开热榜快照；线索分按排名计算，不代表销量或需求增速'})
    return rows


def collect_trends(limit=30, keyword='', get_json=None):
    integer(limit, '条数', 1, 100)
    errors = []
    for source, endpoint in ENDPOINTS.items():
        try:
            rows = parse_trends(source, (get_json or fetch_json)(endpoint))
            return [r for r in rows if not keyword or keyword.lower() in r['热词'].lower()][:limit]
        except (OSError, ValueError, RuntimeError) as error:
            errors.append(source + ': ' + type(error).__name__)
    raise RuntimeError('公开热榜暂不可用；可导入商品报价表继续本地分析。' + '；'.join(errors))


def analyze_products(records):
    staged, groups = [], defaultdict(list)
    for index, row in enumerate(records, 2):
        name = str(row.get('商品名称') or row.get('标题') or row.get('name') or '').strip()
        if not name:
            raise ValueError(f'第 {index} 行缺少商品名称')
        sale_raw = row.get('销售价', row.get('售价', row.get('price')))
        cost_raw = row.get('采购成本', row.get('进货价', row.get('cost')))
        sale = money(sale_raw, '销售价', False)
        cost = money(cost_raw, '采购成本', False)
        freight = money(row.get('运费', '0') or '0', '运费', False)
        raw_rate = str(row.get('手续费率', '0') or '0').strip()
        try:
            rate = Decimal(raw_rate.rstrip('%')) / (100 if raw_rate.endswith('%') else 1)
        except InvalidOperation as error:
            raise ValueError('手续费率请填数字比例或带 % 的百分数') from error
        if not rate.is_finite() or not 0 <= rate <= 1:
            raise ValueError('手续费率请填 0–1 的比例或带 % 的百分数')
        fee = (sale*rate).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        profit = sale-cost-freight-fee
        category = str(row.get('品类') or '未分类')
        url = row.get('商品链接') or row.get('链接') or ''
        if url:
            url = clean_url(url)
        staged.append({'商品名称': name, '品类': category, '销售价': str(sale), '采购成本': str(cost),
            '运费': str(freight), '手续费': str(fee), '估算毛利': str(profit),
            '估算毛利率': str((profit/sale*100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)) + '%' if sale else '不适用',
            '异常': '是' if profit < 0 else '否', '商品链接': url,
            '说明': '基于导入报价估算；未包含广告、退货、税费和人工，不是利润承诺'})
        groups[category].append(sale)
    for row in staged:
        values = groups[row['品类']]
        row['同表品类价格带'] = f'{min(values)}–{max(values)}'
        row['同表品类中位价'] = str(median(values))
    return staged
