"""Versioned, offline execution contract. JSON owns review rows and executable steps."""
import copy
import hashlib
import json
import re
from collections import Counter
from fractions import Fraction
from pathlib import Path
from qa_core.api_response_evidence import SAFE_KEY, observed_kind, public_allowed_value
from qa_core.case_report import FIELDS, csv_text, validate_cases

REF = re.compile(r'\$\{([A-Za-z][A-Za-z0-9_.]*)\}')
OPS = {'eq', 'type', 'exists', 'count', 'set', 'contains', 'nonempty', 'rows_eq', 'append_only', 'pluck_set', 'max_count', 'rows_have_keys', 'empty_or_null'}
OPS.update({'any_row_matches', 'fields_absent_or', 'decimal_delta'})
TYPES = {'object': dict, 'array': list, 'integer': int, 'string': str, 'boolean': bool, 'null': type(None)}
CLIENT_SESSIONS = {'anonymous', 'client_password'}
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
                        expectations.append(step['id']+': '+check['path']+' '+check['op']+' '+json.dumps(check.get('value','null或[]' if check['op']=='empty_or_null' else '非空'),ensure_ascii=False))
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
    for name, actor in plan['actors'].items():
        if 'session' in actor and (
            actor['session'] not in CLIENT_SESSIONS or actor['services'] != ['client']
            or name in {'A', 'B', 'client'}
        ):
            raise ValueError('client session mode requires a separate client actor')
        if 'credentials' in actor and (
            actor.get('session') != 'client_password' or actor['credentials'] != 'withdraw_client'
        ):
            raise ValueError('unsupported client actor credentials')
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
            session_mode = plan['actors'][step['actor']].get('session')
            if session_mode and step['action'] != 'api':
                raise ValueError('client session actors require API steps')
            if step.get('diagnostic') and (step['action'] != 'method' or not methods.get(step.get('method'), {}).get('read_only')):
                raise ValueError('only declared read-only methods may continue after failure')
            if step['action'] == 'api':
                if step.get('contract') not in plan['contracts']:
                    raise ValueError('unknown contract')
                route = plan['contracts'][step['contract']]
                if route['service'] not in plan['actors'][step['actor']]['services']:
                    raise ValueError('actor/service mismatch')
                auth = step.get('auth', 'missing' if session_mode == 'anonymous' else 'valid')
                if auth not in {'valid', 'missing', 'invalid'}:
                    raise ValueError('unknown auth mode')
                if session_mode and (route['write'] or (auth == 'valid') != (session_mode == 'client_password')):
                    raise ValueError('client session actors require matching auth and a read-only contract')
                checks = step.get('expect', [])
                if not checks:
                    raise ValueError('API step needs assertions')
                for check in checks:
                    if check['op'] not in OPS or not isinstance(check.get('path'), str):
                        raise ValueError('unknown assertion')
                    if check['op'] == 'type' and check.get('value') not in TYPES:
                        raise ValueError('unknown assertion type')
                    if check['op'] not in {'nonempty','empty_or_null'} and 'value' not in check:
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
                    if check['op'] not in {'nonempty','empty_or_null'} and 'value' not in check:
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
            for check in step.get('expect', []):
                if check['op'] == 'fields_absent_or':
                    field_choices(resolve(check.get('value'), case['variables']))
                if check['op'] == 'any_row_matches' and (
                    not isinstance(check.get('value'), dict) or not check['value']
                    or any(not key for key in check['value'])
                ):
                    raise ValueError('any_row_matches requires fields and expected values')
                if check['op'] == 'decimal_delta' and (
                    not isinstance(check.get('value'), dict) or check['value'].keys() != {'before', 'change'}
                ):
                    raise ValueError('decimal_delta requires before and change')
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


def _optional_plan_source(plan_path, plan, field, inline_fields, suffixes):
    if not isinstance(plan, dict):
        raise ValueError('execution plan must be an object')
    if field not in plan:
        return None
    if any(key in plan for key in inline_fields):
        raise ValueError(f'{field} and inline {"/".join(inline_fields)} are mutually exclusive')
    name = plan[field]
    invalid_path = f'{field} must be a relative {" or ".join(suffixes)} path'
    if not isinstance(name, str) or any(mark in name for mark in ('\\', ':', '\x00')):
        raise ValueError(invalid_path)
    relative = Path(name)
    if relative.suffix not in suffixes or relative.is_absolute() or '..' in relative.parts:
        raise ValueError(invalid_path)
    directory = Path(plan_path).parent.resolve()
    source = directory / relative
    if not source.resolve().is_relative_to(directory):
        raise ValueError(f'{field} must stay within the requirement directory')
    return source


