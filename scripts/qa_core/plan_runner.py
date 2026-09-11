"""Sequential execution and four-state results; adapters own I/O and business setup."""
import copy
import json
import time
from qa_core.execution_plan import at, MISSING, resolve, assertions


def execute(cases, adapter, run_id, checkpoint=None):
    results = []
    for case in cases:
        item = {'id':case['id'], 'status':'NOT_RUN', 'actual':case.get('blocked',''), 'steps':[]}
        results.append(item)
        if case.get('blocked') or not case.get('steps'):
            item['actual'] = case.get('blocked') or '仅人工执行；尚未导入人工结果，不计自动通过'
            if checkpoint: checkpoint(results)
            continue
        variables = {**copy.deepcopy(case['variables']), 'run':{'id':run_id}}
        stopped = False
        for source in case['steps']:
            step_result = {'id':source['id'], 'actor':source['actor'], 'status':'NOT_RUN', 'actual':'依赖步骤未通过'}
            item['steps'].append(step_result)
            if stopped and not source.get('diagnostic'): continue
            previously_stopped = stopped
            started = time.monotonic()
            try:
                step = resolve(source, variables)
                response = adapter.execute(step, case['id'])
                for key in ['evidence','error_category']:
                    if key in response: step_result[key] = response[key]
                if response.get('execution_error'): raise RuntimeError('business request outcome uncertain')
                if 'http' in response:
                    body = response.get('body')
                    step_result['observation'] = {'http':response['http'], 'business_status':body.get('status') if isinstance(body,dict) and type(body.get('status')) is bool else None}
                checks = assertions(step.get('expect', []), response)
                step_result['assertions'] = checks
                failed = [c for c in checks if c['status'] == 'FAIL']
                if failed:
                    step_result.update(status='FAIL', actual=json.dumps(failed,ensure_ascii=False))
                else:
                    extracted = {}
                    for key, path in step.get('extract', {}).items():
                        value = at(response,path)
                        if value is MISSING: raise ValueError('extraction path missing: ' + path)
                        extracted[key] = value
                    variables.update(extracted)
                    step_result.update(status='PASS', actual=response.get('summary','断言通过'))
            except Exception as error:
                import traceback
                step_result['error_locations'] = [{'file':frame.filename.rsplit('/',1)[-1], 'line':frame.lineno, 'function':frame.name} for frame in traceback.extract_tb(error.__traceback__)]
                if error.__cause__ is not None:
                    step_result['cause_type'] = type(error.__cause__).__name__
                # Error messages may contain requests, credentials or personal values.
                step_result.update(status='ERROR', actual=type(error).__name__ + '；请求/前置/提取失败，详见本轮检查点')
            step_result['elapsed_ms'] = round((time.monotonic()-started)*1000)
            if step_result['status'] != 'PASS' and not previously_stopped:
                stopped = True
                item.update(status=step_result['status'], actual=step_result['actual'], failed_step=source['id'])
            if checkpoint: checkpoint(results)
        if not stopped:
            item.update(status='PASS', actual='全部业务步骤及断言通过')
            if case.get('observational'):
                item.update(status='NOT_RUN',actual='已完成500/1000/2000字节独立观察；最大长度契约未知，不计边界验收PASS')
        item['recovery'] = getattr(adapter,'recoveries',{}).get(case['id'],[])
        if any(r['status'] != 'PASS' for r in item['recovery']):
            item['recovery_failed'] = True
            if item['status'] == 'PASS': item.update(status='ERROR',actual='业务断言通过，但权限恢复未获验证')
        item['elapsed_ms'] = sum(s.get('elapsed_ms',0) for s in item['steps'])
        if checkpoint: checkpoint(results)
    return results
