"""Whitelist screenshots linked to this run. No image creation or API calls."""
import hashlib
import json
from datetime import datetime
from pathlib import Path


def visual_gallery(state, root=Path('.')):
    root = root.resolve()
    images, notes = [], []
    start, end = state.get('startedAt', 0)*1000, state.get('finishedAt', 0)*1000
    def load(name):
        try:
            value = json.loads((root / 'ui/results' / name).read_text())
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}
    def add(item, expected_run, prefix='', minimum=None):
        if not isinstance(item, dict) or not item.get('path'):
            return False
        file = (root / item['path']).resolve()
        base = root / 'ui/results/screenshots'
        if not file.is_relative_to(base) or file.suffix != '.png' or not file.is_file():
            return False
        if item.get('runId') != expected_run or not (start if minimum is None else minimum) <= item.get('capturedAt', 0) <= end:
            return False
        if hashlib.sha256(file.read_bytes()).hexdigest() != item.get('sha256'):
            return False
        images.append({'src': '../results/screenshots/' + file.name, 'title': item.get('title', file.stem), 'caption': prefix + item.get('kind', '截图留证') + ' · ' + item.get('assertion', '')})
        return True
    kyc = load('client-kyc-submit.json')
    count = 0
    if state.get('kycRunId') and kyc.get('runId') == state['kycRunId']:
        kyc_run = load('kyc-ui-run-status.json')
        minimum = start
        try:
            if kyc_run.get('runId') == state['kycRunId']:
                minimum = max(start - 3600000, datetime.fromisoformat(kyc_run['startedAt'].replace('Z', '+00:00')).timestamp()*1000)
        except (KeyError, ValueError):
            pass
        for item in kyc.get('visualEvidence', {}).values():
            if item.get('privacy') == 'status_label_only':
                count += add(item, state['kycRunId'], minimum=minimum)
    if not count:
        notes.append('KYC：本轮未保存可关联的状态截图；仅保留已有结构化断言，不补拍历史提交画面。')
    for name, phase, key, field, legacy, title, caption in [
        ('client-deposit-contract.json','deposit_ui','depositId','depositResponse','deposit-contract-after.png','充值：建单后的支付页面','已核对 UI 金额和非活动参数；支付页面截图不代表实际到账。'),
        ('client-withdraw-contract.json','withdraw_ui','withdrawId','legalResponse','withdraw-legal-amount.png','提现：成功提示及订单详情','核对页面成功提示、金额与订单号；Pending 不代表最终出款。'),
    ]:
        data = load(name)
        linked = bool(state.get(key)) and data.get(field, {}).get('orderId') == state[key]
        if not linked:
            notes.append(title + '：缺少本轮关联截图。')
            continue
        current = sum(add(item, state.get('runId')) for item in data.get('visualEvidence', {}).values())
        # Legacy images have no digest; use only fixed, known paths from completed
        # same-order stages and a strict capture mtime window. Label their origin.
        file = root / 'ui/results/screenshots' / legacy
        if not current and not data.get('visualEvidence') and phase in state.get('completed', []) and file.is_file() and start <= file.stat().st_mtime*1000 <= end:
            images.append({'src':'../results/screenshots/'+legacy,'title':title,'caption':'本轮已有截图（旧版未记录哈希） · '+caption})
    game = load('game-round-state.json')
    current = 0
    if game.get('runId') == state.get('runId'):
        for item in game.get('visualEvidence', {}).values():
            current += add(item, state.get('runId'))
    if not current:
        notes.append('游戏：本轮没有可验证的识别裁剪图；已有全页截图只作 UI 留证，不能冒充新的图片断言。')
        bet = load('client-game-bet-smoke.json')
        file = root / 'ui/results/screenshots/lucky_penny-after-spin.png'
        if 'bet_ui' in state.get('completed', []) and bet.get('game', {}).get('id') == 'lucky_penny' and file.is_file() and start <= file.stat().st_mtime*1000 <= end:
            images.append({'src':'../results/screenshots/'+file.name,'title':'游戏：投注后的页面','caption':'本轮已有全页截图；实际付费笔数和结算以对应记录断言为准。'})
    def order(item):
        name = item['src'].rsplit('/', 1)[-1]
        return 0 if name.startswith('kyc-') else 1 if name.startswith('deposit-') else 3 if name.startswith('withdraw-') else 2
    return sorted(images, key=order), notes
