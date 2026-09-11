#!/usr/bin/env python3
"""Scan submissions, review locally, and deliver one summary after approved Jira creation."""
import argparse
import json
import os
from pathlib import Path
from qa_core.local_lock import local_run_lock
from qa_core.environment import read_values
from qa_delivery.state import Store, validate_config, digest
from qa_delivery.connectors import Telegram, Jira, RemoteError
from qa_delivery.pipeline import validate_triage, redact_value, render_report, import_manual_review
from qa_delivery.batch import run_batch, execute_batch, submit_approved, refresh_preview
from qa_delivery.intake import confirm, select_candidates
from qa_delivery.preview_report import render_preview

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', nargs='?', default='scan', choices=['scan', 'preview', 'run', 'import-manual', 'approve', 'submit', 'identify', 'check', 'verify', 'status', 'revise', 'reconcile-jira', 'retry-jira'])
    parser.add_argument('--config', default='config/telegram/local.json')
    parser.add_argument('--state', default='reports/telegram')
    parser.add_argument('--max-pages', type=int, default=20)
    parser.add_argument('--credentials', default='.env.telegram')
    parser.add_argument('--since', help='start time with timezone, e.g. 2026-09-10T15:00:00+08:00')
    parser.add_argument('--job')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--candidates', help='comma-separated preview candidate IDs')
    selection.add_argument('--requirements', help='comma-separated requirement IDs from the preview')
    parser.add_argument('--revision', help='exact preview revision being approved')
    parser.add_argument('--review-file')
    parser.add_argument('--manual', type=Path, help='Filled manual.csv from this job team-packet')
    parser.add_argument('--bugs', help='explicit PRODUCT candidate IDs approved from the local report')
    args = parser.parse_args()
    from qa_delivery.scan_history import parse_since
    since = parse_since(args.since)
    config = validate_config(json.loads((ROOT / args.config).read_text(encoding='utf-8')))
    credentials = ROOT / args.credentials
    if credentials.is_file():
        os.environ.update(read_values(credentials))
    if args.mode == 'check':
        print('Configuration structure OK (offline); no Telegram, Jira, Codex or business requests sent.')
        for name in ('TELEGRAM_BOT_TOKEN', config['jira']['email_env'], config['jira']['token_env']):
            print(name + ': ' + ('set' if os.environ.get(name) else 'missing'))
        print('Configured Stories:', ', '.join(config['stories']) or '(none)')
        print('Submission permissions: all members; scan requires local confirmation before tests')
        print('Tester numeric IDs:', sum(bool(t.get('telegram_id')) for t in config.get('testers', {}).values()))
        for key, env in config['environments'].items():
            print(key, 'version probes:', len(env.get('version_probes', [])))
        return 0
    state = (ROOT / args.state).resolve()
    if args.mode == 'preview':
        with local_run_lock(namespace='qa-telegram-batch', inherit=False):
            summary = refresh_preview(config, state)
        print(render_preview(summary, state), end='')
        return 0
    if args.mode == 'verify':
        telegram = Telegram(os.environ.get('TELEGRAM_BOT_TOKEN', ''))
        me = telegram.verify(config)
        for key in ('submission_chat_id', 'testing_chat_id'):
            telegram.call('getChat', {'chat_id': config[key]})
            print(key + ': accessible')
            membership = telegram.call('getChatMember', {'chat_id': config[key], 'user_id': me['id']})
            reads_text = bool(me.get('can_read_all_group_messages')) or membership.get('status') in ('administrator', 'creator')
            print(key + ' ordinary messages: ' + ('enabled' if reads_text else 'privacy mode requires configuration'))
        jira = Jira(config['jira'])
        identity = jira.call('GET', 'myself')
        print('Jira authentication: OK; account matches configured email:',
              identity.get('emailAddress', '').lower() == os.environ[config['jira']['email_env']].lower())
        if config.get('pilot_story'):
            print('Pilot Story:', jira.resolve_story(config['pilot_story']))
        return 0
    store = Store(state / 'queue.sqlite3')
    try:
        if args.mode == 'import-manual':
            if not args.manual:
                raise ValueError('manual import requires --manual')
            with local_run_lock(namespace='qa-telegram-batch', inherit=False):
                revision = import_manual_review(store,config,state,args.job,args.revision,args.manual)
            print('人工结果已合并，BUG列表需按新版本确认：', revision)
            print('未重跑API/UI、未创建Jira或发送群消息；AI分类失败时用revise整理。')
            return 0
        if args.mode == 'approve':
            row = store.get(args.job)
            if not row or row['config_hash'] != digest(config):
                raise ValueError('missing job or changed configuration; review again first')
            payload = json.loads(row['payload'])
            owner = config['stories'][payload['story']].get('tester_id')
            with store.db:
                store._approve([args.job, args.revision, args.bugs or ''], owner, config)
            if store.get(args.job)['status'] != 'APPROVED':
                raise ValueError('approval rejected; check Story owner, current revision and PRODUCT IDs')
            print('具体 BUG 已在本机确认；未写 Jira、未发送群消息。下一步执行 submit。')
            return 0
        if args.mode == 'identify':
            with local_run_lock(namespace='qa-telegram-batch', inherit=False):
                telegram = Telegram(os.environ.get('TELEGRAM_BOT_TOKEN', ''))
                telegram.verify(config)
                updates = telegram.call('getUpdates', {'offset': store.offset(), 'timeout': 0,
                                                       'limit': 100, 'allowed_updates': ['message']})
                for update in updates:
                    m = update.get('message', {})
                    if m.get('chat', {}).get('id') == config['testing_chat_id'] and m.get('text', '').split('@')[0].strip() == '/whoami':
                        user = m.get('from', {})
                        if not user.get('is_bot') and not m.get('sender_chat'):
                            print({'telegram_id': user.get('id'), 'username': user.get('username'), 'name': user.get('first_name')})
                print('Inspected up to 100 pending updates; cursor unchanged, no messages sent or tests run.')
            return 0
        if args.mode in ('reconcile-jira', 'retry-jira'):
            row = store.get(args.job)
            if not row or row['status'] not in ('SUBMIT_BLOCKED', 'INTERRUPTED') or not row['approved'] or row['config_hash'] != digest(config):
                raise ValueError('requires a previously approved, stopped job with unchanged configuration')
            if args.mode == 'reconcile-jira':
                jira = Jira(config['jira']); p = json.loads(row['payload'])
                for issue in store.db.execute("SELECT * FROM issues WHERE job=? AND state='INTENT'", (args.job,)).fetchall():
                    found = jira.find(p['story'], issue['fingerprint'])
                    if found:
                        with store.db:
                            store.db.execute("UPDATE issues SET state='CREATED',jira_key=? WHERE fingerprint=?", (found['key'], issue['fingerprint']))
                print('Read-only reconciliation finished. No match stays uncertain; no issue was created.')
            else:
                with store.db:
                    if store.db.execute("SELECT 1 FROM issues WHERE job=? AND state='INTENT'", (args.job,)).fetchone():
                        raise ValueError('uncertain create remains; reconcile first, never blindly recreate')
                    store.db.execute("UPDATE jobs SET status='APPROVED' WHERE id=?", (args.job,))
                print('Stored approval requeued; completed issues will not be recreated.')
            return 0
        if args.mode == 'revise':
            store.db.execute('BEGIN IMMEDIATE')
            # Local review edits never approve. Old Telegram confirmations become invalid.
            row = store.get(args.job)
            if not row or row['status'] != 'REVIEW':
                raise ValueError('only an unapproved report may be revised')
            report = json.loads(row['report'])
            revision = redact_value(json.loads(Path(args.review_file).read_text(encoding='utf-8')))
            validate_triage(revision, report['results'])
            report.update(summary=revision['summary'], bugs=revision['bugs'])
            render_report(state / 'runs' / row['id'], json.loads(row['payload']), report)
            store.finish(row['id'], report)
            print('本地 BUG 列表已修订；需要重新确认，未发送群消息。')
            return 0
        if args.mode == 'status':
            for row in store.db.execute('SELECT id,status,revision FROM jobs ORDER BY rowid'):
                print(dict(row))
            return 0
        # One finite process owns ingestion, tests and approved Jira submissions.
        with local_run_lock(namespace='qa-telegram-batch', inherit=False):
            telegram = Telegram(os.environ.get('TELEGRAM_BOT_TOKEN', ''))
            if args.mode == 'scan':
                me = telegram.verify(config)
                membership = telegram.call('getChatMember', {'chat_id': config['submission_chat_id'], 'user_id': me['id']})
                if not me.get('can_read_all_group_messages') and membership.get('status') not in ('administrator', 'creator'):
                    print('机器人隐私模式未关闭，普通提测消息不可见；请在BotFather关闭隐私模式并重新加群，再扫描。')
                    return 1
                print('正在获取消息并调用AI分析，请稍候；本步骤不会执行测试。', flush=True)
                summary = run_batch(store, telegram, config, state, max_pages=args.max_pages, since=since)
                print(render_preview(summary, state), end='')
            elif args.mode == 'run':
                # Verify transport before consuming the local approval.
                telegram.verify(config)
                from qa_delivery.intake import preview
                current = preview(store, config)
                if current['revision'] != args.revision:
                    raise ValueError('预览已变化，请重新扫描确认')
                try:
                    selected = select_candidates(current, requirements=args.requirements, candidates=args.candidates)
                except ValueError as error:
                    print(str(error))
                    return 1
                jira = Jira(config['jira'])
                for candidate in current['candidates']:
                    if candidate['id'] in selected:
                        for issue in candidate['issues']:
                            if jira.resolve_story(issue)['story'] != candidate['story']:
                                raise ValueError('Jira父Story与预览不同，请更新本地设计记录后重新扫描')
                jobs = confirm(store, config, selected, args.revision)
                print(execute_batch(store, telegram, config, state, jobs))
                print('本批API执行结束，UI人工表在runs/<job>/team-packet/manual.csv；回填后用import-manual合并。')
                print('报告仅在本机；确认具体BUG后approve，再submit，整批建单成功后才发群。')
            elif args.mode == 'submit':
                print(submit_approved(store, telegram, config, max_pages=args.max_pages))
    finally:
        store.close()
    return 0



def entrypoint():
    try:
        return main()
    except (OSError, KeyError, ValueError, RemoteError) as error:
        print("Startup/preflight failed:", type(error).__name__, "(details suppressed; check local configuration)")
        return 1
