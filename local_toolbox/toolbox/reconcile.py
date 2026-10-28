from collections import defaultdict
from decimal import Decimal
from .common import money
from .tables import read_table, find_column, ID_HEADERS, AMOUNT_HEADERS, normalize_order_id


def reconcile_rows(orders, payments, mapping=None):
    mapping = mapping or {}
    indexes = []
    invalid = []
    for side, rows, id_choice, amount_choice in (
        ('订单', orders, 'order_id', 'order_amount'), ('流水', payments, 'payment_id', 'payment_amount')):
        index = defaultdict(list)
        key = find_column(rows, ID_HEADERS, mapping.get(id_choice, ''))
        amount = find_column(rows, AMOUNT_HEADERS, mapping.get(amount_choice, ''))
        for i, row in enumerate(rows, 2):
            try:
                identity, issue = normalize_order_id(row.get(key))
                value = money(row.get(amount))
                if issue:
                    raise ValueError(issue)
                index[identity].append(value)
            except ValueError as error:
                invalid.append({'订单号': str(row.get(key, '')), '状态': '输入待核实', '异常': '是',
                    '说明': f'{side}表第 {row.get("__row__", i)} 行：{error}', '应收': '', '实收': '', '差额': '',
                    '订单笔数': '', '流水笔数': '', '行类型': '数据质量问题'})
        indexes.append(index)
    left, right = indexes
    result = []
    for identity in sorted(set(left) | set(right)):
        orders_here, paid_here = left.get(identity, []), right.get(identity, [])
        due, paid = sum(orders_here, Decimal(0)), sum(paid_here, Decimal(0))
        statuses = []
        if not paid_here:
            statuses.append('漏收款')
        if not orders_here:
            statuses.append('无源流水')
        if len(orders_here) > 1:
            statuses.append('重复订单待核实')
        if len(paid_here) > 1:
            statuses.append('多笔入账待核实')
        if orders_here and paid_here and due != paid:
            statuses.append('金额不一致')
        result.append({'订单号': identity, '状态': '；'.join(statuses) if statuses else '核对一致',
            '异常': '是' if statuses else '否', '应收': str(due.quantize(Decimal('.01'))),
            '实收': str(paid.quantize(Decimal('.01'))), '差额': str((paid-due).quantize(Decimal('.01'))),
            '订单笔数': len(orders_here), '流水笔数': len(paid_here), '说明': '多笔可能为拆单或退款，请结合业务核实' if len(paid_here)>1 else '',
            '行类型': '核对结果'})
    return sorted(invalid + result, key=lambda r: (r['异常'] != '是', r['订单号']))


def reconcile_files(orders, payments, mapping=None):
    return reconcile_rows(read_table(orders), read_table(payments), mapping)
