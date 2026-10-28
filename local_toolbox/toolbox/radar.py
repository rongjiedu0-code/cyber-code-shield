"""Chinese public-content leads; scores are review aids, never verified demand."""
from datetime import datetime, timezone
from .common import integer
from .urls import fetch_json, clean_url

PAIN_WORDS = {'手动': 15, '对账': 18, '耗时': 20, '麻烦': 12, '求推荐': 15,
              '有没有': 10, '太贵': 18, '重复': 12, '痛点': 18, '效率': 10,
              'manual': 15, 'spreadsheet': 14, 'wish there was': 25, 'workaround': 18}
COMMUNITY_ENDPOINT = 'https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1'


def pain_score(title, text=''):
    combined = (str(title) + ' ' + str(text)).lower()
    matches = [word for word in PAIN_WORDS if word in combined]
    score = min(100, 20 + sum(PAIN_WORDS[word] for word in matches))
    return score, matches


def score_four_dimensions(intensity, workaround, budget, space):
    values = (intensity, workaround, budget, space)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 10 for v in values):
        raise ValueError('四维分数必须在 0–10 之间')
    score = round(intensity*3 + workaround*2.5 + budget*2.5 + space*2, 1)
    return score, '暂不投入' if budget <= 2 or space <= 2 else ('优先人工验证' if score >= 75 else '观察验证')


def analyze_signals(records, keyword=''):
    rows, seen = [], set()
    for item in records:
        title = str(item.get('标题') or item.get('title') or item.get('内容') or '').strip()
        content = str(item.get('内容') or item.get('content') or item.get('desc') or '')
        if not title or keyword and keyword.lower() not in (title + content).lower():
            continue
        url = item.get('来源链接') or item.get('url') or ''
        if url:
            url = clean_url(str(url))
        identity = url or title + '\n' + content
        if identity in seen:
            continue
        seen.add(identity)
        score, matches = pain_score(title, content)
        finance = any(k in title+content for k in ('订单', '对账', '财务', '流水'))
        rows.append({'标题': title, '内容摘录': content[:1200], '商机分': score,
            '命中词': '、'.join(matches), '判读': '有需求措辞，待回访验证' if matches else '普通公开内容，尚无需求证据',
            '建议方向': '订单与财务流程自动化' if finance else '先访谈作者确认实际场景',
            '来源': item.get('来源') or item.get('source') or '用户导入', '来源链接': url,
            '采集时间': item.get('采集时间') or datetime.now(timezone.utc).isoformat()})
    return sorted(rows, key=lambda r: -r['商机分'])


def collect_community(limit=30, keyword='', get_json=None):
    integer(limit, '条数', 1, 100)
    payload = (get_json or fetch_json)(COMMUNITY_ENDPOINT)
    data = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(data, dict) or payload.get('code') != 0 or not isinstance(data.get('list'), list):
        raise ValueError('公开社区返回格式变化，请稍后再试或导入本地内容表')
    raw = []
    for item in data['list']:
        bvid = item.get('bvid', '')
        if not str(bvid).isalnum() or not item.get('title'):
            continue
        raw.append({'title': item['title'], 'desc': item.get('desc', ''),
                    'url': 'https://www.bilibili.com/video/' + bvid,
                    'source': '哔哩哔哩公开社区内容'})
    return analyze_signals(raw, keyword)[:limit]
