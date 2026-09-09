"""Build UI-only presentation evidence from artifacts inside one run window."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

SOURCES = {
    'client-login-positive.json': '登录正例',
    'client-login-negative.json': '登录反例',
    'client-main-flow-ui.json': '主导航页面扫描',
    'client-deposit-contract.json': '充值页面契约',
    'client-game-bet-smoke.json': '指定游戏启动',
    'client-p0-positive-negative.json': '页面状态正反例',
}
PURPOSES = {
    'client-login.spec.mjs': '核验认证结果和登录后的页面状态；反例验证登录前置与拒绝行为。',
    'client-main-flow.spec.mjs': '检查首页及主导航页面可访问，并记录页面状态与真实网络请求。',
    'client-deposit-contract.spec.mjs': '检查充值支付方式、金额控件和活动选择；是否提交请求以本轮证据为准。',
    'client-game-bet-smoke.spec.mjs': '核验配置游戏启动及页面身份；真实 Spin 次数单独展示。',
    'client-p0-positive-negative.spec.mjs': '检查游客、无效游戏、缺少验证码及登录后钱包等页面状态。',
}


def timestamp(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError):
        return None


def run_window(source, status):
    stats = source.get('stats', {}) if isinstance(source, dict) else {}
    start = timestamp(stats.get('startTime'))
    if start is not None:
        try:
            return start, start + float(stats['duration']) / 1000
        except (KeyError, ValueError, TypeError):
            return None
    return None  # No Playwright run means no unrelated sidecar may be attached.


def fresh(path, window, data=None):
    if not window or not path.is_file():
        return False
    value = None
    if isinstance(data, dict):
        value = timestamp(data.get('scannedAt') or data.get('executedAt'))
    value = path.stat().st_mtime if value is None else value
    return window[0] - 2 <= value <= window[1] + 2


def relative_link(path, output):
    return quote(os.path.relpath(path.resolve(), output.parent.resolve()), safe='/.-_')


def build_evidence(source, status, items, input_path, output):
    directory = input_path.parent.resolve()
    window = run_window(source, status)
    evidence = {
        'highlights': [], 'timeline': [], 'checks': [], 'images': [], 'artifacts': [],
        'timeline_title': 'UI 用例执行轨迹', 'timeline_note': '按固定套件顺序，非全资金业务流程',
        'checks_title': '页面与交互观察', 'checks_note': '辅助证据，不追加通过用例数',
        'image_note': '截图展示页面状态。游戏启动与真实投注分别记录；业务金额结论需订单与账变核对。',
    }
    loaded = {}
    omitted = 0
    for filename, label in SOURCES.items():
        path = directory / filename
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            omitted += 1
            continue
        if not isinstance(data, dict) or not fresh(path, window, data):
            omitted += 1
            continue
        loaded[filename] = data
        # Raw sidecars can contain response bodies. Publish only allowlisted summaries.
    for index, item in enumerate(items, 1):
        purpose = PURPOSES.get(Path(item['target']).name, '核验该用例定义的页面与交互断言。')
        item['expected'] = purpose
        item['actual'] = {'PASS': '本轮 Playwright 断言通过', 'FAIL': '本轮断言或执行失败',
                          'NOT_RUN': '本轮未收集', 'SKIPPED': '本轮跳过'}.get(item['status'], item['actual'])
        evidence['timeline'].append({'step': str(index), 'title': item['name'], 'status': item['status'],
                                     'detail': purpose, 'source': f"{item['id']} · {item['duration'] or '无耗时记录'}"})
    surfaces = loaded.get('client-main-flow-ui.json', {}).get('surfaces', [])
    labels = {'home': '首页', 'game': '游戏大厅', 'rewards': 'Rewards 页面', 'filcoin': 'Filcoin 页面', 'my': '个人中心'}
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        evidence['checks'].append({'name': labels.get(surface.get('id'), '导航页面'), 'status': '已采集',
                                   'detail': '页面状态与网络事件已记录；可访问性仅代表 UI 观察，不代表该模块全部业务已回归。'})
    game = loaded.get('client-game-bet-smoke.json', {})
    deposit = loaded.get('client-deposit-contract.json', {})
    network = [event for data in loaded.values() for event in data.get('network', []) if isinstance(event, dict)]
    # The same request may be captured by multiple listeners; deduplicate event identities.
    responses = {(str(e.get('ts')), str(e.get('method')), str(e.get('url')), str(e.get('status'))): e
                 for e in network if e.get('kind') == 'response'}
    http_errors = sum(isinstance(e.get('status'), int) and e['status'] >= 400 for e in responses.values())
    evidence['highlights'] = [
        {'label': '页面观察', 'value': f'{len(surfaces)} 个', 'detail': '主导航扫描实际产物'},
        {'label': '网络响应', 'value': f'{len(responses)} 条', 'detail': f'其中 HTTP ≥ 400：{http_errors} 条；不等于业务断言数'},
        {'label': '真实投注', 'value': f"{game.get('completedSpinCount', 0)} 次" if game else '未采集',
         'detail': '本轮执行投注开关已开启' if game.get('executeBet') else '本轮未开启真实投注' if game else '没有可关联的本轮游戏证据'},
        {'label': '充值请求', 'value': '已捕获' if deposit.get('depositRequest') else '未提交' if deposit else '未采集',
         'detail': '捕获请求不等于到账成功' if deposit.get('depositRequest') else '仅页面契约验证' if deposit else '没有可关联的本轮充值证据'},
    ]
    if deposit:
        evidence['checks'].append({'name': '充值金额与渠道控件', 'status': '已采集',
                                   'detail': f"记录 {len(deposit.get('beforeControls', []))} 个控件；页面完整断言见对应充值用例。"})
    evidence['checks'].append({'name': '证据关联范围', 'status': '说明',
                               'detail': f'仅收录本次 Playwright 时间窗口内的证据；{omitted} 份缺失、损坏或过期的辅助结果未纳入。HTTP 失败不自动判定为用例失败，反例也可能产生拒绝响应。'})
    candidates = []
    if deposit:
        candidates.append((directory / 'screenshots/deposit-contract-before.png', '充值页面', '金额与支付方式控件'))
    for key, title in [('before', '游戏启动页面'), ('after', '游戏检查结束页面')]:
        value = game.get('screenshots', {}).get(key)
        if value:
            path = Path(value)
            if not path.is_absolute():
                path = directory / 'screenshots' / path.name
            candidates.append((path, title, '本轮未执行真实投注' if not game.get('executeBet') else f"本轮记录 {game.get('completedSpinCount', 0)} 次 Spin；以结构化结果核对"))
    for path, title, caption in candidates:
        path = path.resolve()
        if path.is_relative_to(directory / 'screenshots') and fresh(path, window):
            evidence['images'].append({'title': title, 'src': relative_link(path, output), 'caption': caption})
    if not evidence['images']:
        evidence['checks'].append({'name': '页面截图', 'status': '未采集', 'detail': '本轮没有可关联的截图，不使用历史图片补齐。'})
    # Export only the exact allowlisted model; never include auth/session, raw bodies, query strings or DOM text.
    artifact = output.with_name('p0-ui-evidence.json')
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    evidence['artifacts'].append({'label': 'UI 证据摘要 JSON', 'href': relative_link(artifact, output),
                                  'detail': '本轮白名单字段摘要，不含 token、响应正文或页面原文'})
    return evidence


def append_markdown(output, evidence):
    def text(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = ['\n## 本次执行摘要\n']
    for item in evidence['highlights']:
        lines.append(f"- {text(item['label'])}：{text(item['value'])}。{text(item['detail'])}")
    lines += ['\n## UI 用例执行轨迹\n', '| 用例 | 结果 | 过程 | 耗时 |', '|---|---|---|---|']
    for item in evidence['timeline']:
        lines.append('| ' + ' | '.join(text(item[k]) for k in ('title', 'status', 'detail', 'source')) + ' |')
    lines += ['\n## 页面与交互观察\n']
    for item in evidence['checks']:
        lines.append(f"- {text(item['name'])}（{text(item['status'])}）：{text(item['detail'])}")
    lines += ['\n## 页面证据\n', evidence['image_note']]
    for item in evidence['images']:
        lines.append(f"\n![{item['title']}]({item['src']})\n\n{item['caption']}")
    for item in evidence['artifacts']:
        lines.append(f"\n[{item['label']}]({item['href']})")
    with output.open('a', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
