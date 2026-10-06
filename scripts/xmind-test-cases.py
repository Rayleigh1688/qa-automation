#!/usr/bin/env python3
"""Create/import Xmind case maps and fill recorded results; entirely offline."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from qa_core.case_report import FIELDS, csv_text, load_cases, validate_cases
from qa_core.xmind_archive import MAX_ARCHIVE_BYTES, read_xmind_bytes, write_xmind
from qa_core.xmind_cases import cases_to_sheets, extract_cases, fill_results, template_sheets


def _new_path(path):
    if path.exists() or path.is_symlink():
        raise ValueError('output already exists; choose a new file or directory')


def _cases(path):
    if path.suffix.lower() == '.csv':
        return load_cases(path)
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    validate_cases(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('template', help='Create an editable rightward example map')
    p.add_argument('--title', default='测试用例模板')
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('export', help='Export an existing case catalogue')
    p.add_argument('--cases', type=Path, required=True)
    p.add_argument('--title', default='测试用例')
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('import', help='Import human case definitions into a new review directory')
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('fill-results', help='Copy a map and annotate exact IDs using recorded results')
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--results', type=Path, required=True)
    p.add_argument('--cases', type=Path, help='Frozen case CSV or FIELDS-list JSON; reject changed definitions')
    p.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    _new_path(args.out)
    if args.command != 'import' and args.out.suffix.lower() != '.xmind':
        raise ValueError('output file must have .xmind extension')
    if args.command == 'template':
        sheets = template_sheets(args.title)
        write_xmind(args.out, sheets)
        print('Xmind template created; 2 examples, no tests executed:', args.out)
    elif args.command == 'export':
        cases = _cases(args.cases)
        write_xmind(args.out, cases_to_sheets(cases, args.title))
        print(f'Xmind exported: {len(cases)} case definitions; no tests executed:', args.out)
    else:
        with args.input.open('rb') as stream:
            source = stream.read(MAX_ARCHIVE_BYTES + 1)
        document = read_xmind_bytes(source)
        cases, locations = extract_cases(document)
        if args.command == 'import':
            manifest = {'schema_version': 1, 'mode': 'case-design-import', 'source': str(args.input.resolve()),
                        'source_sha256': hashlib.sha256(source).hexdigest(), 'format': document.format,
                        'case_count': len(cases), 'locations': locations}
            args.out.mkdir(parents=True, exist_ok=False)
            (args.out / 'cases.csv').write_text(csv_text(cases, FIELDS), encoding='utf-8')
            (args.out / 'cases.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            (args.out / 'source.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            (args.out / 'README.md').write_text('# Xmind人工用例\n\n仅导入用例定义，本次没有执行测试。cases.csv/cases.json供核对，source.json记录原文件hash与主题定位。\n\n原导图保持不变，不生成或覆盖plan.json，不直接将自然语言转换成API指令。按docs/xmind-test-cases.md核对预期、执行入口与数据授权后再执行；团队manual.csv仍由已确认计划冻结生成。\n', encoding='utf-8')
            print(f'Xmind imported: {len(cases)} cases; no tests executed:', args.out / 'cases.csv')
        else:
            report = json.loads(args.results.read_text(encoding='utf-8-sig'))
            frozen = _cases(args.cases) if args.cases else None
            sheets = fill_results(document, report, cases=frozen)
            write_xmind(args.out, sheets, document=document)
            print(f'Xmind results filled: {len(cases)} cases; no tests executed; original preserved:', args.out)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError, OSError) as error:
        # Field values and paths may contain private data; keep terminal errors structural.
        if isinstance(error, ValueError) and str(error).startswith(('output ', 'duplicate Xmind', 'Xmind case', 'Xmind result', 'result field', 'result JSON', 'malformed Xmind')):
            print('Xmind validation failed:', str(error), file=sys.stderr)
        else:
            print('Xmind validation failed; check file format, unique IDs, required case fields and result evidence.', file=sys.stderr)
        raise SystemExit(1)
