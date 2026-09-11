"""Offline UI step/asset validation; no business environment or browser needed."""
import json
import re
from pathlib import Path

OPERATIONS = {'open','click','fill','select','check','upload','wait','press','scroll','observe'}
PROPERTIES = {'count','url','disabled','text','value','loaded','visible'}


def asset_path(plan):
    value = plan.get('ui',{}).get('assets','')
    if not value.startswith('ui/data/') or '..' in Path(value).parts or not value.endswith('.json'):
        raise ValueError('UI assets must be a repository data file')
    return Path(__file__).resolve().parents[2]/value


def load_assets(plan):
    assets = json.loads(asset_path(plan).read_text())
    for page in assets['pages'].values():
        if page['service'] not in plan['services'] or not page['path'].startswith('/') or page['path'].startswith('//'):
            raise ValueError('invalid UI page service/path')
    def locator(spec):
        if not isinstance(spec,dict) or sum(k in spec for k in ['css','role','label','testId','text']) != 1:
            raise ValueError('locator needs exactly one strategy')
        if spec.get('scope'): locator(spec['scope'])
        if 'index' in spec and (type(spec['index']) is not int or type(spec.get('expectedCount')) is not int or not 0 <= spec['index'] < spec['expectedCount']):
            raise ValueError('indexed document slot needs guarded collection size')
    for element in assets['elements'].values(): locator(element)
    for rule in assets['requests']:
        if rule['method'] not in {'GET','POST'} or not rule['path_pattern'].startswith('^') or not rule['path_pattern'].endswith('$'):
            raise ValueError('UI request rules must be anchored')
        re.compile(rule['path_pattern'])
    return assets


def validate_ui(plan, step):
    assets = load_assets(plan)
    if step.get('op') not in OPERATIONS or step.get('page') not in assets['pages']:
        raise ValueError('unknown UI operation/page')
    page = assets['pages'][step['page']]
    if page['service'] not in plan['actors'][step['actor']]['services']:
        raise ValueError('UI actor/service mismatch')
    if step['op'] not in {'open','press'} and step.get('element') not in assets['elements']:
        raise ValueError('unknown UI element')
    from qa_core.execution_plan import references
    if step.get('element'):
        for ref in references(assets['elements'][step['element']]):
            if ref.split('.')[0] not in step.get('bindings',{}):
                raise ValueError('UI element binding missing')
    if step['op']=='observe' and step.get('property') not in PROPERTIES:
        raise ValueError('unknown UI observation')
    if step['op']=='upload' and (type(step.get('size')) is not int or not 100 <= step['size'] <= 1000000):
        raise ValueError('invalid synthetic upload size')
    if step['op'] in {'fill','select','check','press'} and 'value' not in step:
        raise ValueError('UI operation requires value')
    if not all(any(c.get('path')==key and c.get('op')=='eq' and c.get('value') is True for c in step.get('expect',[])) for key in ['checks.completed','checks.policy']):
        raise ValueError('UI completion and policy expectations required')
    if not step.get('expect'):
        raise ValueError('UI step needs explicit expectations')
    if step.get('response'):
        response = step['response']
        route = plan['contracts'].get(response.get('contract'))
        if not route or route['service'] != page['service']:
            raise ValueError('unknown UI response contract')
        if step['op'] not in {'click','upload'}:
            raise ValueError('response must be armed on triggering action')
        if response.get('none'):
            if not 100 <= response.get('window_ms',0) <= 5000 or not any(c['path']=='request_count' and c['op']=='eq' and c['value']==0 for c in step['expect']):
                raise ValueError('negative response needs bounded observation/count assertion')
        elif not all(any(c['path']==key and c['op']=='eq' for c in step['expect']) for key in ['http','body.status']):
            raise ValueError('UI response needs HTTP/business assertions')
        if route.get('ownership') and route['ownership'] not in response.get('match',{}):
            raise ValueError('UI write response needs record correlation')
    return assets
