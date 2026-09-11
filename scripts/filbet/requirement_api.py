"""Requirement-owned read API suites; strict assertions and response-free evidence."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit

from filbet import smoke
from qa_core.environment import load_environment
from qa_core.local_lock import local_run_lock
from qa_core.case_report import execution_status, write_views

ROOT = Path(__file__).resolve().parents[2]
# Query-only POSTs are intentionally explicit. Export and edit are not queries.
READ_ROUTES = {
    ('GET', '/admin/kyc/review/list'),
    ('GET', '/admin/kyc/ekyc/log'),
    ('POST', '/admin/kyc/list'),
    ('GET', '/admin/promo/betting/rebate/report'),
    ('POST', '/cmpl/record/game'),
    ('POST', '/admin/record/game'),
    ('POST', '/admin/record/bet'),
}
OPS = {'type', 'eq', 'rows_eq', 'rows_in', 'row_keys', 'row_decimal',
       'page_limit', 'count_rows', 'jp_multi', 'jp_visibility', 'rebate_details'}
TYPES = {'object': dict, 'array': list, 'integer': int, 'string': str, 'boolean': bool}


def load_suite(requirement):
    if not re.fullmatch(r'ISOP-\d+', requirement):
        raise ValueError('invalid requirement identifier')
    folder = ROOT / 'requirements' / requirement
    source = folder / 'plan.json'
    if source.is_file():
        from qa_core.execution_plan import legacy_query_suite
        raw = source.read_bytes()
        suite = legacy_query_suite(json.loads(raw))
    else:
        raw = (folder / 'api/cases.json').read_bytes()
        suite = json.loads(raw)
    if suite['requirement'] != requirement:
        raise ValueError('suite requirement mismatch')
    acceptance = set(re.findall(r'\| (ISOP-\d+-C\d+) \|', (folder / 'test-cases.md').read_text()))
    seen = set()
    for case in suite['cases']:
        if case['id'] in seen or not case['case_ids'] or not set(case['case_ids']) <= acceptance:
            raise ValueError('duplicate combination or missing acceptance case reference')
        seen.add(case['id'])
        if case.get('blocked'):
            continue
        req = case['request']
        if (req['method'], req['path']) not in READ_ROUTES:
            raise ValueError('route is not an approved query')
        if case.get('auth', 'valid') not in {'valid', 'missing', 'invalid'}:
            raise ValueError('unknown auth mode')
        if case['expect'] not in {'success', 'auth_rejected', 'validation_rejected'}:
            raise ValueError('unknown expectation')
        if case['expect'] == 'success' and not case.get('checks'):
            raise ValueError('positive case needs explicit checks')
        if case['expect'] == 'validation_rejected' and not case.get('error_pattern'):
            raise ValueError('negative case needs an error contract')
        for check in case.get('checks', []):
            if check['op'] not in OPS:
                raise ValueError('unknown assertion')
            if check['op'] == 'type' and check['value'] not in TYPES:
                raise ValueError('unknown assertion type')
    return suite, hashlib.sha256(raw).hexdigest()


def decimal(value):
    if isinstance(value, bool) or value is None:
        raise ValueError('not a finite amount')
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError('not a finite amount')
    return number


def evaluate(case, result):
    """No raw response values in diagnostics, including assertion failures."""
    body = result.get('decoded_body')
    http = result.get('status')
    if not isinstance(http, int) or http >= 500:
        return 'FAIL', ['transport/server failure']
    if case['expect'] != 'success':
        if not isinstance(body, dict) or body.get('status') is not False:
            return 'FAIL', ['expected decoded business rejection']
        # Returning a data object/list on an auth failure may leak records.
        if case['expect'] == 'auth_rejected':
            # FAT 2026-09-10 gateway contract: literal "token" is an error marker,
            # not a returned token. Do not accept arbitrary string data.
            if http == 200 and body.get('data') == 'token':
                return 'PASS', []
            message = ' '.join(str(body.get(k, '')) for k in ('message', 'msg', 'error'))
            denied = http in (401, 403) or (http == 200 and re.search(
                r'unauthori[sz]ed|unauthenticated|not logged|login.*(?:expired|required)|'
                r'(?:invalid|expired).*token|token.*(?:invalid|expired)|未登录|登录.*(?:失效|过期)',
                message, re.I))
            safe = body.get('data') in (None, '', False) or body.get('data') == {} or body.get('data') == []
            return ('PASS', []) if denied and safe else ('FAIL', ['auth rejection or no-data contract not satisfied'])
        message = ' '.join(str(body.get(k, '')) for k in ('message', 'msg', 'error'))
        valid = http in (200, 400, 422) and re.search(case['error_pattern'], message, re.I)
        return ('PASS', []) if valid else ('FAIL', ['validation error did not match expected parameter rejection'])
    if http != 200 or not isinstance(body, dict) or body.get('status') is not True:
        return 'FAIL', ['expected HTTP 200 and business status true']
    failures = []
    for check in case.get('checks', []):
        op, path = check['op'], check.get('path', 'data.d')
        value = smoke.get_nested(body, path)
        try:
            ok = True
            if op == 'type':
                ok = type(value) is TYPES[check['value']]
            elif op == 'eq':
                ok = type(value) is type(check['value']) and value == check['value']
            elif op == 'count_rows':
                ok = type(value) is int and value == len(smoke.get_nested(body, 'data.d'))
            elif op == 'page_limit':
                ok = isinstance(value, list) and len(value) <= check['value']
            else:
                if not isinstance(value, list):
                    raise ValueError('rows missing')
                for row in value:
                    if not isinstance(row, dict):
                        raise ValueError('row invalid')
                    if op == 'rows_eq':
                        ok &= type(row.get(check['field'])) is type(check['value']) and row.get(check['field']) == check['value']
                    elif op == 'rows_in':
                        ok &= row.get(check['field']) in check['value']
                    elif op == 'row_keys':
                        ok &= all(k in row for k in check['value'])
                    elif op == 'row_decimal':
                        for key in check['value']:
                            decimal(row[key])
                    elif op == 'jp_visibility':
                        expected = row['platform_name'] in ('mi', 'op') and decimal(row['jp_contribution'] or '0') != 0
                        ok &= type(row['show_jp_info']) is bool and row['show_jp_info'] == expected
                    elif op == 'jp_multi':
                        details = row['jackpot_details']
                        ok &= row['jp_type'] == 99 and isinstance(details, list) and len(details) > 1
                        if ok:
                            ok &= all(d['jp_type'] in (1, 2, 3, 4) for d in details)
                            ok &= sum((decimal(d['jp_winning']) for d in details), Decimal(0)) == decimal(row['jp_winning'])
                    elif op == 'rebate_details':
                        details = json.loads(row['conf'])
                        if not isinstance(details, list) or not details:
                            raise ValueError('rebate detail missing')
                        for field in ('bonus', 'multiple_amount'):
                            ok &= sum((decimal(d[field]) for d in details), Decimal(0)) == decimal(row[field])
            if not ok:
                failures.append(f'{op}:{path} mismatch')
        except (TypeError, KeyError, ValueError, InvalidOperation):
            failures.append(f'{op}:{path} missing/invalid data')
    if failures:
        return 'FAIL', failures
    if case.get('requires_rows') and not smoke.get_nested(body, 'data.d'):
        return 'BLOCKED', ['query succeeded but no matching business sample; row assertions not exercised']
    return 'PASS', []


def observation(result):
    body = result.get('decoded_body')
    rows = smoke.get_nested(body, 'data.d')
    # Deliberate allowlist: never persist raw body, request headers, IDs or error text.
    return {'http': result.get('status'), 'business_status': body.get('status') if isinstance(body, dict) and type(body.get('status')) is bool else None,
            'rows': len(rows) if isinstance(rows, list) else None, 'elapsed_ms': result.get('elapsed_ms'),
            'data_type': type(smoke.get_nested(body, 'data')).__name__, 'rows_type': type(rows).__name__,
            'auth_marker': 'token' if isinstance(body, dict) and body.get('status') is False and body.get('data') == 'token' else None}


def execute_case(case, args):
    req = case['request']
    path = req['path']
    if req.get('query'):
        path += '?' + urlencode(req['query'])
    row = {'method': req['method'], 'clean_url': '{{admin_url}}' + path,
           'suggested_base_var': '{{admin_url}}', 'priority': 'requirement', 'case_id': case['id']}
    previous = os.environ.get('ADMIN_TOKEN')
    try:
        if case.get('auth') == 'missing':
            os.environ.pop('ADMIN_TOKEN', None)
        elif case.get('auth') == 'invalid':
            os.environ['ADMIN_TOKEN'] = 'invalid-requirement-test-token'
        result = smoke.request_once(row, args.timeout, args.insecure, req.get('body'), args.body_format)
        status, details = evaluate(case, result)
        return status, details, observation(result)
    finally:
        if previous is None:
            os.environ.pop('ADMIN_TOKEN', None)
        else:
            os.environ['ADMIN_TOKEN'] = previous


def write_reports(folder, report, suite=None):
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    lines = [f"# {report['requirement']} API 执行结果", '',
             f"时间：{report['run_at']}；环境：{report['environment']}；部署版本：{report['deployment']}。", '',
             f"用例 SHA256：`{report['cases_sha256']}`。请求/响应原文不落盘。", '',
             '本报告仅验证列出的 API 组合，不自动将整条验收用例或 UI 标为 PASS。', '',
             '| 组合 ID | 验收 Case | 正反例 | 状态 | HTTP / 业务状态 / 行数 | 说明 |',
             '| --- | --- | --- | --- | --- | --- |']
    for item in report['results']:
        obs = item.get('observation', {})
        lines.append(f"| {item['id']} | {', '.join(item['case_ids'])} | {item['kind']} | {item['status']} | "
                     f"{obs.get('http', '—')} / {obs.get('business_status', '—')} / {obs.get('rows', '—')} | "
                     + '; '.join(item['details']).replace('|', '/') + ' |')
    (folder / 'report.md').write_text('\n'.join(lines) + '\n')
    if suite is not None:
        catalogue, outcomes = [], []
        for case, item in zip(suite['cases'], report['results']):
            req = case.get('request', {})
            catalogue.append({'用例编号': case['id'], '类型': 'API',
                '模块/接口': req.get('path', '业务前置'), '用例名称': case.get('title', case['id']),
                '前置条件': case.get('blocked') or '指定环境；有效管理员登录',
                '参数/步骤': (req.get('method', '') + ' ' + json.dumps(req.get('query', req.get('body', {})), ensure_ascii=False)).strip() or '待补执行资产',
                '预期结果': case.get('expect', '满足验收预期') + '; ' + '; '.join(
                    f"{c.get('path', 'data.d')} {c['op']} {c.get('value', '')}" for c in case.get('checks', [])),
                '级别': '验收', '验收点': ', '.join(case['case_ids'])})
            status = execution_status(item)
            obs = item.get('observation', {})
            outcomes.append({'id': case['id'], 'status': status,
                'actual': '; '.join(item['details']) or f"HTTP {obs.get('http')}；业务状态 {obs.get('business_status')}；断言通过",
                'category': '待分析' if status == 'FAIL' else '', 'evidence': str(folder / 'result.json')})
        write_views(folder / 'views', catalogue, {'run_id': folder.name, 'environment': report['environment'],
                    'source_time': report['run_at'], 'results': outcomes})


def run(args):
    suites = [(key, *load_suite(key)) for key in args.requirements]
    if args.only:
        available = {c['id'] for _, s, _ in suites for c in s['cases']}
        if not set(args.only) <= available:
            raise ValueError('unknown combination identifier')
        suites = [(key, {**s, 'cases': [c for c in s['cases'] if c['id'] in args.only]}, digest)
                  for key, s, digest in suites]
    if args.timeout <= 0 or args.timeout > 60:
        raise ValueError('timeout must be between 0 and 60 seconds')
    if not args.execute:
        for key, suite, _ in suites:
            print(key, dict(Counter('BLOCKED' if c.get('blocked') else c['kind'] for c in suite['cases'])))
        return 0
    if not args.env:
        raise ValueError('--env must explicitly select .env.fat or .env.uat')
    environment = Path(args.env).name
    hosts = {'.env.fat': 'admin-fat.filbet2025.com', '.env.uat': 'admin-uat.filbet2025.com'}
    if environment not in hosts:
        raise ValueError('only explicit FAT/UAT environment is supported')
    env = load_environment(args.env)
    url = urlsplit(env.get('ADMIN_URL', ''))
    if url.scheme != 'https' or url.netloc != hosts[environment]:
        raise ValueError('ADMIN_URL must match the selected FAT/UAT environment')
    os.environ.update(env)
    os.environ.pop('ADMIN_TOKEN', None)
    run_at = datetime.now(timezone.utc)
    run_id = run_at.strftime('%Y%m%dT%H%M%S%fZ')
    overall = Counter()
    with local_run_lock():
        login_ok = False
        try:
            auth, token = smoke.admin_login(args)
            login_ok = bool(token) and all(r.get('status') == 200 and smoke.get_nested(r.get('decoded_body'), 'status') is True for r in auth)
        except (Exception, SystemExit):
            login_ok = False
        for key, suite, digest in suites:
            report = {'requirement': key, 'run_at': run_at.isoformat(), 'environment': environment,
                      'deployment': '未提供', 'cases_sha256': digest,
                      'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'source_commit': suite['source_commit'], 'selection': args.only or 'all',
                      'login': 'PASS' if login_ok else 'FAIL', 'results': []}
            for case in suite['cases']:
                item = {k: case[k] for k in ('id', 'case_ids', 'kind')}
                if case.get('blocked'):
                    status, details, obs = 'BLOCKED', [case['blocked']], {}
                elif not login_ok:
                    status, details, obs = 'BLOCKED', ['fresh admin login failed; no business request sent'], {}
                else:
                    try:
                        status, details, obs = execute_case(case, args)
                    except Exception:
                        status, details, obs = 'FAIL', ['request/evaluation exception; raw details suppressed'], {}
                item.update(status=status, details=details, observation=obs)
                report['results'].append(item)
                overall[status] += 1
                print(key, case['id'], status, flush=True)
            folder = ROOT / 'requirements' / key / 'api/results' / run_id
            write_reports(folder, report, suite)
            print('Report:', folder / 'views/results.html', flush=True)
    os.environ.pop('ADMIN_TOKEN', None)
    print('Summary:', dict(overall))
    return 1 if overall['FAIL'] else 2 if overall['BLOCKED'] else 0
