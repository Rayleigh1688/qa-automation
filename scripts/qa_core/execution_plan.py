"""Versioned, offline execution contract. JSON owns review rows and executable steps."""
import copy
import hashlib
import json
import re
from pathlib import Path
from qa_core.case_report import FIELDS, csv_text, validate_cases

REF = re.compile(r'\$\{([A-Za-z][A-Za-z0-9_.]*)\}')
OPS = {'eq', 'type', 'exists', 'count', 'set', 'contains', 'nonempty', 'rows_eq', 'append_only', 'pluck_set', 'max_count', 'rows_have_keys'}
TYPES = {'object': dict, 'array': list, 'integer': int, 'string': str, 'boolean': bool, 'null': type(None)}
MISSING = object()


def at(value, path):
    for part in path.split('.') if path else []:
        if isinstance(value, dict):
            value = value.get(part, MISSING)
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return MISSING
    return value


def references(value):
    if isinstance(value, str):
        return set(REF.findall(value))
    if isinstance(value, dict):
        return set().union(*(references(v) for v in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(references(v) for v in value)) if value else set()
    return set()


def resolve(value, variables):
    if isinstance(value, str):
        match = REF.fullmatch(value)
        def get(key):
            result = at(variables, key)
            if result is MISSING:
                raise ValueError('missing variable: ' + key)
            return copy.deepcopy(result)
        if match:
            return get(match[1])
        return REF.sub(lambda m: str(get(m[1])), value)
    if isinstance(value, dict):
        return {k: resolve(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, variables) for v in value]
    return value


def expand(plan):
    result = []
    for case in plan['cases']:
        datasets = case.get('datasets', [None])
        for name in datasets:
            item = copy.deepcopy(case)
            item['variables'] = {**plan.get('variables', {}), **case.get('variables', {})}
            if name is not None:
                if name not in plan.get('datasets', {}):
                    raise ValueError('unknown dataset: ' + name)
                item['id'] += ':' + name
                item['review']['用例编号'] = item['id']
                item['variables']['data'] = plan['datasets'][name]
            if item.get('steps'):
                descriptions, expectations = [], []
                for step in item['steps']:
                    route = plan['contracts'].get(step.get('contract'), {})
                    target = route.get('method','') + ' ' + route.get('path',step.get('method',step.get('page','')+'/'+step.get('op','')))
                    params = {k:step[k] for k in ['body','query','params','upload','auth','element','value','property','response'] if k in step}
                    descriptions.append(step['id']+' ['+step['actor']+'] '+target.strip()+' '+json.dumps(params,ensure_ascii=False,separators=(',',':')))
                    for check in step.get('expect',[]):
                        expectations.append(step['id']+': '+check['path']+' '+check['op']+' '+json.dumps(check.get('value','非空'),ensure_ascii=False))
                if name is not None:
                    descriptions.append('数据集 '+name+': '+json.dumps(plan['datasets'][name],ensure_ascii=False))
                item['review']['参数/步骤'] = '\n'.join(descriptions)
                item['review']['预期结果'] += '\n'+'\n'.join(expectations)
            result.append(item)
    return result


def validate(plan, methods=None):
    methods = methods or {}
    if plan.get('execution_policy') not in {None,'api-first'}:
        raise ValueError('unknown execution policy')
    if plan.get('schema_version') != 2 or not re.fullmatch(r'ISOP-\d+', plan.get('requirement', '')):
        raise ValueError('invalid execution plan version/story')
    for alias, service in plan['services'].items():
        if not re.fullmatch(r'[A-Z_]+', service['env']):
            raise ValueError('service must reference an environment key')
    for route in plan['contracts'].values():
        if route['service'] not in plan['services'] or route['method'] not in {'GET', 'POST', 'PUT', 'DELETE'}:
            raise ValueError('invalid route reference')
        if not re.fullmatch(r'/[A-Za-z0-9_/-]+', route['path']) or route.get('encoding') not in {'json', 'cbor', 'multipart'}:
            raise ValueError('invalid route path/encoding')
        if type(route.get('write')) is not bool or (route['write'] and not route.get('scope')):
            raise ValueError('route needs write classification/scope')
    cases = expand(plan)
    validate_cases([c['review'] for c in cases])
    seen = set()
    for case in cases:
        from qa_core.team_delivery import validate_delivery
        validate_delivery(case)
        if plan.get('execution_policy')=='api-first' and not case.get('delivery'):
            raise ValueError('api-first case needs explicit execution assignment')
        if case['id'] in seen or case['review']['用例编号'] != case['id']:
            raise ValueError('duplicate/mismatched case ID')
        seen.add(case['id'])
        acceptance = {ref.strip().removeprefix(plan['requirement']+'-') for ref in case['review']['验收点'].split(',')}
        if not acceptance <= set(plan.get('acceptance_ids', [])):
            raise ValueError('unknown acceptance reference')
        if case.get('blocked'):
            if case.get('steps'):
                raise ValueError('blocked case cannot contain executable steps')
            continue
        known = set(case['variables']) | {'run'}
        steps = case.get('steps', [])
        if not steps:
            if case.get('delivery',{}).get('mode')=='manual': continue
            raise ValueError('case needs steps or explicit non-execution reason')
        if not any(s.get('action') in {'api','ui'} or methods.get(s.get('method'), {}).get('business') for s in steps):
            raise ValueError('preparation alone cannot be a business case')
        ids = set()
        for step in steps:
            if step['id'] in ids:
                raise ValueError('duplicate step ID')
            ids.add(step['id'])
            if step.get('actor') not in plan['actors']:
                raise ValueError('unknown actor')
            if step.get('diagnostic') and (step['action'] != 'method' or not methods.get(step.get('method'), {}).get('read_only')):
                raise ValueError('only declared read-only methods may continue after failure')
            if step['action'] == 'api':
                if step.get('contract') not in plan['contracts']:
                    raise ValueError('unknown contract')
                route = plan['contracts'][step['contract']]
                if route['service'] not in plan['actors'][step['actor']]['services']:
                    raise ValueError('actor/service mismatch')
                if step.get('auth', 'valid') not in {'valid', 'missing', 'invalid'}:
                    raise ValueError('unknown auth mode')
                checks = step.get('expect', [])
                if not checks:
                    raise ValueError('API step needs assertions')
                for check in checks:
                    if check['op'] not in OPS or not isinstance(check.get('path'), str):
                        raise ValueError('unknown assertion')
                    if check['op'] == 'type' and check.get('value') not in TYPES:
                        raise ValueError('unknown assertion type')
                    if check['op'] != 'nonempty' and 'value' not in check:
                        raise ValueError('assertion needs expected value')
                if not case.get('observational') and not any(c['path'] == 'body.status' and c['op'] == 'eq' and type(c.get('value')) is bool for c in checks):
                    raise ValueError('business result must have a fixed expectation')
                if not any(c['path'] == 'http' for c in checks) or not any(c['path'] == 'body.status' for c in checks):
                    raise ValueError('HTTP and business assertion required')
            elif step['action'] == 'ui':
                from qa_core.ui_contract import validate_ui
                validate_ui(plan,step)
                for check in step.get('expect',[]):
                    if check.get('op') not in OPS or not isinstance(check.get('path'),str):
                        raise ValueError('unknown UI assertion')
                    if check['op']=='type' and check.get('value') not in TYPES:
                        raise ValueError('unknown UI assertion type')
                    if check['op']!='nonempty' and 'value' not in check:
                        raise ValueError('UI assertion needs expected value')
            elif step['action'] == 'method':
                if step.get('method') not in methods:
                    raise ValueError('unknown business method')
                validator = methods[step['method']].get('validate')
                if validator:
                    def known_inputs(value):
                        if isinstance(value,dict): return {k:known_inputs(v) for k,v in value.items()}
                        if isinstance(value,list): return [known_inputs(v) for v in value]
                        refs = references(value)
                        return resolve(value,case['variables']) if refs and all(r.split('.')[0] in case['variables'] for r in refs) else value
                    validator(plan,known_inputs(step))
                for check in step.get('expect', []):
                    if check.get('op') not in OPS or not isinstance(check.get('path'), str):
                        raise ValueError('unknown method assertion')
                    if check['op'] == 'type' and check.get('value') not in TYPES:
                        raise ValueError('unknown assertion type')
            else:
                raise ValueError('unknown action')
            for ref in references(step):
                if ref.split('.')[0] not in known:
                    raise ValueError('undefined variable: ' + ref)
                if ref.split('.')[0] in case['variables'] and at(case['variables'], ref) is MISSING:
                    raise ValueError('undefined input path: ' + ref)
            for name, path in step.get('extract', {}).items():
                if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name) or name in known or not isinstance(path, str):
                    raise ValueError('invalid/duplicate extraction')
                known.add(name)
    return cases


