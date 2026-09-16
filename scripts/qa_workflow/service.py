"""Shared preflight and finite event-to-API orchestration; no Jira writes/outbox."""
import json
from pathlib import Path
import re
from types import SimpleNamespace
from qa_core.execution_plan import load
from qa_core.case_catalogue import design_rows, overview_rows, plan_api_rows
from qa_core.local_lock import local_run_lock
from qa_delivery.state import digest
from qa_delivery.requirement_bridge import task_plan
from qa_delivery.pipeline import run_pipeline, check_account
from filbet.requirement_adapter import Adapter, METHODS
from .generation import context
from .state import collect_results
from .evidence import review


def preflight(state, config, story, environment='FAT', payload=None, policy=None):
    reasons, warnings = [], []
    evidence = review(state.root, story)
    warnings.append('证据同步：' + evidence['status'] + '；' + '；'.join(evidence['errors'] + evidence['pending']))
    reasons.extend(evidence['errors'])
    policy = policy or json.loads((state.root/'config/workflow.json').read_text(encoding='utf-8'))
    rule = policy.get('stories',{}).get(story,{})
    if rule.get('paused'):
        reasons.append('已暂停：' + (rule.get('pause_reason') or '按当前状态及用户范围不执行'))
    elif story == 'ISOP-2022':
        reasons.append('2022等待修复，暂停优先；需用户重新开测指令')
    if environment != 'FAT': reasons.append('本轮仅适配FAT；UAT不在范围内')
    if not rule.get('authorized'): reasons.append('本需求尚无可沿用的自动执行授权')
    if story not in config['stories'] or environment not in config['stories'].get(story,{}).get('environments',[]):
        reasons.append('需求/环境未配置')
    payload = payload or {'story':story,'environment':environment,'build':'未提供','scopes':['api','ui']}
    selection = None
    try:
        sources = context(state.root,story)
        source_hash = digest(sources)
        selection = task_plan(state.root,config,payload)
        if not selection:
            reasons.append('尚无统一执行计划；保留旧CLI，自动触发不猜测旧契约')
        else:
            plan,cases,_ = load(state.root/'requirements'/story/'plan.json',METHODS)
            business = overview_rows(design_rows(state.root/'requirements'/story/'test-cases.md',story),story)
            api_rows = plan_api_rows(plan,cases,{r['用例编号'] for r in business})
            warnings.append(f'业务用例关联已检查：{len(business)} 条总用例、{len(api_rows)} 条API组合；不代表未覆盖能力已实现')
            if selection['plan_sha256'] != rule.get('plan_sha256'):
                reasons.append('计划尚未通过本轮本地检查绑定，或已变更')
            if not selection['automatic_ids']: reasons.append('当前范围没有已就绪API用例')
            if selection['blocked']: warnings.append('部分用例未就绪，保留NOT_RUN：'+json.dumps(selection['blocked'],ensure_ascii=False))
            if set(selection['allow_write']) - set(rule.get('allow_write',[])):
                reasons.append('配置写入范围超过已保存授权')
            if not reasons:
                plan,cases,_ = load(state.root/'requirements'/story/'plan.json',METHODS)
                selected = [c for c in cases if c['id'] in selection['automatic_ids']]
                env = config['environments'][environment]
                args = SimpleNamespace(env=str(state.root/env['env_file']),allow_write=selection['allow_write'],timeout=15,insecure=selection['insecure'])
                adapter = Adapter(plan,args,state.directory/'preflight')
                adapter.preflight(selected)
                check_account(config,{'env_file':str(state.root/env['env_file'])})
            warnings.append('离线检查不证明样本/业务就绪；运行时仍检查本轮fixture和独立断言')
    except (ValueError,OSError,KeyError) as error:
        reasons.append('执行前检查失败：'+(str(error) if isinstance(error,ValueError) else type(error).__name__))
        source_hash = None
    return {'story':story,'status':'BLOCKED' if reasons else 'READY','reasons':reasons,'warnings':warnings,
            'environment':environment,'execution':selection,'sources_sha256':source_hash,'policy_sha256':digest(policy)}


def event_reason(candidate):
    messages = candidate.get('source_messages') or [{'action':candidate.get('ai_action'), 'environment_source':candidate.get('environment_source',''), 'text':candidate.get('text',''), 'scope_note':candidate.get('scope_note','')}]
    if any(m.get('action') != 'READY' for m in messages): return '消息包含不确定/撤回信息，保留待核对'
    if candidate.get('environment') != 'FAT': return '提测环境不属于本轮FAT范围'
    if any(m.get('environment_source') != 'AI evidence' for m in messages): return '提测环境未明确；本地默认FAT不等于已确认环境'
    if 'api' not in candidate.get('scopes',[]): return '本次为人工UI范围'
    if not any(re.search(r'API|接口|后端|backend',m.get('scope_note','')+' '+m.get('text',''),re.I) for m in messages):
        return '消息未明确接口提测，默认API范围不能充当部署依据'
    return ''


def process_candidates(state, config, preview, *, execute=False, jira=None, pipeline=run_pipeline):
    outcomes = []
    for candidate in preview.get('candidates',[]):
        story = candidate['story']
        check = preflight(state,config,story,candidate['environment'],candidate)
        reason = event_reason(candidate)
        if preview.get('pending_analysis'): reason = '尚有消息未完成分析'
        if reason:
            check['reasons'].append(reason)
            check['status'] = 'BLOCKED'
        payload = {**candidate,'execution':check['execution']}
        key = digest([story,candidate['environment'],candidate['build'], sorted(candidate['member_ids']),
                      check['execution'],check['sources_sha256'],check['policy_sha256']])
        state.append(story,'preflight',{**check,'source':'reports/telegram/preview.json','event_key':key},key='preflight:'+digest([key,check]))
        result = {'story':story,'event_key':key,'status':check['status'],'reasons':check['reasons']}
        outcomes.append(result)
        if not execute or check['status'] != 'READY': continue
        if jira is None: raise ValueError('执行前需要Jira只读核对父需求')
        if any(jira.resolve_story(issue)['story'] != story for issue in candidate['issues']):
            result.update(status='BLOCKED',reasons=['Jira父需求与事件不符'])
            continue
        # Re-read mutable files immediately before claiming the event.
        again = preflight(state,config,story,candidate['environment'],candidate)
        if again != check: raise ValueError('计划、来源或执行配置已变化，请重跑检查')
        if not state.claim(key,payload):
            result['status'] = 'ALREADY_CLAIMED'
            continue
        folder = state.directory/'runs'/key[:24]
        try:
            job = {'payload':json.dumps(payload,ensure_ascii=False),'config_hash':digest(config)}
            report = pipeline(config,job,folder)
            result['status'] = report['status']
            state.finish(key,report['status'])
            state.append(story,'execution',{'status':report['status'],'source':str(folder.relative_to(state.root)/'report.html'),
                'event_key':key,'note':'BUG候选只生成本地HTML；未建单、未发群'})
        except Exception:
            state.finish(key,'INTERRUPTED')
            raise
    collect_results(state)
    return outcomes
