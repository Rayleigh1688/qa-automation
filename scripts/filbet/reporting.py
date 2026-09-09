"""FILBET report defaults layered over the reusable presentation component."""
from qa_core.reporting import *
from qa_core.reporting import write_html_report as _write_html_report


def write_html_report(**kwargs):
    evidence = dict(kwargs.get('evidence') or {})
    evidence.setdefault('images_title', 'Playwright 页面证据')
    evidence.setdefault('image_note', '截图证明页面状态与浏览器交互；充值到账、流水变化和提现同单仍以结构化核对结果为准。')
    evidence.setdefault('checks_title', '统一资金链核对')
    kwargs['evidence'] = evidence
    kind = kwargs.get('report_kind')
    kwargs.setdefault('layout', 'ui' if kind == 'UI' else 'gallery' if kind == '受控 UI 全流程' else 'default')
    return _write_html_report(**kwargs)