def datasets_path(plan_path, plan):
    """Resolve the optional YAML source within the requirement directory."""
    return _optional_plan_source(plan_path, plan, 'datasets_file', ('datasets',), ('.yaml', '.yml'))


def plan_sources(plan_path, plan):
    """Resolve the files whose contents form part of a plan."""
    sources = {
        'datasets_file': datasets_path(plan_path, plan),
        'cases_file': _optional_plan_source(plan_path, plan, 'cases_file', ('contracts', 'cases'), ('.json',)),
    }
    return {key: source for key, source in sources.items() if source is not None}


def _load_yaml_datasets(raw):
    try:
        import yaml
    except ImportError:
        raise ValueError('YAML datasets require PyYAML (install config/requirements-yaml.txt)') from None

    class DatasetLoader(yaml.SafeLoader):
        def compose_node(self, parent, index):
            # Datasets expand into JSON review rows. An alias could produce a
            # cyclic or disproportionately large expansion.
            if self.check_event(yaml.AliasEvent):
                raise ValueError('YAML dataset aliases are not supported')
            return super().compose_node(parent, index)

        def construct_mapping(self, node, deep=False):
            if not isinstance(node, yaml.MappingNode):
                raise ValueError('invalid YAML dataset mapping')
            mapping = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                if not isinstance(key, str):
                    raise ValueError('YAML dataset mapping keys must be strings')
                if key in mapping:
                    raise ValueError('duplicate YAML dataset mapping key')
                mapping[key] = self.construct_object(value_node, deep=deep)
            return mapping

    def json_value(value):
        if isinstance(value, dict):
            return all(json_value(item) for item in value.values())
        if isinstance(value, list):
            return all(json_value(item) for item in value)
        if type(value) is float:
            return -float('inf') < value < float('inf')
        return value is None or type(value) in {str, bool, int}

    try:
        data = yaml.load(raw.decode('utf-8-sig'), Loader=DatasetLoader)
    except (yaml.YAMLError, UnicodeDecodeError, RecursionError):
        raise ValueError('invalid YAML datasets syntax or tag') from None
    if not isinstance(data, dict) or not all(isinstance(item, dict) for item in data.values()):
        raise ValueError('YAML datasets must map dataset names to objects')
    if not json_value(data):
        raise ValueError('YAML datasets require JSON-compatible values')
    return data


def _load_cases(raw):
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate JSON key in cases_file')
            value[key] = item
        return value

    data = json.loads(raw, object_pairs_hook=unique_object)
    if (not isinstance(data, dict) or data.keys() != {'contracts', 'cases'}
            or not isinstance(data['contracts'], dict) or not isinstance(data['cases'], list)):
        raise ValueError('cases_file must contain exactly a contracts object and a cases array')
    return data


def load(path, methods=None):
    raw = Path(path).read_bytes()
    plan = json.loads(raw)
    digest = hashlib.sha256(raw)
    sources = plan_sources(path, plan)
    if source := sources.get('datasets_file'):
        datasets_raw = source.read_bytes()
        plan['datasets'] = _load_yaml_datasets(datasets_raw)
        del plan['datasets_file']
        digest.update(b'\0datasets-v1\0' + hashlib.sha256(datasets_raw).digest())
    if source := sources.get('cases_file'):
        cases_raw = source.read_bytes()
        plan.update(_load_cases(cases_raw))
        del plan['cases_file']
        digest.update(b'\0cases-v1\0' + hashlib.sha256(cases_raw).digest())
    return plan, validate(plan, methods), digest.hexdigest()


def export_cases(path, cases):
    Path(path).write_text(csv_text([c['review'] for c in cases], FIELDS), encoding='utf-8')


def field_choices(value):
    if not isinstance(value, dict) or not value or any(
        not isinstance(key, str) or not key or not isinstance(choices, list)
        for key, choices in value.items()
    ):
        raise ValueError('fields_absent_or requires field names mapped to lists of allowed values')
    if any(isinstance(choice, (dict, list)) and choice for choices in value.values() for choice in choices):
        raise ValueError('fields_absent_or compares scalar values and empty containers')
    return value


def typed_equal(actual, expected):
    return type(actual) is type(expected) and actual == expected


def matching_fields(node, fields):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in fields:
                yield key, value
            yield from matching_fields(value, fields)
    elif isinstance(node, list):
        for value in node:
            yield from matching_fields(value, fields)


def decimal_amount(value):
    if type(value) is int or (type(value) is str and re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)', value)):
        return Fraction(value)
    return None


