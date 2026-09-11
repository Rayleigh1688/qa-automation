"""Compact requirement-level review; full evidence remains in preview.json."""
from .pipeline import safe_text


def cell(value):
    return ' '.join(safe_text(value).split()).replace('|', '／')


def notice_status(candidate):
    actions = {message.get('action', candidate.get('ai_action'))
               for message in candidate.get('source_messages', [])} or {candidate.get('ai_action')}
    if 'READY' in actions:
        return '提测/部署通知（另有备注）' if actions - {'READY'} else '提测/部署通知'
    return '待核实（撤回备注）' if 'WITHDRAWN' in actions else '待核实（非明确提测）'


def render_preview(summary, state):
    rows = sorted(summary['candidates'], key=lambda row: (int(row['story'].split('-')[1]), row['environment'], row['build'], row['id']))
    pending = summary.get('pending_analysis', 0)
    failed = summary.get('analysis', {}).get('status') == 'FAILED'
    groups = {}
    for row in rows:
        groups.setdefault(row['story'], []).append(row)
    count = len(groups)
    label = '上次扫描' if summary.get('preview_refreshed_at') else '扫描'
    lines = [f'{label}{"未完成" if pending or failed else "完成"}：收到 {summary.get("updates", 0)} 条更新，待确认 {count} 个需求。']
    if summary.get('preview_refreshed_at'):
        lines.append('本地查看，未获取新消息；来源扫描时间：' + cell(summary.get('scan', {}).get('finished_at', '未记录')))
    if pending or failed:
        lines.append(f'AI分析未完成，{pending} 条消息待分析；以下为已有候选，暂不能执行。')
        if summary.get('analysis', {}).get('detail'):
            lines.append('失败原因：' + cell(summary['analysis']['detail']))
    if rows:
        lines += ['', '| 需求工单 | 需求名称 | 环境 | 配置范围 | 提测判断 |', '| --- | --- | --- | --- | --- |']
        for story, batches in groups.items():
            environments, statuses = [], []
            for row in batches:
                default = any('local default' in m.get('environment_source', '') for m in row.get('source_messages', []))
                default = default or 'local default' in row.get('environment_source', '')
                environment = row['environment'] + ('（默认，待核实）' if default else '')
                if environment not in environments:
                    environments.append(environment)
                status = notice_status(row)
                if status not in statuses:
                    statuses.append(status)
            scope = '、'.join({'api': 'API', 'ui': '手工UI'}.get(s, s) for s in sorted({s for row in batches for s in row['scopes']})) or '待核实（范围不匹配）'
            status = '；'.join(statuses) + (f'；{len(batches)} 批次需分别选范围' if len(batches) > 1 else '')
            lines.append('| ' + ' | '.join(cell(v) for v in [story, batches[0].get('requirement_title', story),
                '、'.join(environments), scope, status]) + ' |')
    else:
        lines.append('暂无已归属到现有需求目录的待确认任务。')
    if summary.get('unmatched'):
        lines.append(f'另有 {len(summary["unmatched"])} 项尚未归属到现有需求，保留在详细清单中。')
    if summary.get('limit_reached'):
        lines.append('达到扫描页数上限，请再次扫描接收剩余消息。')
    lines += ['', '未执行测试。配置范围不等于本次提测范围或完整测试已就绪。',
              '详细清单（来源、版本、负责人及用例缺口）：' + str(state / 'preview.json')]
    if rows and not pending and not failed:
        lines += ['确认需求及范围后，使用所选需求编号执行：',
                  'npm run qa:telegram -- run --requirements <需求编号,需求编号> --revision ' + summary['revision'],
                  '同一需求有多个环境、版本或范围时，用详细清单的 --candidates 选择具体批次。']
    elif pending or failed:
        lines.append('消息已保存在本机，修复后重新扫描即可，无需重发。')
    return '\n'.join(lines) + '\n'
