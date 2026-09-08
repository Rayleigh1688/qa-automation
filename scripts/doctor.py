#!/usr/bin/env python3
"""Local readiness checks. --network explicitly opts into unauthenticated HTTPS HEAD probes."""
from qa_core.terminal import print_result, print_path

import argparse
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.error import HTTPError
from qa_core.environment import load_environment
from qa_core.local_lock import local_run_lock, LocalRunBusy

ROOT = Path(__file__).resolve().parents[1]


def runner(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def placeholder(value):
    return '<' in value or 'example.com' in value


def phone(value):
    value = ''.join(c for c in value if c.isdigit())
    if value.startswith('63'):
        value = value[2:]
    return value.lstrip('0')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def probe(url):
    # No cookies, auth, response body, redirects, login or business API calls.
    try:
        with build_opener(NoRedirect).open(Request(url, method='HEAD'), timeout=10) as response:
            return response.status < 400
    except HTTPError as error:
        return 300 <= error.code < 400 or error.code in (401, 403, 405)
    except Exception:
        return False


def check(args):
    failures = []
    def require(ok, message):
        if not ok:
            failures.append(message)
    require(sys.version_info >= (3, 10), 'Python 版本过低：安装 Python 3.10 或更高版本。')
    try:
        env = load_environment(args.env)
    except (SystemExit, OSError):
        return ['配置不可读：复制对应环境模板到 .env 文件；检查 --env 与 QA_ENV_LOCAL。']
    # Report names only, never values, file contents, exceptions or credentials.
    for file in [args.env, os.environ.get('QA_ENV_LOCAL')]:
        if not file:
            continue
        path = Path(file)
        require(not path.stat().st_mode & 0o077, '配置权限过宽：对环境文件及个人文件执行 chmod 600。')
        tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', '--', str(path.resolve())], capture_output=True).returncode == 0
        require(not tracked, '凭据配置已受版本控制：改用被 Git 忽略的 .env 文件，勿将真实凭据填入模板。')
    env = {key: '' if placeholder(value) else value for key, value in env.items()}
    scope = args.scope or ('UAT' if '.uat' in Path(args.env).name.lower() else 'FAT')
    for name in ('API_URL', 'ADMIN_URL', 'CLIENT_BASE_URL'):
        try:
            parsed = urlparse(env.get(name, ''))
            valid = (parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username
                     and not parsed.password and not parsed.query and not parsed.fragment)
        except ValueError:
            valid = False
        require(valid, f'{name}：填写本环境 HTTPS 地址，不能含用户名、密码、查询参数或占位符。')
    for name in ['run-api-tests', *(['run-ui-p0-tests'] if args.target != 'api' else [])]:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                runner(name).preflight(SimpleNamespace(scope=scope, safe_only=True), env)
        except SystemExit as error:
            # Existing safe preflights only emit static variable/dependency names.
            failures.append(str(error) + '\n修复：按环境模板补齐所列变量；依赖缺失运行 npm ci。')
        except Exception:
            failures.append(f'{name} 前置检查异常：核对 URL 格式并运行 npm run check。')
    if scope == 'UAT':
        require(env.get('CLIENT_AUTH_MODE') == 'otp' and env.get('CLIENT_OTP_SOURCE') == 'admin_sms'
                and env.get('REGISTER_OTP_SOURCE') == 'admin_sms', 'UAT：CLIENT_AUTH_MODE=otp，CLIENT_OTP_SOURCE/REGISTER_OTP_SOURCE=admin_sms。')
        require(bool(env.get('ADMIN_LOGIN_TOTP_SECRET') or env.get('ADMIN_APPROVAL_TOTP_SECRET')), 'UAT：配置动态后台登录 TOTP seed。')
        require(not env.get('ADMIN_GOOGLE_CODE'), 'UAT：清空 ADMIN_GOOGLE_CODE，使用动态 TOTP。')
    lanes = {key: phone(env.get(key, '')) for key in ('WRITE_CLIENT_PHONE', 'PRE_KYC_CLIENT_PHONE', 'KYC_CLIENT_PHONE', 'REGISTER_PHONE')}
    for key in ('KYC_CLIENT_PHONE', 'REGISTER_PHONE'):
        require(not lanes[key] or lanes[key] not in (lanes['WRITE_CLIENT_PHONE'], lanes['PRE_KYC_CLIENT_PHONE']), f'{key}：必须使用本轮独立新号，不能复用资金号或 BASIC 号。')
    require(not lanes['WRITE_CLIENT_PHONE'] or lanes['WRITE_CLIENT_PHONE'] != lanes['PRE_KYC_CLIENT_PHONE'], 'WRITE_CLIENT_PHONE 与 PRE_KYC_CLIENT_PHONE 必须分离。')
    for alias in ('BET_CLIENT_PHONE', 'WITHDRAW_CLIENT_PHONE'):
        require(not lanes['WRITE_CLIENT_PHONE'] or phone(env.get(alias, '')) == lanes['WRITE_CLIENT_PHONE'], f'{alias} 必须填写与 WRITE_CLIENT_PHONE 相同的执行者资金号。')
        password = alias.replace('PHONE', 'PASSWORD')
        require(not env.get(password) or env.get(password) == env.get('WRITE_CLIENT_PASSWORD'), f'{password} 必须与 WRITE_CLIENT_PASSWORD 一致。')
    if args.target != 'api':
        if shutil.which('node'):
            result = subprocess.run(['node', '--input-type=module', '-e',
                "import fs from 'node:fs'; import {chromium} from 'playwright'; process.exit(fs.existsSync(chromium.executablePath()) ? 0 : 1);"], capture_output=True)
            require(result.returncode == 0, 'Playwright Chromium 缺失：运行 npm ci 和 npx playwright install chromium。')
        else:
            require(False, 'Node.js 缺失：安装满足 Playwright 要求的 Node.js/npm。')
    if args.target == 'business':
        require(scope == 'FAT', '受控 UI business 目前仅支持 FAT；UAT 使用 API/默认 UI 检查。')
        for key in ('QA_OPERATOR', 'WRITE_CLIENT_PHONE', 'WRITE_CLIENT_PASSWORD', 'PRE_KYC_CLIENT_PHONE', 'REGISTER_PASSWORD', 'CLIENT_WALLET_PASSWORD', 'ADMIN_APPROVAL_TOTP_SECRET'):
            require(bool(env.get(key)), f'{key}：在个人配置中补齐；资金号须由团队分配给执行者。')
        require(Path(env['KYC_IMAGE']).is_file() if env.get('KYC_IMAGE') else False, 'KYC_IMAGE：配置本地测试素材文件，勿提交证件或个人资料。')
        for executable in ('magick', 'tesseract'):
            require(bool(shutil.which(executable)), f'{executable} 缺失：安装 ImageMagick 7 / Tesseract。')
        if shutil.which('tesseract'):
            languages = subprocess.run(['tesseract', '--list-langs'], capture_output=True, text=True)
            require('eng' in languages.stdout.split(), 'Tesseract 缺少 eng：安装英文语言数据。')
    try:
        with local_run_lock(inherit=False):
            pass
    except (LocalRunBusy, OSError):
        require(False, '本机锁不可用：等待当前 QA 任务退出，或检查临时目录权限；不要删除运行中的锁。')
    if args.network and not failures:
        with local_run_lock(inherit=False):
            for name in ('API_URL', 'ADMIN_URL', 'CLIENT_BASE_URL'):
                require(probe(env[name]), f'{name} HTTPS 探测失败：检查 VPN、DNS、证书和服务；doctor 不输出响应正文。')
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env', default=os.environ.get('ENV_FILE', '.env.fat'))
    parser.add_argument('--scope', choices=['FAT', 'UAT'])
    parser.add_argument('--target', choices=['api', 'ui', 'business'], default='ui')
    parser.add_argument('--network', action='store_true', help='Explicit unauthenticated HTTPS HEAD only; no login or funds')
    args = parser.parse_args()
    os.chdir(ROOT)
    try:
        failures = check(args)
    except (OSError, ValueError, LocalRunBusy):
        failures = ['本地配置或锁检查失败：检查文件权限、URL 格式和运行中任务；未输出原始异常。']
    for message in failures:
        print_result('FAIL: ' + message, 'FAIL')
    print_result('doctor ' + ('FAIL' if failures else 'PASS') + (' · 显式 HTTPS 探测' if args.network and not failures else ' · 本地检查'), 'FAIL' if failures else 'PASS')
    print('说明：本地检查不证明账号状态、分配唯一性或业务通过；KYC 每轮新号，BASIC 永久未认证，资金号按执行者分配。')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