def visible_assertion_scalar(path, value):
    if path == 'http':
        return type(value) is int and 100 <= value <= 599
    if path in {'request_count', 'body.data.s', 'body.data.t'}:
        return type(value) is int and 0 <= value <= 100000000
    return type(value) is bool and (
        path in {'value', 'body.status', 'body.data.has_wallet_password'} or path.startswith('checks.')
    )


def assertion_display(path, op, expected, value, definition):
    if value is MISSING:
        actual = '<missing>'
    elif op == 'type':
        actual = type(value).__name__
    elif op in {'count', 'max_count'}:
        actual = len(value) if isinstance(value, (dict, list, str)) else None
    elif op == 'exists':
        actual = True
    elif visible_assertion_scalar(path, value):
        actual = value
    else:
        actual = public_allowed_value(value)
    if op == 'type' and isinstance(expected, str) and expected in TYPES:
        display_expected = expected
    elif op in {'count', 'max_count'} and type(expected) is int and 0 <= expected <= 100000000:
        display_expected = expected
    elif op == 'exists' and type(expected) is bool:
        display_expected = expected
        if value is MISSING:
            actual = False
    elif op == 'rows_have_keys' and isinstance(definition, list) and all(
        isinstance(key, str) and SAFE_KEY.fullmatch(key) for key in definition
    ):
        display_expected = definition
    elif op == 'nonempty':
        display_expected = '非空'
    elif op == 'empty_or_null':
        display_expected = [None, []]
    elif op == 'eq' and visible_assertion_scalar(path, expected):
        display_expected = expected
    else:
        display_expected = public_allowed_value(expected)
    return display_expected, actual


def assertions(checks, response, *, source_checks=None):
    results = []
    for index, check in enumerate(checks):
        value = at(response, check['path'])
        expected = check.get('value')
        op = check['op']
        source = source_checks[index] if source_checks is not None else check
        path = source['path']
        ok = False
        unexpected = None
        observations = None
        if op == 'exists':
            ok = (value is not MISSING) is expected
        elif value is not MISSING:
            if op == 'eq':
                ok = typed_equal(value, expected)
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
            elif op == 'empty_or_null':
                ok = value is None or (isinstance(value, list) and not value)
            elif op == 'pluck_set':
                ok = isinstance(value, list) and isinstance(expected, list) and all(at(row, check['field']) is not MISSING for row in value) and sorted(json.dumps(at(row, check['field']),sort_keys=True) for row in value) == sorted(json.dumps(v,sort_keys=True) for v in expected)
            elif op == 'rows_eq':
                ok = isinstance(value, list) and bool(value) and all(typed_equal(at(row, check['field']), expected) for row in value)
            elif op == 'any_row_matches':
                ok = isinstance(value, list) and bool(expected) and any(
                    isinstance(row, dict) and all(typed_equal(at(row, field), target) for field, target in expected.items())
                    for row in value
                )
            elif op == 'append_only':
                ok = isinstance(value, list) and isinstance(expected, list) and len(value) == len(expected) + 1 and all(row in value for row in expected)
            elif op == 'nonempty':
                ok = isinstance(value, (list, str, dict)) and bool(value)
            elif op == 'fields_absent_or' and isinstance(value, (dict, list)):
                allowed = field_choices(expected)
                failed_fields = set()
                observations = {key: Counter() for key in allowed}
                for key, item in matching_fields(value, allowed):
                    observations[key][observed_kind(item)] += 1
                    if not any(typed_equal(item, choice) for choice in allowed[key]):
                        failed_fields.add(key)
                unexpected = sorted(failed_fields)
                ok = not unexpected
            elif op == 'decimal_delta':
                actual_amount = decimal_amount(value)
                before = decimal_amount(expected['before'])
                change = decimal_amount(expected['change'])
                ok = None not in (actual_amount, before, change) and actual_amount - before == change
        # Compare resolved values in memory and report the original path template.
        expected_value, actual = assertion_display(path, op, expected, value, source.get('value'))
        item = {'path': path, 'op': op, 'expected': expected_value, 'actual': actual,
                'status': 'PASS' if ok else 'FAIL'}
        if op == 'fields_absent_or' and isinstance(expected, dict):
            labels = {key: key if isinstance(key, str) and SAFE_KEY.fullmatch(key) else f'<hidden key {index}>'
                      for index, key in enumerate(expected, 1)}
            item['expected'] = {labels[key]: [public_allowed_value(choice) for choice in choices]
                                for key, choices in expected.items()}
            if observations is not None:
                item['field_observations'] = {labels[key]: dict(counts) for key, counts in observations.items()}
                item['unexpected_fields'] = [labels[key] for key in unexpected]
        if value is not MISSING:
            item['actual_type'] = type(value).__name__
            if isinstance(value, (dict, list, str)):
                item['actual_length'] = len(value)
        results.append(item)
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