def load(path, methods=None):
    raw = Path(path).read_bytes()
    plan = json.loads(raw)
    return plan, validate(plan, methods), hashlib.sha256(raw).hexdigest()


def export_cases(path, cases):
    Path(path).write_text(csv_text([c['review'] for c in cases], FIELDS), encoding='utf-8')


def assertions(checks, response):
    results = []
    for check in checks:
        value = at(response, check['path'])
        expected = check.get('value')
        op = check['op']
        ok = False
        if op == 'exists':
            ok = (value is not MISSING) is expected
        elif value is not MISSING:
            if op == 'eq':
                ok = type(value) is type(expected) and value == expected
            elif op == 'type':
                ok = type(value) is TYPES[expected]
            elif op == 'count':
                ok = isinstance(value, (dict, list, str)) and len(value) == expected
            elif op == 'set':
                ok = isinstance(value, list) and sorted(map(lambda v: json.dumps(v, sort_keys=True), value)) == sorted(map(lambda v: json.dumps(v, sort_keys=True), expected))
            elif op == 'contains':
                ok = isinstance(value, (list, str, dict)) and expected in value
            elif op == 'max_count':
                ok = isinstance(value, list) and len(value) <= expected
            elif op == 'rows_have_keys':
                ok = isinstance(value, list) and bool(value) and all(isinstance(row,dict) and all(k in row for k in expected) for row in value)
            elif op == 'pluck_set':
                ok = isinstance(value, list) and isinstance(expected, list) and all(at(row, check['field']) is not MISSING for row in value) and sorted(json.dumps(at(row, check['field']),sort_keys=True) for row in value) == sorted(json.dumps(v,sort_keys=True) for v in expected)
            elif op == 'rows_eq':
                ok = isinstance(value, list) and bool(value) and all(type(at(row, check['field'])) is type(expected) and at(row, check['field']) == expected for row in value)
            elif op == 'append_only':
                ok = isinstance(value, list) and isinstance(expected, list) and len(value) == len(expected) + 1 and all(row in value for row in expected)
            elif op == 'nonempty':
                ok = isinstance(value, (list, str, dict)) and bool(value)
        # Only scalar protocol fields are public; private business values stay in memory.
        safe = check['path'] in {'http', 'body.status'} or op in {'type', 'count', 'exists'} or (check['path'].startswith('checks.') and type(value) is bool) or (check['path']=='value' and type(value) is bool) or check['path']=='request_count'
        actual = '<missing>' if value is MISSING else (type(value).__name__ if op == 'type' else len(value) if op == 'count' and isinstance(value, (dict, list, str)) else value is not MISSING if op == 'exists' else value if safe else '<redacted>')
        results.append({'path': check['path'], 'op': op, 'expected': expected if safe else '<redacted>', 'actual': actual, 'status': 'PASS' if ok else 'FAIL'})
        if not safe and value is not MISSING:
            results[-1]['actual_type'] = type(value).__name__
            if isinstance(value,(dict,list,str)): results[-1]['actual_length'] = len(value)
    return results


