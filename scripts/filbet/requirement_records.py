"""Read-only assertions for ISOP-2022 record queries; no response identities persisted."""
from decimal import Decimal, InvalidOperation


def amount(value):
    if value is None or isinstance(value, bool):
        raise ValueError('invalid amount')
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('invalid amount')
    return result


def inspect_record_response(data, request):
    rows = data['d']
    checks = {'page_count': type(data['s']) is int and data['s'] == len(rows),
              'page_limit': len(rows) <= request['page_size'],
              'total_count': type(data['t']) is int and data['t'] >= len(rows)}
    if not rows:
        return checks
    for start, end, field in [('start_time','end_time','bet_time'),('settle_start_time','settle_end_time','settle_time')]:
        if start in request and end in request:
            checks[field+'_range'] = all(type(r.get(field)) is int and request[start] <= r[field] <= request[end] for r in rows)
    if request.get('node') in (1,2):
        allowed = (1,) if request['node']==1 else (0,2)
        checks['node_filter'] = all(r.get('node') in allowed for r in rows)
    sport = request.get('game_type')==4 or request.get('pagcor_game_type')=='sports_betting'
    if sport:
        checks['sports_only'] = all(str(r.get('game_class'))=='4' for r in rows)
    elif 'settle_start_time' in request:
        checks['exclude_sports'] = all(str(r.get('game_class'))!='4' for r in rows)
    if 'state' in request:
        checks['state_filter'] = all(str(r.get('state'))==request['state'] for r in rows)
    if 'order_type' in request:
        checks['order_type_filter'] = all(r.get('bet_type')==request['order_type'] for r in rows)
    try:
        checks['payout_sign'] = all(amount(r['payout_amount']) == amount(r['bet_amount'])-amount(r['net_amount']) for r in rows)
        subtotal = data['a']['subtotal']
        for summary, field in [('bet_amount','bet_amount'),('valid_bet_amount','valid_bet_amount'),('grand_inc','payout_amount'),('ggr','net_amount')]:
            checks['subtotal_'+summary] = amount(subtotal[summary]) == sum((amount(r[field]) for r in rows),Decimal(0))
        checks['subtotal_order_count'] = amount(subtotal['order_count']) == len(rows)
    except (KeyError,TypeError,ValueError,InvalidOperation):
        checks['amount_fields_valid'] = False
    return checks


def record_check(adapter, step, case_id):
    params = step['params']
    checks = inspect_record_response(params['data'],params['request'])
    # Only protocol counts and named assertion outcomes enter public evidence.
    return {'checks':checks,'value':all(checks.values()),
            'summary':'行数='+str(len(params['data']['d']))+'；'+', '.join(k+'='+str(v) for k,v in checks.items())}
