"""Bounded public report evidence. Raw credentials and response values stay in memory."""
from itertools import islice
import re


REDACTED = '<redacted>'
OMITTED = '<omitted>'
MAX_DEPTH = 8
MAX_ITEMS = 12
MAX_NODES = 160
ENVELOPE_FIELDS = frozenset({'status', 'code', 'message', 'msg', 'error', 'data'})
COMMON_FIELDS = frozenset({'d', 's', 't', 'rows', 'list', 'has_wallet_password'})
PAGINATION_KEYS = frozenset({'d', 's', 't'})
REQUEST_NUMBERS = frozenset({'page', 'page_size', 'time_flag', 'mode', 'sort'})
REVIEWED_MESSAGES = frozenset({
    'ok', 'success', 'successful', 'operation successful', 'request successful',
    'unauthorized', 'access denied', 'permission denied', 'invalid token', 'token expired',
    'bad request', 'invalid request', 'invalid parameter', 'invalid parameters',
    'not found', 'internal server error', 'service unavailable', 'system busy',
    'service is busy, please try again later！', 'service is busy, please try again later!',
    'no available transfer interface',
    '成功', '操作成功', '请求成功', '請求成功', '权限不足', '權限不足', '系统繁忙', '系統繁忙',
})
MESSAGE_FIELDS = frozenset({'message', 'msg', 'error'})
SAFE_KEY = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,63}\Z')
PRIVATE_CONTAINER = re.compile(r'token|secret|password|cookie|authorization|session|credential', re.I)


def observed_kind(value):
    """Classify a tested field without copying its identifier or text."""
    if value is None:
        return 'null'
    if type(value) is int:
        return 'integer_zero' if value == 0 else 'integer_nonzero'
    if type(value) is str:
        return 'empty_string' if value == '' else 'nonempty_string'
    if type(value) is bool:
        return 'boolean'
    if isinstance(value, (dict, list)):
        return ('nonempty_' if value else 'empty_') + type(value).__name__
    return type(value).__name__


def public_allowed_value(value):
    """Display the empty sentinels as exact values, without exposing custom data."""
    kind = observed_kind(value)
    if kind in {'null', 'integer_zero', 'empty_string', 'empty_dict', 'empty_list'}:
        return value
    return REDACTED


def reviewed_keys(checks):
    keys = set()
    for check in checks:
        keys.update(check.get('path', '').split('.'))
        field = check.get('field')
        if isinstance(field, str):
            keys.update(field.split('.'))
        value = check.get('value')
        if check.get('op') in {'fields_absent_or', 'any_row_matches'} and isinstance(value, dict):
            keys.update(value)
        if check.get('op') == 'rows_have_keys' and isinstance(value, list):
            keys.update(key for key in value if isinstance(key, str))
    return {key for key in keys if isinstance(key, str) and SAFE_KEY.fullmatch(key)}


class _Preview:
    def __init__(self, fields, *, request=False, priority_fields=frozenset()):
        self.fields = fields
        self.request = request
        self.priority_fields = priority_fields
        self.remaining = MAX_NODES
        self.truncated = False
        self.redacted = False
        self.omitted_fields = 0

    def hidden(self):
        self.redacted = True
        return REDACTED

    def project(self, value, *, field='', depth=0, paginated=False, private=False):
        if not self.remaining or depth > MAX_DEPTH:
            self.truncated = True
            return OMITTED
        self.remaining -= 1
        if value is None or type(value) is str and value == '':
            return value
        if private:
            return self.hidden()
        if isinstance(value, dict):
            return self.mapping(value, depth)
        if isinstance(value, list):
            self.truncated |= len(value) > MAX_ITEMS
            return [self.project(item, field=field, depth=depth + 1)
                    for item in islice(value, MAX_ITEMS)]
        if self.request:
            if field in REQUEST_NUMBERS and type(value) is int and 0 <= value <= 100000:
                return value
        else:
            if type(value) is bool and field in {'status', 'has_wallet_password'}:
                return value
            if type(value) is int and (
                field == 'updated_uid' and value == 0
                or paginated and field in {'s', 't'} and 0 <= value <= 100000000
            ):
                return value
            if (depth == 1 and field in MESSAGE_FIELDS and type(value) is str
                    and len(value) <= 120 and value.strip().casefold() in REVIEWED_MESSAGES):
                return value
        return self.hidden()

    def mapping(self, value, depth):
        result = {}
        if self.request:
            self.truncated |= len(value) > MAX_ITEMS
            items = islice(value.items(), MAX_ITEMS)
        else:
            items = self.response_items(value, depth)
        paginated = PAGINATION_KEYS <= value.keys() and isinstance(value.get('d'), (list, type(None)))
        for index, (key, item) in enumerate(items, 1):
            visible = isinstance(key, str) and key in self.fields
            label = key if visible else f'<hidden key {index}>'
            self.redacted |= not visible
            private = (isinstance(key, str) and key != 'has_wallet_password'
                       and bool(PRIVATE_CONTAINER.search(key)))
            result[label] = self.project(item, field=label, depth=depth + 1,
                                         paginated=paginated, private=private)
        return result

    def response_items(self, value, depth):
        priority = self.priority_fields | ENVELOPE_FIELDS if depth == 0 else self.priority_fields
        visible = [(key, item) for key, item in value.items() if isinstance(key, str) and key in self.fields]
        visible.sort(key=lambda pair: pair[0] not in priority)
        self.truncated |= len(visible) > MAX_ITEMS
        # Unknown keys can wrap structured data, such as a VIP level map.
        # Keep a bounded number of those branches with masked labels.
        branches = islice(
            ((key, item) for key, item in value.items()
             if (not isinstance(key, str) or key not in self.fields)
             and isinstance(item, (dict, list)) and item),
            max(0, MAX_ITEMS - len(visible)),
        )
        selected_branches = list(branches)
        omitted = len(value) - len(visible) - len(selected_branches)
        self.omitted_fields += omitted
        self.redacted |= omitted > 0
        return visible[:MAX_ITEMS] + selected_branches


def response_evidence(response, source, checks):
    body = response.get('body')
    priority_fields = reviewed_keys(source.get('expect', ()))
    priority_fields |= {
        key for check in checks if check.get('op') == 'fields_absent_or'
        for key in (check.get('value') or {}) if isinstance(key, str) and SAFE_KEY.fullmatch(key)
    }
    preview = _Preview(ENVELOPE_FIELDS | COMMON_FIELDS | priority_fields, priority_fields=priority_fields)
    result = {'body': preview.project(body), 'body_type': type(body).__name__,
              'truncated': preview.truncated, 'redacted': preview.redacted}
    if preview.omitted_fields:
        result['omitted_fields'] = preview.omitted_fields
    if response.get('decode_status') in ('decoded', 'empty', 'undecodable'):
        result['decode_status'] = response['decode_status']
    for key in ('body_bytes', 'elapsed_ms'):
        if type(response.get(key)) is int and response[key] >= 0:
            result[key] = response[key]
    return result


def request_evidence(route, source, step):
    """Use the registered contract, never the opened URL or authentication headers."""
    result = {key: route[key] for key in ('method', 'path', 'encoding') if key in route}
    fields = {
        field for key in ('query', 'body') if isinstance(source.get(key), dict)
        for field in source[key] if isinstance(field, str) and SAFE_KEY.fullmatch(field)
    }
    preview = _Preview(fields, request=True)
    for key in ('query', 'body'):
        if key in source and key in step:
            result[key] = preview.project(step[key])
    if preview.truncated:
        result['truncated'] = True
    if preview.redacted:
        result['redacted'] = True
    return result
