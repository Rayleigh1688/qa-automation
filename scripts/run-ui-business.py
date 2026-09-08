#!/usr/bin/env python3
"""Controlled FAT UI business chain, separate from the default page suite."""
from qa_core.terminal import print_result, print_path

import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
from ui_fund_flow import FundApi, validate_deposit_resume, require_paid_bets
from ui_business_report import render_report, collect_assertions
from ui_business_artifacts import prepare_business_artifacts
from ui_process import run_ui_process


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    target.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env', required=True)
    parser.add_argument('--resume-reconcile', default='', help='Read-only resume of this-run final reconciliation; never replays UI writes')
    parser.add_argument('--resume-run', default='', help='Continue a this-run deposit lookup failure without creating another order')
    parser.add_argument('--execute', action='store_true', help='Create UI orders, approve deposit and perform real UI bets')
    parser.add_argument('--kyc-run-id', default='', help='Explicitly link the just-completed KYC UI run; otherwise run KYC UI first')
    parser.add_argument('--bet-spins', type=int, default=3, choices=range(3, 6), help='Exact paid bets before explicit admin turnover clear (3–5)')
    parser.add_argument('--clear-remaining-turnover', action='store_true', help='Explicit admin clear after verified UI bets')
    parser.add_argument('--allow-existing-turnover', action='store_true', help='Include designated fund account existing turnover in the explicit clear')
    parser.add_argument('--new-kyc-account', action='store_true', help='Register an isolated fresh test account, then submit KYC through UI')
    parser.add_argument('--headed', action='store_true')
    parser.add_argument('--deposit-amount', type=int, default=1200)
    parser.add_argument('--withdraw-amount', type=int, default=1000)
    args = parser.parse_args()
    state = {'runId': str(uuid.uuid4()), 'scope': 'FAT', 'status': 'BLOCKED', 'stage': 'preflight', 'completed': [], 'startedAt': time.time(), 'writesRequested': args.execute, 'paidBetTarget': args.bet_spins, 'depositAmount': args.deposit_amount, 'withdrawAmount': args.withdraw_amount, 'adminClearRequested': args.clear_remaining_turnover, 'existingTurnoverAllowed': args.allow_existing_turnover}
    resume_mode = None
    prior = None
    prior_records = []
    api = None
    code = 1
    try:
        prepare_business_artifacts(resume=bool(args.resume_run or args.resume_reconcile), kyc_run_id=args.kyc_run_id)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print_result(f'UI artifact preparation blocked: {error}', 'BLOCKED')
        return 1
    Path('ui/results').mkdir(parents=True, exist_ok=True)
    with open('ui/results/ui-business-run.log', 'w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            if args.resume_reconcile and (args.execute or args.resume_run or args.new_kyc_account):
                raise RuntimeError('Reconciliation continuation is read-only and cannot include write/resume flags')
            if args.execute and not args.clear_remaining_turnover:
                raise RuntimeError('Fixed paid-bet flow requires explicit --clear-remaining-turnover')
            if args.resume_run and args.new_kyc_account:
                raise RuntimeError('Resume cannot register another KYC account')
            if args.new_kyc_account and args.kyc_run_id:
                raise RuntimeError('Fresh KYC cannot use prior evidence')
            if args.allow_existing_turnover and not args.clear_remaining_turnover:
                raise RuntimeError('Existing turnover requires explicit admin clear mode')
            if args.execute:
                subprocess.run(['node', '--input-type=module', '-e', "import {visualDependencies} from './ui/framework/game-round-state.mjs'; await visualDependencies();"], check=True, stdout=log, stderr=log)
            if args.resume_run:
                if not args.execute: raise RuntimeError('Resume requires --execute')
                prior = read('ui/results/ui-business-run-status.json')
                deposit = read('ui/results/client-deposit-contract.json')
                prior_records = read('api/results/ui-fund-support.json')
                resume_mode = validate_deposit_resume(prior, deposit, prior_records, args.resume_run, time.time())
                state['runId'] = prior['runId']
                state['startedAt'] = prior['startedAt']
                state['resumedAt'] = time.time()
                args.kyc_run_id = prior['kycRunId']
            os.environ['ENV_FILE'] = args.env
            api = FundApi(args.env)
            for key, host in [('CLIENT_BASE_URL', 'client-fat.filbet2025.com'), ('API_URL', 'client-fat.filbet2025.com'), ('ADMIN_URL', 'admin-fat.filbet2025.com')]:
                url = urlparse(os.environ.get(key, ''))
                if url.scheme != 'https' or url.netloc != host:
                    raise RuntimeError('All services must use the designated FAT environment')
            if not (0 < args.deposit_amount <= 1200 and 0 < args.withdraw_amount <= 1000):
                raise RuntimeError('Controlled amounts exceed this runner safety bounds')
            for key in ['CLIENT_WALLET_PASSWORD', 'ADMIN_APPROVAL_TOTP_SECRET']:
                if not os.environ.get(key): raise RuntimeError(f'{key} is required')
            normalize = lambda value: ''.join(c for c in value if c.isdigit()).removeprefix('63').removeprefix('0')
            lanes = [normalize(os.environ.get(key, '')) for key in ['WRITE_CLIENT_PHONE', 'KYC_CLIENT_PHONE', 'PRE_KYC_CLIENT_PHONE']]
            if not all(lanes) or len(set(lanes)) != 3: raise RuntimeError('KYC, fund and BASIC lanes must be distinct')
            env = {**os.environ, 'ENV_FILE_PRECEDENCE': 'shell', 'CLIENT_REUSE_P0_AUTH': 'true', 'CLIENT_AUTH_LANE': 'fund_flow_account', 'CLIENT_AUTH_ARTIFACT_PREFIX': 'ui-fund-auth', 'CLIENT_P0_STORAGE_STATE_PATH': 'ui/results/ui-fund-storage-state.json', 'CLIENT_AUTH_MODE': 'password', 'CLIENT_PHONE': os.environ['WRITE_CLIENT_PHONE'], 'CLIENT_PASSWORD': os.environ['WRITE_CLIENT_PASSWORD'], 'PRESERVE_UI_RESULTS': 'true', 'EXECUTE_BET': 'false', 'EXECUTE_DEPOSIT_CONTRACT': 'false', 'EXECUTE_WITHDRAW_UI': 'false'}
            env['UI_BUSINESS_RUN_ID'] = state['runId']
            if args.headed: env['PLAYWRIGHT_HEADLESS'] = 'false'
            def run(command, extra=None):
                run_ui_process(command, env={**env, **(extra or {})}, stdout=log, stderr=log, check=True)
            def ui(spec, extra, output):
                if spec == 'client-game-bet-smoke':
                    for artifact in ['game-paid-bets.json', 'game-round-state.json']:
                        Path('ui/results', artifact).unlink(missing_ok=True)
                Path(output).unlink(missing_ok=True)
                run(['npx', 'playwright', 'test', f'ui/cases/{spec}.spec.mjs', '--workers=1', '--retries=0'], extra)
                return read(output)
            if args.resume_reconcile:
                prior = read('ui/results/ui-business-run-status.json')
                withdraw = read('ui/results/client-withdraw-contract.json')
                if not (prior.get('runId') == args.resume_reconcile and prior.get('scope') == 'FAT' and prior.get('stage') == 'reconcile' and prior.get('status') == 'BLOCKED'
                        and 'withdraw_ui' in prior.get('completed', []) and 0 <= time.time() - prior.get('startedAt', 0) <= 3600
                        and withdraw.get('legalOrderCreated') is True and withdraw.get('transactionId') == prior.get('withdrawId')):
                    raise RuntimeError('Missing recent this-run UI withdrawal checkpoint')
                prior_records = read('api/results/ui-fund-support.json')
                wallet_before = next(r for r in prior_records if r.get('name') == 'ui_fund_wallet_before')
                transaction_baseline = next(r['data'] for r in prior_records if r.get('name') == 'ui_fund_transactions')
                api.fresh_client()
                api.uid = str(api.query('/member/kyc/detail', 'fund_kyc')['data']['uid'])
                if api.uid != str(wallet_before['data']['uid']):
                    raise RuntimeError('Reconciliation account differs from original fund account')
                api.records = prior_records + api.records
                state = {**prior, 'resumedReconciliationAt': time.time(), 'previousError': prior.get('error')}
                state.pop('error', None)
                state['reconciliation'] = api.reconcile_ui_withdraw(prior['withdrawId'], int(withdraw['legalResponse']['amount']))
                state['transactions'] = api.reconcile_transactions(transaction_baseline, wallet_before, state['startedAt'])
                state['completed'].append('reconcile')
                state['stage'] = 'complete'
                state['status'] = 'PASS'
                code = 0
                return code
            wallet_before = api.preflight(args.withdraw_amount, allow_turnover=resume_mode == 'credited' or args.allow_existing_turnover)
            transaction_baseline = api.transactions()
            if prior:
                previous_wallet = next(r for r in prior_records if r.get('name') == 'ui_fund_wallet_before')
                previous_transactions = next(r['data'] for r in prior_records if r.get('name') == 'ui_fund_transactions')
                checkpoint = next(r for r in prior_records if r.get('name') == 'wallet_after_deposit') if resume_mode == 'credited' else previous_wallet
                if wallet_before['data']['balance'] != checkpoint['data']['balance']:
                    raise RuntimeError('Fund balance changed since checkpoint; continuation blocked')
                if resume_mode == 'lookup' and transaction_baseline['t'] != previous_transactions['t']:
                    raise RuntimeError('Fund transactions changed since failed lookup')
                if prior.get('stage') == 'bet_ui':
                    baseline_record = next(r for r in reversed(prior_records) if r.get('name') == 'ui_fund_bets')
                    from ui_fund_flow import bet_rows
                    if api.bets() != bet_rows(baseline_record['data']):
                        raise RuntimeError('Bet records changed after checkpoint; do not replay UI bets')
                    if prior.get('paidBetTarget') != args.bet_spins or prior.get('adminClearRequested') is not True:
                        raise RuntimeError('Resume cannot change paid bet target or clear mode')
                wallet_before = previous_wallet
                transaction_baseline = previous_transactions
                api.records = prior_records + api.records
            state['completed'].append('fund_preflight')
            if not args.execute:
                state['status'] = 'READY'
                code = 0
                return code
            state['stage'] = 'kyc_ui'
            if args.new_kyc_account:
                env.update(api.prepare_kyc_account())
                state['kycAccountPrepared'] = True
            if not args.kyc_run_id:
                run(['node', 'scripts/run-ui-kyc.mjs', '--approve'])
            kyc = read('ui/results/client-kyc-submit.json')
            kyc_run = read('ui/results/kyc-ui-run-status.json')
            expected_run = args.kyc_run_id or kyc_run.get('runId')
            from datetime import datetime, timezone
            age = datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(kyc_run['startedAt'].replace('Z', '+00:00')).timestamp()
            if not (kyc.get('runId') == expected_run == kyc_run.get('runId') and kyc.get('status') == 'APPROVED' and kyc_run.get('status') == 'APPROVED' and kyc.get('uiSubmitted') is True and kyc.get('adminApproved') is True and 0 <= age <= 3600):
                raise RuntimeError('Missing current approved KYC UI evidence')
            state['kycRunId'] = expected_run
            state['completed'].append('kyc_ui')
            state['stage'] = 'deposit_ui'
            deposit = read('ui/results/client-deposit-contract.json') if prior else ui('client-deposit-contract', {'EXECUTE_DEPOSIT_CONTRACT': 'true', 'CLIENT_DEPOSIT_AMOUNT': str(args.deposit_amount)}, 'ui/results/client-deposit-contract.json')
            order = deposit.get('depositResponse', {})
            if order.get('businessStatus') is not True or not order.get('orderId'): raise RuntimeError('Missing UI deposit order')
            if int(deposit.get('depositRequest', {}).get('amount', 0)) != args.deposit_amount: raise RuntimeError('Continuation deposit amount mismatch')
            state['depositId'] = order['orderId']
            state['completed'].append('deposit_ui')
            state['stage'] = 'deposit_credit'
            wallet_after_deposit = next(r for r in prior_records if r.get('name') == 'wallet_after_deposit') if resume_mode == 'credited' else api.approve_ui_deposit(order['orderId'], args.deposit_amount, wallet_before)
            state['completed'].append('deposit_credit')
            state['stage'] = 'bet_baseline'
            api.fresh_client()
            bet_baseline = api.bets()
            state['turnover'] = {}
            def persist_turnover():
                write('ui/results/ui-business-run-status.json', state)
            turnover_before_bets = api.wait_deposit_turnover(state['depositId'], args.deposit_amount, state['turnover'], persist_turnover)
            state['stage'] = 'bet_ui'
            bet = ui('client-game-bet-smoke', {'EXECUTE_BET': 'true', 'CLIENT_GAME_REQUIRE_PAID_BETS': 'true', 'CLIENT_GAME_SPIN_COUNT': str(args.bet_spins), 'CLIENT_GAME_BET_AMOUNT': '100', 'CLIENT_GAME_ID': 'lucky_penny'}, 'ui/results/client-game-bet-smoke.json')
            if not (bet.get('controlledPaidBets') is True and bet.get('paidEvidence', {}).get('accepted') is True and bet['paidEvidence'].get('paidBetRecords') == args.bet_spins):
                raise RuntimeError('Exact paid UI bet evidence missing')
            state['completed'].append('bet_ui')
            state['stage'] = 'bet_reconcile'
            state['betReconciliation'] = api.reconcile_bets(bet_baseline, wallet_after_deposit, int(bet['completedSpinCount']), 100)
            require_paid_bets(state['betReconciliation'], args.bet_spins, 100)
            state['completed'].append('bet_reconcile')
            state['stage'] = 'turnover_clear'
            api.clear_after_ui_bets(state['betReconciliation'], args.bet_spins, 100, turnover_before_bets, state['turnover'], persist_turnover)
            state['completed'].append('turnover_clear')
            state['stage'] = 'withdraw_preflight'
            api.before_withdraw(args.withdraw_amount)
            state['stage'] = 'withdraw_ui'
            withdraw = ui('client-withdraw-contract', {'EXECUTE_WITHDRAW_UI': 'true', 'CLIENT_WITHDRAW_CHANNEL': 'Maya', 'CLIENT_WITHDRAW_AMOUNT': str(args.withdraw_amount)}, 'ui/results/client-withdraw-contract.json')
            order = withdraw.get('legalResponse', {})
            if not withdraw.get('legalOrderCreated') or order.get('businessStatus') is not True or order.get('orderId') != withdraw.get('transactionId'): raise RuntimeError('Missing this-run UI withdrawal order')
            state['withdrawId'] = order['orderId']
            state['completed'].append('withdraw_ui')
            state['stage'] = 'reconcile'
            state['reconciliation'] = api.reconcile_ui_withdraw(order['orderId'], args.withdraw_amount)
            state['transactions'] = api.reconcile_transactions(transaction_baseline, wallet_before, state['startedAt'])
            state['completed'].append('reconcile')
            state['stage'] = 'complete'
            state['status'] = 'PASS'
            code = 0
        except (Exception, SystemExit, KeyboardInterrupt) as error:
            if state['stage'] == 'bet_ui':
                plan_path = Path('ui/results/game-paid-bets.json')
                if plan_path.exists():
                    state['betCheckpoint'] = read(plan_path)
                try:
                    game = read('ui/results/client-game-bet-smoke.json')
                    state['partialBetReconciliation'] = api.reconcile_bets(bet_baseline, wallet_after_deposit, int(game['completedSpinCount']), int(game['requestedBetAmount']))
                    state['remainingTurnover'] = str(api.turnover())
                except (Exception, SystemExit) as diagnostic_error:
                    state['diagnosticError'] = type(diagnostic_error).__name__
            state['error'] = f'{type(error).__name__}: {error}'
        finally:
            state['finishedAt'] = time.time()
            state['exitCode'] = code
            if api:
                write('api/results/ui-fund-support.json', api.c.redact_payload(api.records))
                state['supportSha256'] = hashlib.sha256(Path('api/results/ui-fund-support.json').read_bytes()).hexdigest()
            state['assertions'] = collect_assertions(state)
            write('ui/results/ui-business-run-status.json', state)
            render_report(state)
            Path('ui/results/ui-fund-storage-state.json').unlink(missing_ok=True)
            print_result(f"UI business {state['status']} at {state['stage']}", state['status'], file=sys.__stdout__)
            print_path(f"HTML report: {Path('ui/reports/ui-business-report.html').resolve().as_uri()}", file=sys.__stdout__)
            print_path(f"Run log: {Path('ui/results/ui-business-run.log').resolve()}", file=sys.__stdout__)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
