"""Readonly phone/status protection; user_message is editable per user confirmation."""
import json


def checks(before, after, accepted, changes):
    result = {'formal_unchanged':before['formal']==after['formal']}
    if accepted is False:
        result['rejected_without_effects'] = before == after
        return result
    result['valid_business_status'] = accepted is True
    result['one_pending'] = not before['pending'] and len(after['pending']) == 1
    result['processed_unchanged'] = before['processed'] == after['processed']
    result['audit_append'] = len(after['audit']) == len(before['audit'])+1 and all(x in after['audit'] for x in before['audit'])
    if not result['one_pending']:
        return result
    draft = after['pending'][0]['after_info']
    if isinstance(draft, str): draft = json.loads(draft)
    original = before['formal']['admin']
    result['phone_protected'] = 'phone' not in draft or str(draft['phone']) == str(original['phone'])
    result['kyc_status_protected'] = 'kyc_status' not in draft or draft['kyc_status'] == original['kyc_status']
    result['editable_fields_recorded'] = all(k in draft and draft[k] == value for k,value in changes.items())
    return result


def verify(adapter, step, case_id):
    p = step['params']
    values = checks(p['before'],p['after'],p['accepted'],p['changes'])
    return {'checks':{'protected_edit':all(values.values())},'summary':'检查手机号/状态保护及合法姓名、地址、留言变更；'+json.dumps(values,ensure_ascii=False)}
