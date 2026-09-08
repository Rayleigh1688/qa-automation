"""Project existing assertion evidence into a safe, per-step report (no requests)."""
import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from p0_report_template import write_html_report
from ui_business_visuals import visual_gallery

PHASES = {
    'fund_preflight': '资金账号前置', 'kyc_ui': 'KYC 提交、审核与刷新',
    'deposit_ui': 'UI 非活动充值建单', 'deposit_credit': '充值补单与到账',
    'bet_ui': 'UI 游戏与付费投注', 'bet_reconcile': '投注、派奖与钱包',
    'turnover_clear': '后台显式清零', 'withdraw_ui': 'UI 提现提交', 'reconcile': '前后台订单及账变对账',
}


def read(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def number(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def collect_assertions(state, root=Path('.')):
    result = []
    completed = state.get('completed', [])
    def check(phase, name, expected, actual, predicate, source, status=None):
        if status is None:
            active = {'preflight': 'fund_preflight', 'bet_baseline': 'bet_ui', 'withdraw_preflight': 'withdraw_ui'}.get(state.get('stage'), state.get('stage'))
            attempted = phase in completed or (state.get('status') == 'BLOCKED' and phase == active)
            status = 'NOT_RUN' if not attempted else 'NOT_RECORDED' if actual is None else 'PASS' if predicate else 'FAIL'
        result.append({'id': f'UIA-{len(result)+1:03}', 'phase': phase, 'name': f'{PHASES[phase]} · {name}', 'expected': expected, 'actual': actual if actual is not None else '缺少本轮证据', 'status': status, 'detail': source})
    def linked(filename, predicate):
        value = read(root / 'ui/results' / filename, {})
        return value if isinstance(value, dict) and predicate(value) else {}
    def in_window(value):
        try:
            ts = datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
            return state['startedAt'] <= ts <= state['finishedAt']
        except (ValueError, TypeError, KeyError, AttributeError):
            return False
    support_path = root / 'api/results/ui-fund-support.json'
    records = read(support_path, [])
    records = [r for r in records if isinstance(r, dict)] if isinstance(records, list) else []
    support_ok = support_path.exists() and state.get('supportSha256') == hashlib.sha256(support_path.read_bytes()).hexdigest()
    # Legacy run has no hash: only link the exact UI deposit's approval evidence.
    if not support_ok and not state.get('supportSha256'):
        support_ok = bool(state.get('depositId')) and any(r.get('name') == 'admin_deposit_manual_success' and str(r.get('deposit_id')) == state['depositId'] for r in records)
    if not support_ok:
        records = []
    def record(name):
        return next((r for r in records if r.get('name') == name), {})
    def data(name):
        value = record(name).get('data')
        return value if isinstance(value, dict) else {}
    src = 'api/results/ui-fund-support.json'
    kyc_status = data('fund_kyc').get('kyc_status')
    check('fund_preflight', '资金号 KYC 已通过', 5, kyc_status, kyc_status == 5, src + ' · fund_kyc')
    accounts = record('fund_accounts').get('data')
    count = sum(isinstance(a, dict) and a.get('status') == 1 for a in accounts) if isinstance(accounts, list) else None
    check('fund_preflight', '存在有效提款账户', '≥1', count, count is not None and count > 0, src + ' · fund_accounts')
    kyc = linked('client-kyc-submit.json', lambda r: bool(state.get('kycRunId')) and r.get('runId') == state['kycRunId'])
    sub = kyc.get('submission', {})
    for name, expected, actual in [('提交前可提交状态', 0, kyc.get('beforeStatus')), ('成功上传附件数', 3, sub.get('successfulUploads')), ('提交业务成功', True, sub.get('businessStatus')), ('页面提交成功提示', True, sub.get('successVisible')), ('UI 提交后待审状态', 2, kyc.get('afterStatus')), ('本轮后台审核成功', True, kyc.get('adminApproved')), ('fresh UI 刷新审核通过', 5, kyc.get('approvedStatus'))]:
        check('kyc_ui', name, expected, actual, actual == expected, 'ui/results/client-kyc-submit.json')
    deposit = linked('client-deposit-contract.json', lambda r: bool(state.get('depositId')) and r.get('depositResponse', {}).get('orderId') == state['depositId'])
    amount = deposit.get('depositRequest', {}).get('amount')
    expected_amount = state.get('depositAmount', record('wallet_after_deposit').get('expected_balance_delta'))
    for name, expected, actual, ok in [('UI 提交金额', expected_amount, amount, number(amount) is not None and number(amount) == number(expected_amount)), ('非活动充值参数', True, deposit.get('nonBonusConfirmed'), deposit.get('nonBonusConfirmed') is True), ('建单业务成功', True, deposit.get('depositResponse', {}).get('businessStatus'), deposit.get('depositResponse', {}).get('businessStatus') is True), ('UI 订单与本轮订单一致', True, True if deposit else None, bool(deposit))]:
        check('deposit_ui', name, expected, actual, ok, 'ui/results/client-deposit-contract.json')
    approval = record('admin_deposit_manual_success')
    check('deposit_credit', '本次订单补单成功', True, approval.get('business_status'), approval.get('business_status') is True and str(approval.get('deposit_id')) == state.get('depositId'), src + ' · admin_deposit_manual_success')
    delta = record('wallet_after_deposit').get('actual_balance_delta')
    check('deposit_credit', '钱包到账增量等于充值额', expected_amount, delta, number(delta) is not None and number(delta) == number(expected_amount), src + ' · wallet_after_deposit')
    bet = linked('client-game-bet-smoke.json', lambda r: in_window(r.get('scannedAt')) and (not r.get('runId') or r['runId'] == state.get('runId')))
    paid = bet.get('paidEvidence', {})
    target = state.get('paidBetTarget')
    check('bet_ui', '本轮实际付费笔数', target, paid.get('paidBetRecords'), paid.get('accepted') is True and paid.get('paidBetRecords') == target, 'ui/results/client-game-bet-smoke.json · paidEvidence（不是点击数）')
    frames = bet.get('frames', [])
    markers = bet.get('game', {}).get('expectedFrameText', [])
    identity = all(any(marker in frame for frame in frames) for marker in markers) if markers and frames else None
    check('bet_ui', '配置的厂商及游戏身份匹配', True, identity, identity is True, 'ui/results/client-game-bet-smoke.json · frames/expectedFrameText')
    events = read(root / 'ui/results/game-round-state.json', {}).get('events', [])
    events = [e for e in events if state.get('startedAt', float('inf'))*1000 <= e.get('ts', 0) <= state.get('finishedAt', 0)*1000]
    ready = events[-1].get('state') == 'ready' if events else None
    check('bet_ui', '最终画面恢复普通投注状态', True, ready, ready is True, 'ui/results/game-round-state.json · 最后状态')
    free = any(e.get('state') == 'free' for e in events)
    free_start, durations = None, []
    for event in events:
        if event.get('state') == 'free' and free_start is None:
            free_start = event['ts']
        if event.get('state') == 'ready' and free_start is not None:
            durations.append(event['ts'] - free_start)
            free_start = None
    recovered = bool(durations) and free_start is None and all(0 <= duration <= 60000 for duration in durations)
    check('bet_ui', '免费旋转等待分支', '5 秒复查、60 秒内恢复 ready', '本轮未触发' if events and not free else {'恢复耗时毫秒': durations, '仍在免费局': free_start is not None} if free else None, recovered, 'ui/results/game-round-state.json；未触发不算通过', status='NOT_TRIGGERED' if events and not free and 'bet_ui' in completed else None)
    rec = state.get('betReconciliation', {})
    check('bet_reconcile', '全部新增投注及派奖已结算', True, rec.get('settled'), rec.get('settled') is True, 'ui-business-run-status.json · betReconciliation')
    check('bet_reconcile', '付费金额合计', target*100 if isinstance(target, int) else None, rec.get('betAmount'), number(rec.get('betAmount')) == number(target*100 if isinstance(target, int) else None), 'ui-business-run-status.json · betReconciliation')
    check('bet_reconcile', '钱包变化等于投注净输赢（含零投注派奖）', rec.get('netAmount'), rec.get('walletDelta'), number(rec.get('walletDelta')) is not None and number(rec.get('walletDelta')) == number(rec.get('netAmount')), 'ui-business-run-status.json · betReconciliation')
    turnover = state.get('turnover', {})
    if 'baselineStatus' in turnover:
        check('bet_ui', '本轮充值流水已就绪后才允许投注', 'READY', turnover['baselineStatus'], turnover['baselineStatus'] == 'READY', 'ui-business-run-status.json · turnover.baselinePolls（5 秒查询、最长 60 秒）')
    before, after = number(turnover.get('beforeBets')), number(turnover.get('afterBets'))
    check('turnover_clear', '清零前已通过 UI 投注降低流水', f"小于 {turnover.get('beforeBets', '未记录')}", turnover.get('afterBets'), before is not None and after is not None and after < before, 'ui-business-run-status.json · turnover')
    check('turnover_clear', '后台处理后剩余流水', 0, turnover.get('afterAdminClear'), number(turnover.get('afterAdminClear')) == 0, 'ui-business-run-status.json · turnover（后台清零，不是自然完成）')
    withdraw = linked('client-withdraw-contract.json', lambda r: bool(state.get('withdrawId')) and r.get('transactionId') == state['withdrawId'])
    for name, expected, actual, ok in [('页面创建订单成功', True, withdraw.get('legalOrderCreated'), withdraw.get('legalOrderCreated') is True), ('建单业务成功', True, withdraw.get('legalResponse', {}).get('businessStatus'), withdraw.get('legalResponse', {}).get('businessStatus') is True), ('UI 金额与实际请求一致', withdraw.get('legalAmount'), withdraw.get('legalResponse', {}).get('amount'), number(withdraw.get('legalAmount')) is not None and number(withdraw.get('legalAmount')) == number(withdraw.get('legalResponse', {}).get('amount'))), ('页面订单号等于响应订单号', True, withdraw.get('transactionId') == withdraw.get('legalResponse', {}).get('orderId') if withdraw else None, bool(withdraw) and withdraw.get('transactionId') == withdraw.get('legalResponse', {}).get('orderId'))]:
        check('withdraw_ui', name, expected, actual, ok, 'ui/results/client-withdraw-contract.json')
    reconciliation = state.get('reconciliation', {})
    check('reconcile', '前后台提现同订单、UID、金额', True, reconciliation.get('sameUid'), reconciliation.get('sameUid') is True and reconciliation.get('orderId') == state.get('withdrawId') and number(reconciliation.get('amount')) == number(withdraw.get('legalAmount')), 'ui-business-run-status.json · reconciliation')
    check('reconcile', '提现提交阶段状态', 'under_review', reconciliation.get('status'), reconciliation.get('status') == 'under_review', 'ui-business-run-status.json · reconciliation；不代表最终出款')
    tx = state.get('transactions', {})
    check('reconcile', '新增账变全部匹配后台 ID/金额/前后余额', tx.get('newRecords'), tx.get('clientAdminMatched'), isinstance(tx.get('newRecords'), int) and tx['newRecords'] > 0 and tx.get('newRecords') == tx.get('clientAdminMatched'), 'ui-business-run-status.json · transactions')
    check('reconcile', '账变合计等于全流程钱包增量', tx.get('walletDelta'), tx.get('transactionSum'), number(tx.get('walletDelta')) is not None and number(tx.get('walletDelta')) == number(tx.get('transactionSum')), 'ui-business-run-status.json · transactions')
    return result


def render_report(state, root=Path('.')):
    assertions = state.get('assertions') or collect_assertions(state, root)
    aliases = {'preflight': 'fund_preflight', 'bet_baseline': 'bet_ui', 'withdraw_preflight': 'withdraw_ui'}
    failed_phase = aliases.get(state.get('stage'), state.get('stage'))
    items = [{'id': str(i+1), 'name': label, 'group': '受控 UI 业务流程', 'kind': 'UI/API 协作', 'status': 'PASS' if phase in state['completed'] else 'FAIL' if phase == failed_phase and state['status'] == 'BLOCKED' else 'NOT_RUN', 'detail': state.get('error', '') if phase == failed_phase else '具体断言见上方表格'} for i, (phase, label) in enumerate(PHASES.items())]
    verdict = state['status']
    if verdict == 'PASS' and any(a['status'] == 'FAIL' for a in assertions):
        verdict = 'EVIDENCE_MISMATCH'
    elif verdict == 'PASS' and any(a['status'] == 'NOT_RECORDED' for a in assertions):
        verdict = 'EVIDENCE_INCOMPLETE'
    images, image_notes = visual_gallery(state, root)
    bet = state.get('betReconciliation', {})
    def money(value):
        parsed = number(value)
        return f'{parsed:,.2f}' if parsed is not None else '未记录'
    highlights = [{'label': '实际付费投注', 'value': money(bet.get('betAmount')), 'detail': f"{bet.get('paidBetRecords', '未记录')} 笔付费；{bet.get('zeroBetRecords', '未记录')} 条零投注记录"}, {'label': '投注净额 / 钱包变化', 'value': f"{money(bet.get('netAmount'))} / {money(bet.get('walletDelta'))}", 'detail': '包含派奖，数值来自已执行的对账'}, {'label':'全流程账变 / 钱包变化', 'value': f"{money(state.get('transactions', {}).get('transactionSum'))} / {money(state.get('transactions', {}).get('walletDelta'))}", 'detail':'包含充值、投注、派奖及提现'}]
    write_html_report(title='FAT UI 业务流程', scope='FAT', report_kind='受控 UI 全流程', verdict=verdict, verdict_detail=state.get('error', ('本轮经检查点续跑完成；' if state.get('resumedAt') or state.get('resumedReconciliationAt') else '') + 'UI 建单及付费投注；后台显式清流；提现待审不等于出款'), items=items, output=root / 'ui/reports/ui-business-report.html', metadata=[('原运行结论', state['status']), ('运行 ID', state.get('runId', '')), ('付费投注目标', str(state.get('paidBetTarget')))], evidence={'images': images, 'images_first': True, 'image_note': ' '.join(image_notes) + ' 点击原图放大；DOM 截图留证与实际图片识别输入分别标注。', 'highlights': highlights, 'checks': assertions, 'checks_title': '逐步骤断言', 'checks_note': 'PASS=证据满足；NOT_TRIGGERED=未触发；NOT_RECORDED=缺少明细；NOT_RUN=步骤未完成。汇总卡统计业务步骤，不是单元测试。'})