def legacy_query_suite(plan):
    """Generate the v1 read-CLI view from the same reviewed v2 query steps."""
    suite = {'schema_version':1,'requirement':plan['requirement'],**plan.get('legacy_metadata',{}),'cases':[]}
    for case in plan['cases']:
        if not case.get('legacy_ids'):
            continue
        step = case['steps'][0]
        route = plan['contracts'][step['contract']]
        if route['write']: raise ValueError('legacy CLI cannot receive a write contract')
        auth = step.get('auth','valid')
        checks = []
        for check in step['expect']:
            if check['path'] in {'http','body.status'} or auth!='valid' or check['op']=='nonempty': continue
            op = {'max_count':'page_limit','rows_have_keys':'row_keys'}.get(check['op'],check['op'])
            checks.append({**check,'op':op,'path':check['path'].removeprefix('body.')})
        suite['cases'].append({'id':case['id'],'case_ids':re.findall(r'ISOP-\d+-C\d+',case['review']['验收点']),
            'title':case['review']['用例名称'],'kind':'positive' if auth=='valid' else 'negative',
            'request':{'method':route['method'],'path':route['path'],**{k:step[k] for k in ['query','body'] if k in step}},
            'auth':auth,'expect':'success' if auth=='valid' else 'auth_rejected',
            'requires_rows':any(c['op']=='nonempty' for c in step['expect']), 'checks':checks})
    suite['cases'].extend(plan.get('legacy_acceptance',[]))
    return suite
