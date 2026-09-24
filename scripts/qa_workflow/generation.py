"""AI business-case drafts with source hashes; fixed executable plans remain authoritative."""
from requirement_paths import requirement_dir
import json
import re
from pathlib import Path
from qa_delivery.pipeline import ai, obj, STRING, STRINGS, write_json, redact_value
from qa_delivery.state import digest
from qa_core.case_report import csv_text

CASE_SCHEMA = obj({'id':STRING, 'layer':{'type':'string','enum':['API','UI','FLOW']},
    'title':STRING,'preconditions':STRING,'steps':STRINGS,'expected':STRING,
    'source_ids':STRINGS,'acceptance_ids':STRINGS,'data_requirements':STRINGS,'blockers':STRINGS})
SCHEMA = obj({'summary':STRING,'cases':{'type':'array','items':CASE_SCHEMA},'questions':STRINGS})


def context(root, story):
    if not re.fullmatch(r'ISOP-\d+',story): raise ValueError('invalid requirement')
    directory = requirement_dir(root, story)
    sources = {}
    for name in ('design.md','questions.md','test-cases.md','api/test-cases.md','evidence-sync.md','evidence-sync.json','preparation.csv','api/contract-review.md','api/data-review.md','plan.json','api/cases.json'):
        path = directory/name
        if path.is_file():
            text = path.read_text(encoding='utf-8-sig')
            sources[name] = {'sha256':digest(text),'text':text}
    if not {'design.md','test-cases.md'} <= sources.keys(): raise ValueError('缺少需求设计或业务用例来源')
    return {'story':story,'sources':sources}


def validate(value, data):
    if not isinstance(value,dict) or not isinstance(value.get('summary'),str) or not isinstance(value.get('questions'),list):
        raise ValueError('invalid AI case response')
    cases = value.get('cases')
    if not isinstance(cases,list) or not cases or len(cases)>300: raise ValueError('empty or excessive generated cases')
    seen = set()
    source_text = '\n'.join(s['text'] for s in data['sources'].values())
    known = set(re.findall(r'\b(?:AC-\d+|C\d+|R\d+|ISOP-\d+-C\d+)\b',source_text))
    for case in cases:
        if set(case) != set(CASE_SCHEMA['properties']): raise ValueError('invalid generated case fields')
        if not re.fullmatch(r'DRAFT-\d+',case['id']) or case['id'] in seen: raise ValueError('duplicate/invalid draft ID')
        seen.add(case['id'])
        if case['layer'] not in ('API','UI','FLOW'): raise ValueError('invalid layer')
        for name in ('title','preconditions','expected'):
            if not isinstance(case[name],str) or not case[name].strip(): raise ValueError('missing business expectation')
        for name in ('steps','source_ids','acceptance_ids','data_requirements','blockers'):
            if not isinstance(case[name],list) or any(not isinstance(v,str) or not v.strip() for v in case[name]): raise ValueError('invalid generated list')
        if not case['steps'] or not case['source_ids'] or not set(case['source_ids']) <= data['sources'].keys(): raise ValueError('invented/missing source')
        if not set(case['acceptance_ids']) <= known: raise ValueError('invented acceptance reference')
        if not case['acceptance_ids'] and not case['blockers']: raise ValueError('missing acceptance reference must remain blocked')
    return value


def generate(state, story, config, analyzer=ai, validate_output=False):
    from .evidence import review
    evidence = review(state.root, story)
    if evidence['errors']:
        raise ValueError('证据同步基线已失效：' + '；'.join(evidence['errors']))
    data = context(state.root,story)
    key = digest([data, SCHEMA])
    folder = state.directory/'generation'/story/key
    folder.mkdir(parents=True, exist_ok=True)
    accepted = folder/'validated.json'
    if accepted.is_file():
        cached = json.loads(accepted.read_text(encoding='utf-8'))
        validate(cached,data)
        return cached
    if validate_output:
        saved_context = json.loads((folder/'cases-context.json').read_text(encoding='utf-8'))
        if saved_context != redact_value(data): raise ValueError('saved AI context differs from current sources')
        value = json.loads((folder/'cases.json').read_text(encoding='utf-8'))
    else:
        (folder/'cases.json').unlink(missing_ok=True)
        value = analyzer(config,folder,'cases',
            'Generate Chinese business test cases from the supplied confirmed requirements. Use DRAFT-001 style IDs. '
            'Separate API and manual UI checks. Include positive, rejection/no-side-effect, boundary, permissions, '
            'independent data reconciliation and asynchronous risks where applicable. '
            'source_ids must be supplied file names; acceptance_ids must literally exist in sources. '
            'Never invent endpoints, expected formulas, sample IDs or decisions. Record unresolved dependencies in blockers/questions. '
            'Use evidence-sync source coverage and decisions when present. Unread sources are gaps, not proof of missing requirements. '
            'Respect confirmed scope exclusions and never reopen resolved questions because historical text differs. '
            'Do not copy API responses as expected values. This is a draft, not executed code or a PASS result.', data, SCHEMA)
    validate(value,data)
    value.update(case_checks={c['id']: ('BLOCKED_EXPECTATION' if not c['acceptance_ids'] else 'BLOCKED' if c['blockers'] else 'DRAFT_LINKED') for c in value['cases']},
                 story=story, source_sha256=key, source_hashes={n:s['sha256'] for n,s in data['sources'].items()},
                 status='DRAFT',note='AI草稿；未覆盖原用例/计划/人工状态，业务预期及可执行映射仍须核对')
    write_json(accepted,value)
    headers = ['草稿编号','类型','用例名称','前置条件','步骤','预期','验收点','来源','数据要求','阻塞']
    rows = [dict(zip(headers,[c['id'],c['layer'],c['title'],c['preconditions'],' → '.join(c['steps']),c['expected'],','.join(c['acceptance_ids']),','.join(c['source_ids']),'; '.join(c['data_requirements']),'; '.join(c['blockers'])])) for c in value['cases']]
    (folder/'cases.csv').write_text(csv_text(rows,headers),encoding='utf-8')
    state.append(story,'generation',{'status':'AI用例草稿已生成','source':str(accepted.relative_to(state.root)) if accepted.is_relative_to(state.root) else str(accepted),
                  'source_sha256':key,'count':len(value['cases']),'questions':value['questions']})
    return value
