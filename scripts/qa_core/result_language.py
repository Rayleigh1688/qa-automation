"""Chinese presentation of recorded assertions; never changes execution status."""
import json

STATUS_LABELS = {'PASS':'通过','FAIL':'失败','NOT_RUN':'未执行','ERROR':'执行出错'}
FIELDS = {'http':'HTTP状态','body.status':'业务处理状态','body.data':'返回数据',
          'body.data.d':'记录列表','body.data.t':'总记录数','body.data.s':'本页记录数',
          'body.data.a.total':'全部记录合计','body.data.a.subtotal':'本页小计',
          'checks.page_limit':'每页条数限制','checks.page_count':'本页记录数',
          'checks.bet_time_range':'投注时间筛选','checks.settle_time_range':'结算时间筛选',
          'checks.node_filter':'线路筛选','checks.exclude_sports':'排除体育记录',
          'checks.sports_only':'体育类型筛选','checks.payout_sign':'派彩金额计算'}
TYPES = {'array':'列表','list':'列表','object':'对象','dict':'对象','NoneType':'空值（null）',
         'integer':'整数','int':'整数','boolean':'是/否','bool':'是/否','string':'文本','str':'文本'}


def friendly_row(row):
    result = dict(row)
    raw = row['实际结果/失败点']
    try:
        checks = json.loads(raw)
    except (TypeError, ValueError):
        return result
    if not isinstance(checks,list) or not checks or not all(isinstance(c,dict) and 'path' in c and 'op' in c for c in checks):
        return result
    phrases = []
    for c in checks:
        path, op = c['path'],c['op']
        field = FIELDS.get(path,'该项检查')
        actual, expected = c.get('actual'),c.get('expected')
        if path=='body.data.d' and (actual=='NoneType' or c.get('actual_type')=='NoneType' or (op=='count' and actual is None)):
            phrase='预期返回记录列表；实际返回空值（null），没有可读取的列表。'
        elif op=='type':
            phrase=f'预期{field}为{TYPES.get(expected,"约定类型")}；实际为{TYPES.get(actual,"其他类型")}。'
        elif path=='body.data.t' and op=='eq':
            phrase='总记录数与预期不一致；分页场景中应保持与上一页相同。'
        elif path=='body.data.a.total' and op=='eq':
            phrase='预期翻页后全部记录合计不变；实际合计不一致。'
        elif path=='checks.page_limit':
            phrase='预期返回条数不超过设置的每页条数；实际超出限制。'
        elif op=='nonempty':
            phrase=f'预期{field}有内容；实际未满足。'
        else:
            phrase=f'{field}未达到预期，展开查看技术断言。'
        if phrase not in phrases: phrases.append(phrase)
    if any('空值（null）' in phrase for phrase in phrases):
        phrases.append('是否漏查记录需结合样本核对；空值本身不能证明记录丢失。')
    result['实际结果/失败点'] = ' '.join(phrases)
    result['技术断言'] = raw
    return result
