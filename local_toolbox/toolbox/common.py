import hashlib
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def stable_id(prefix, value):
    return prefix + hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:24]


def integer(value, name, low=1, high=100000):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f'{name} 必须是 {low}–{high} 的整数')
    return value


def money(value, name='金额', allow_negative=True):
    if isinstance(value, bool) or value is None:
        raise ValueError(name + '不能为空或布尔值')
    text = str(value).strip().replace('￥', '').replace('¥', '').replace('CNY', '').replace('RMB', '')
    if text.startswith('(') and text.endswith(')'):
        text = '-' + text[1:-1]
    if ',' in text:
        import re
        if not re.fullmatch(r'-?\d{1,3}(?:,\d{3})+(?:\.\d+)?', text):
            raise ValueError(name + '千位分隔符格式不正确')
        text = text.replace(',', '')
    try:
        result = Decimal(text)
        if not result.is_finite() or abs(result) > Decimal('1000000000000'):
            raise ValueError(name + '超出范围')
        if not allow_negative and result < 0:
            raise ValueError(name + '不能为负数')
        return result.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    except InvalidOperation as error:
        raise ValueError(name + '格式错误') from error
