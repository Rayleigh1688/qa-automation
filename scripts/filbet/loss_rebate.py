"""ISOP-2090 directed read-only report checks against frozen row contracts."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from filbet.requirement_api import evaluate as evaluate_query
from filbet.requirement_session import Session
from qa_core.case_report import FIELDS, write_views
from qa_core.environment import load_environment
from qa_core.redaction import sanitize_error

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = "/admin/promo/nl/list"
TZ = ZoneInfo("Asia/Manila")
# 10-12 testing context identifies these rows as pre-submission seed/version data.
HISTORICAL_CONTRACT_DATES = {"2026-10-07"}
CHECK_KEYS = {
    "主表净输等于有效投注减派彩": "main-nl",
    "冻结规则净输等于有效投注减派彩": "rule-nl",
    "冻结规则净输合计与主表净输一致": "nl-sum",
    "冻结规则返利按max净输乘历史比例": "rule-bonus",
    "冻结明细返利合计对应主表封顶前": "before-cap",
    "冻结规则公式合计对应主表封顶前": "formula-before-cap",
    "主表历史上限约束实派": "actual-cap",
    "主表打码金额等于实派乘历史倍数": "turnover",
    "已派发行净输严格超过历史统一门槛": "threshold",
    "每UID每天仅一笔日报": "uid-day",
    "10条分页完整集合与100条参考一致": "pagination",
    "全量汇总去重人数与行金额": "summary",
}


def check_key(title):
    return CHECK_KEYS.get(title, "query-" + hashlib.sha256(title.encode()).hexdigest()[:16])


def evidence_status(rows, failures=None, pending=None):
    """Business relations require records; empty truth is not verification."""
    return "NOT_RUN" if not rows else "FAIL" if failures else "NOT_RUN" if pending else "PASS"


def coverage_features(rows):
    return {
        "negative_rule_rows": sum(any(amount(d.get("net_loss_amount")) < 0 for d in details_of(r)) for r in rows),
        "multi_rule_rows": sum(len(details_of(r)) > 1 for r in rows),
        "zero_cap_rows": sum(amount(r.get("upper_limit")) == 0 for r in rows),
        "zero_gate_rows": sum(amount(r.get("lower_limit")) == 0 for r in rows),
        "positive_gate_rows": sum(amount(r.get("lower_limit")) > 0 for r in rows),
        "nonpositive_nl_rows": sum(amount(r.get("net_loss_amount")) <= 0 for r in rows),
    }


def coverage_boundaries(features):
    missing = []
    if not features["negative_rule_rows"]:
        missing.append("本批无负净输规则，C04负值抵减未测")
    if not features["zero_cap_rows"]:
        missing.append("本批无上限0记录，C03无限上限未测")
    if not features["positive_gate_rows"]:
        missing.append("本批门槛全0，已派正值不证明C02低于/等于门槛及零/负净输拒派")
    return missing


class ContractError(ValueError):
    """A response shape cannot support the intended business assertion."""


def amount(value):
    if value is None or isinstance(value, bool):
        raise ContractError("amount missing or invalid")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ContractError("amount missing or invalid") from error
    if not result.is_finite():
        raise ContractError("amount not finite")
    return result


def parse_page(response):
    body = response.get("body")
    if response.get("http") != 200 or not isinstance(body, dict) or body.get("status") is not True:
        raise ContractError("expected HTTP 200 and business success")
    data = body.get("data")
    if not isinstance(data, dict) or "data" not in data or type(data.get("t")) is not int or data["t"] < 0:
        raise ContractError("nl/list requires data.data rows and integer data.t")
    rows = data["data"]
    if rows is None and data["t"] == 0:
        rows = []
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ContractError("nl/list rows missing or invalid")
    summary = data.get("s")
    if summary is not None and not isinstance(summary, dict):
        raise ContractError("nl/list summary must be an object or null")
    return rows, data["t"], summary


def row_key(row):
    value = row.get("id")
    if value is None or value == "" or isinstance(value, (bool, float)):
        raise ContractError("row id missing or unsafe")
    return str(value)


def row_set(rows):
    keys = [row_key(row) for row in rows]
    if len(set(keys)) != len(keys):
        raise ContractError("duplicate report record id")
    return set(keys)


def pages_equal(pages, baseline):
    combined = [row for page in pages for row in page]
    return len(combined) == len(baseline) and row_set(combined) == row_set(baseline)


def stat_date(value):
    text = str(value or "").strip()
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    if text.isdigit() and len(text) in (10, 13):
        return datetime.fromtimestamp(int(text) / (1000 if len(text) == 13 else 1), TZ).date().isoformat()
    raise ContractError("statistics date missing or unsupported")


def details_of(row):
    value = row.get("conf")
    try:
        details = json.loads(value) if isinstance(value, str) else value
    except (ValueError, TypeError) as error:
        raise ContractError("frozen conf cannot be decoded") from error
    if not isinstance(details, list) or not details or any(not isinstance(item, dict) for item in details):
        raise ContractError("frozen conf must contain rule rows")
    return details


def precision_result(actual, expected):
    """Exact checks pass; sub-cent differences await the rounding contract."""
    if actual == expected:
        return "PASS"
    if expected != expected.quantize(Decimal("0.01")) and abs(actual - expected) < Decimal("0.01"):
        return "NOT_RUN"
    return "FAIL"


def auth_denied(response):
    result, _ = evaluate_query({"expect": "auth_rejected"},
                               {"status": response.get("http"), "decoded_body": response.get("body")})
    return result == "PASS"


def public_observation(response):
    body = response.get("body")
    data = body.get("data") if isinstance(body, dict) else None
    rows = data.get("data") if isinstance(data, dict) else None
    return {"http": response.get("http"),
            "business_status": body.get("status") if isinstance(body, dict)
            and type(body.get("status")) is bool else None,
            "row_count": len(rows) if isinstance(rows, list) else None,
            "total": data.get("t") if isinstance(data, dict) and type(data.get("t")) is int else None,
            "data_type": type(data).__name__}


def private_json(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def selected_dates(args):
    """Use one explicit bounded window for the reference and every filter probe."""
    start, end = getattr(args, "start_date", None), getattr(args, "end_date", None)
    if not start and not end:
        return {}, [f"2026-10-{day:02d}" for day in range(7, 12)]
    if not start or not end:
        raise ValueError("--start-date and --end-date must be supplied together")
    if any(not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) for value in (start, end)):
        raise ValueError("statistics window dates must use YYYY-MM-DD")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    span = (last - first).days
    if not 0 <= span < 31:
        raise ValueError("statistics window must contain 1 to 31 inclusive days")
    return {"stime": start, "etime": end}, [(first + timedelta(days=i)).isoformat() for i in range(span + 1)]


def run_readonly(args):
    if Path(args.env).name != ".env.fat":
        raise ValueError("directed 2090 collector only supports explicit .env.fat")
    date_query, filter_days = selected_dates(args)
    if not args.execute:
        print(json.dumps({"requirement": "ISOP-2090", "path": REPORT_PATH,
                          "scope": "one fresh admin login; GET nl/list only", "execute": False,
                          "date_window": date_query, "date_filter_days": filter_days}))
        return 0
    config = load_environment(args.env)
    if (config.get("ADMIN_URL"), config.get("API_URL")) != (
        "https://admin-fat.filbet2025.com", "https://client-fat.filbet2025.com"
    ):
        raise ValueError("FAT endpoints must match selected environment")
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S%f")
    folder = args.out / ("api-readonly-" + stamp)
    evidence = args.out / "evidence" / ("api-readonly-" + stamp)
    folder.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    results, catalogue, requests = [], [], []
    report = {"requirement": "ISOP-2090", "run_id": folder.name, "environment": "FAT",
              "source_time": datetime.now(TZ).isoformat(), "deployment": "未提供",
              "mode": "directed-readonly", "results": results, "requests": requests,
              "date_window": date_query, "date_filter_days": filter_days,
              "scope": "GET nl/list; frozen conf internal arithmetic, filtering, pagination and auth only",
              "boundaries": ["子项结果不覆盖整条复合功能用例", "未以当前活动配置校验历史比例",
                             "未读取独立注单/奖金钱包/账变/流水源", "未调用导出或业务写接口"]}
    serial = 0

    def record(title, cases, status, actual, refs, *, observation=None):
        ident = f"2090-READ-{len(results) + 1:03d}"
        mapped = ["ISOP-2090-" + case for case in cases]
        item = {"id": ident, "check_key": check_key(title), "case_ids": mapped, "status": status, "actual": actual,
                "category": "未决精度/未具备证据" if status == "NOT_RUN" else "待分析" if status == "FAIL" else "",
                "evidence": "; ".join(refs)}
        if observation:
            item["observation"] = observation
        results.append(item)
        catalogue.append({"用例编号": ident, "类型": "API", "模块/接口": REPORT_PATH,
                          "用例名称": title, "前置条件": "FAT；单次fresh管理员会话；冻结本轮行数据",
                          "参数/步骤": "定向只读采集；原始参数和响应留私有证据，公开只用别名",
                          "预期结果": title + "满足本单v2.0已定合同；精度未决部分不扩判",
                          "级别": "验收子项", "验收点": ", ".join(mapped)})

    session = Session(config["ADMIN_URL"], config, timeout=20, insecure=args.insecure)

    def request(label, query, *, auth="valid"):
        nonlocal serial
        serial += 1
        query = {**date_query, **query}
        response = session.request("GET", REPORT_PATH, query=query, auth=auth)
        target = evidence / f"{serial:03d}-{label}-private.json"
        private_json(target, {"method": "GET", "path": REPORT_PATH, "query": query,
                              "auth": auth, "response": response})
        ref = str(target.relative_to(ROOT))
        requests.append({"label": label, "method": "GET", "path": REPORT_PATH,
                         "auth": auth, "private_evidence": ref,
                         "observation": public_observation(response)})
        return response, ref

    def compare(title, cases, mismatches, refs, *, pending=None, detail=None, samples=None):
        status = evidence_status(samples, mismatches, pending) if samples is not None else "FAIL" if mismatches else "NOT_RUN" if pending else "PASS"
        actual = detail or "冻结行合同全部一致"
        if samples is not None and not samples:
            actual += "；基线无记录，业务关系未验证"
        if mismatches:
            actual += "；不符=" + "; ".join(mismatches[:12])
        if pending:
            actual += "；历史版本/精度待确认=" + "; ".join(pending[:12])
        record(title, cases, status, actual, refs)

    try:
        session.login()
        report["login"] = "success; token in memory only"
        response, base_ref = request("baseline-100", {"page": 1, "page_size": 100})
        baseline, total, summary = parse_page(response)
        if total != len(baseline) or total > 100:
            raise ContractError("bounded baseline not complete; no dependent assertions")
        if date_query and any(not date_query["stime"] <= stat_date(row.get("stats_day")) <= date_query["etime"] for row in baseline):
            raise ContractError("baseline contains rows outside the requested statistics window")
        row_set(baseline)
        record("全量行结构与总条数", ["C14"], "PASS", f"data.data为列表；所选范围全量{len(baseline)}行；data.t={total}", [base_ref])
        aliases = {row_key(row): f"R{index + 1:02d}" for index, row in enumerate(baseline)}
        users = sorted({str(row.get("uid", "")) for row in baseline})
        members = {uid: f"M{index + 1:02d}" for index, uid in enumerate(users)}
        private_json(evidence / "aliases-private.json", {"records": aliases, "members": members})
        report["baseline"] = {"rows": total, "members": len(users),
                              "dates": sorted({stat_date(row.get("stats_day")) for row in baseline}),
                              "coverage_features": coverage_features(baseline)}
        report["boundaries"].extend(coverage_boundaries(report["baseline"]["coverage_features"]))
        pages, page_refs = [], []
        for page in range(1, (total + 9) // 10 + 1):
            current, ref = request(f"page10-{page}", {"page": page, "page_size": 10})
            rows, current_total, _ = parse_page(current)
            if current_total != total or len(rows) > 10:
                raise ContractError("pagination total or page limit changed")
            pages.append(rows)
            page_refs.append(ref)
        compare("10条分页完整集合与100条参考一致", ["C14"], [] if pages_equal(pages, baseline) else ["行集合/数量不一致"], [base_ref, *page_refs], detail=f"已采集{len(pages)}页，共{sum(map(len,pages))}行", samples=baseline)
        filter_results = []
        for day in filter_days:
            current, ref = request("date-" + day, {"page": 1, "page_size": 100, "stime": day, "etime": day})
            rows, found, _ = parse_page(current)
            wanted = [row for row in baseline if stat_date(row.get("stats_day")) == day]
            ok = found == len(rows) and row_set(rows) == row_set(wanted)
            filter_results.append((len(results), ok))
            record("统计日期精确筛选 " + day, ["C14"], "PASS" if ok else "FAIL",
                   f"冻结参考{len(wanted)}行；实际{len(rows)}行；total={found}", [base_ref, ref])
        for key in ("uid", "username", "phone", "vip", "level"):
            sample = next((row for row in baseline if row.get(key) not in (None, "")), None)
            if sample is None:
                record(key + "精确筛选", ["C14"], "NOT_RUN", "冻结基线无非空字段样本", [base_ref])
                continue
            value = str(sample[key])
            current, ref = request("filter-" + key, {"page": 1, "page_size": 100, key: value})
            rows, found, _ = parse_page(current)
            wanted = [row for row in baseline if str(row.get(key, "")) == value]
            ok = found == len(rows) and row_set(rows) == row_set(wanted)
            filter_results.append((len(results), ok))
            record(key + "精确筛选", ["C14"], "PASS" if ok else "FAIL",
                   f"样本{members[str(sample.get('uid',''))]}；冻结参考{len(wanted)}行；实际{len(rows)}行；不公开筛选值", [base_ref, ref])
        current, ref = request("nonexistent-uid", {"page": 1, "page_size": 100, "uid": "999999999999999999"})
        rows, found, _ = parse_page(current)
        record("不存在UID返回空集", ["C14"], "PASS" if not rows and found == 0 else "FAIL", f"实际{len(rows)}行；total={found}", [ref])
        for auth in ("missing", "invalid"):
            current, ref = request("auth-" + auth, {"page": 1, "page_size": 10}, auth=auth)
            record(auth + "鉴权拒绝且不泄露报表", ["C19"], "PASS" if auth_denied(current) else "FAIL",
                   "明确鉴权拒绝且data无业务数据" if auth_denied(current) else "未满足鉴权拒绝/无数据合同", [ref], observation=public_observation(current))
        # Freeze historical rule fields; never use the current activity ratio matrix.
        checks = {key: [] for key in ("main-nl", "rule-nl", "nl-sum", "rule-bonus", "before-cap", "formula-before-cap", "actual-cap", "turnover", "threshold", "uid-day")}
        pending = {key: [] for key in checks}
        seen_uid_days = set()
        for row in baseline:
            alias = aliases[row_key(row)]
            details = details_of(row)
            key = (str(row.get("uid", "")), stat_date(row.get("stats_day")))
            if key in seen_uid_days:
                checks["uid-day"].append(alias)
            seen_uid_days.add(key)
            values = {field: amount(row.get(field)) for field in ("valid_bet_amount", "payout_amount", "net_loss_amount", "capped_amount", "bonus", "upper_limit", "lower_limit", "multiple", "multiple_amount")}
            pairs = [("main-nl", values["net_loss_amount"], values["valid_bet_amount"] - values["payout_amount"]),
                     ("actual-cap", values["bonus"], min(values["capped_amount"], values["upper_limit"]) if values["upper_limit"] > 0 else values["capped_amount"]),
                     ("turnover", values["multiple_amount"], values["bonus"] * values["multiple"])]
            detail_nl = detail_bonus = formula_bonus = Decimal(0)
            for index, detail in enumerate(details):
                tag = f"{alias}/规则{index + 1}"
                nl = amount(detail.get("net_loss_amount"))
                paid = amount(detail.get("bonus", detail.get("capped_amount")))
                expected = max(nl, Decimal(0)) * amount(detail.get("rate")) / 100
                for check, actual, target in (("rule-nl", nl, amount(detail.get("valid_bet_amount")) - amount(detail.get("payout_amount"))), ("rule-bonus", paid, expected)):
                    state = precision_result(actual, target)
                    if state != "PASS":
                        if check == "rule-bonus" and key[1] in HISTORICAL_CONTRACT_DATES:
                            state = "NOT_RUN"
                        (pending if state == "NOT_RUN" else checks)[check].append(f"{tag} 实际{actual}/应为{target}")
                detail_nl += nl
                detail_bonus += paid
                formula_bonus += expected
            pairs.extend([("nl-sum", values["net_loss_amount"], detail_nl),
                          ("before-cap", values["capped_amount"], detail_bonus),
                          ("formula-before-cap", values["capped_amount"], formula_bonus)])
            for check, actual, target in pairs:
                state = precision_result(actual, target)
                if state != "PASS":
                    if check == "formula-before-cap" and key[1] in HISTORICAL_CONTRACT_DATES:
                        state = "NOT_RUN"
                    (pending if state == "NOT_RUN" else checks)[check].append(f"{alias} 实际{actual}/应为{target}")
            if values["net_loss_amount"] <= values["lower_limit"]:
                checks["threshold"].append(alias)
        definitions = [("main-nl", "主表净输等于有效投注减派彩", ["C14"]),
                       ("rule-nl", "冻结规则净输等于有效投注减派彩", ["C14"]),
                       ("nl-sum", "冻结规则净输合计与主表净输一致", ["C14"]),
                       ("rule-bonus", "冻结规则返利按max净输乘历史比例", ["C14"]),
                       ("before-cap", "冻结明细返利合计对应主表封顶前", ["C14"]),
                       ("formula-before-cap", "冻结规则公式合计对应主表封顶前", ["C14", "C03"]),
                       ("actual-cap", "主表历史上限约束实派", ["C03", "C14"]),
                       ("turnover", "主表打码金额等于实派乘历史倍数", ["C08", "C14"]),
                       ("threshold", "已派发行净输严格超过历史统一门槛", ["C01", "C02", "C14"]),
                       ("uid-day", "每UID每天仅一笔日报", ["C08", "C14"])]
        for key, title, cases in definitions:
            compare(title, cases, checks[key], [base_ref], pending=pending[key], detail=f"冻结{len(baseline)}行，未读取当前比例配置", samples=baseline)
        summary_failures = []
        if not isinstance(summary, dict):
            record("全量汇总去重人数与行金额", ["C14"], "NOT_RUN", "响应未提供汇总对象", [base_ref])
        else:
            expected = {"num": Decimal(len(users)), **{key: sum((amount(row.get(key)) for row in baseline), Decimal(0)) for key in ("net_loss_amount", "bonus", "multiple_amount")}}
            for key, value in expected.items():
                if amount(summary.get(key)) != value:
                    summary_failures.append(f"{key} 实际{summary.get(key)}/应为{value}")
            compare("全量汇总去重人数与行金额", ["C14"], summary_failures, [base_ref], detail="行数与UID人数分别核；汇总=" + json.dumps({k: str(v) for k,v in expected.items()}, ensure_ascii=False), samples=baseline)
        current, stable_ref = request("baseline-final-100", {"page": 1, "page_size": 100})
        final_rows, final_total, _ = parse_page(current)
        stable = final_total == total and sorted(map(lambda row: json.dumps(row, sort_keys=True), final_rows)) == sorted(map(lambda row: json.dumps(row, sort_keys=True), baseline))
        record("筛选采集前后冻结集合稳定", ["C14"], "PASS" if stable else "NOT_RUN", "首末完整行值一致" if stable else "首末数据变化；本批筛选差异须重采稳定窗口", [base_ref, stable_ref])
        if not stable:
            for index, ok in filter_results:
                if not ok:
                    results[index].update(status="NOT_RUN", category="在线数据变化", actual=results[index]["actual"] + "；首末基线变化，暂不定性产品失败")
    except Exception as error:
        record("采集前置或合同异常", ["C14"], "ERROR", sanitize_error(error, config), [str(evidence.relative_to(ROOT))])
    finally:
        session.token = ""
    report["counts"] = dict(Counter(item["status"] for item in results))
    report["source_assets"] = []
    for path in sorted((args.out / "evidence/source").glob("*.js")):
        if path.name.endswith(("umi-d433ca66.js", "index-0daee2f9.js", "index-3f1ae5ae.js")):
            content = path.read_bytes()
            if not content.lstrip().lower().startswith(b"<!doctype"):
                report["source_assets"].append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(content).hexdigest()})
    (folder / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_views(folder / "views", catalogue, report, extra_views=False)
    print(json.dumps({"folder": str(folder.relative_to(ROOT)), "counts": report["counts"],
                      "baseline": report.get("baseline"), "requests": len(requests),
                      "failures": [{"id": item["id"], "case_ids": item["case_ids"], "actual": item["actual"]} for item in results if item["status"] in {"FAIL", "ERROR"}]}, ensure_ascii=False, indent=2))
    return 1 if any(item["status"] in {"FAIL", "ERROR"} for item in results) else 0


def reassess_recorded(path):
    """Reclassify existing frozen evidence; preserve the original run and time."""
    import csv
    path = Path(path).resolve()
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("requirement") != "ISOP-2090" or report.get("mode") != "directed-readonly":
        raise ValueError("reassessment requires an original directed 2090 report")
    original = Path(path).parent
    with (original / "views/results.csv").open(encoding="utf-8-sig", newline="") as stream:
        catalogue = [{key: row[key] for key in FIELDS} for row in csv.DictReader(stream)]
    titles = {row["用例编号"]: row["用例名称"] for row in catalogue}
    baseline_ref = next(item["private_evidence"] for item in report["requests"] if item["label"] == "baseline-100")
    baseline_file = ROOT / baseline_ref
    response = json.loads(baseline_file.read_text(encoding="utf-8"))["response"]
    baseline, _, _ = parse_page(response)
    report.setdefault("baseline", {})["coverage_features"] = coverage_features(baseline)
    report["boundaries"] = list(dict.fromkeys(report.get("boundaries", []) +
        coverage_boundaries(report["baseline"]["coverage_features"])))
    rule_failures, rule_pending, formula_failures, formula_pending = [], [], [], []
    historical_examples = []
    for index, row in enumerate(baseline):
        alias = f"R{index + 1:02d}"
        historical = stat_date(row["stats_day"]) in HISTORICAL_CONTRACT_DATES
        formula = Decimal(0)
        for position, detail in enumerate(details_of(row)):
            expected = max(amount(detail["net_loss_amount"]), Decimal(0)) * amount(detail["rate"]) / 100
            paid = amount(detail.get("bonus", detail.get("capped_amount")))
            formula += expected
            status = precision_result(paid, expected)
            if status != "PASS":
                text = f"{alias}/规则{position + 1} 实际{paid}/应为{expected}"
                (rule_pending if historical or status == "NOT_RUN" else rule_failures).append(text)
        actual = amount(row["capped_amount"])
        status = precision_result(actual, formula)
        if status != "PASS":
            text = f"{alias} 实际{actual}/应为{formula}"
            (formula_pending if historical or status == "NOT_RUN" else formula_failures).append(text)
            if historical:
                historical_examples.append(text)
    for item in report["results"]:
        # Legacy reports gain keys from their saved catalogue, never numeric position.
        item.setdefault("check_key", check_key(titles[item["id"]]))
        key = item["check_key"]
        if key in {"rule-bonus", "formula-before-cap"}:
            failures, pending = (rule_failures, rule_pending) if key == "rule-bonus" else (formula_failures, formula_pending)
            item["status"] = evidence_status(baseline, failures, pending)
            item["actual"] = f"冻结{len(baseline)}行；只用历史conf；10-07种子/版本数据不定当前算法失败"
            if failures:
                item["actual"] += "；不符=" + "; ".join(failures)
            if pending:
                item["actual"] += "；历史版本/亚分精度待确认=" + "; ".join(pending)
            item["category"] = "明细展示金额候选" if failures else "历史版本/精度未决"
        if key in {"nl-sum", "rule-bonus", "before-cap"}:
            item["case_ids"] = ["ISOP-2090-C14"]
        if not baseline and key in set(CHECK_KEYS.values()):
            item.update(status="NOT_RUN", category="无业务样本", actual="冻结基线无记录，业务关系未验证")
        if key in {"rule-bonus", "before-cap"}:
            item["finding_group"] = "CONF_PRECAP_DISPLAY"
        if key == "turnover":
            item["finding_group"] = "TURNOVER_ACTUAL_AMOUNT"
            item["category"] = "实派与打码金额候选"
    report["source_assets"] = [item for item in report.get("source_assets", [])
                               if not (ROOT / item["path"]).read_bytes().lstrip().lower().startswith(b"<!doctype")]
    report["classification"] = {"reviewed_at": datetime.now(TZ).isoformat(),
                                "historical_contract_dates": sorted(HISTORICAL_CONTRACT_DATES),
                                "source": "10-12当前测试上下文：10-07为提测前种子/旧配置版本；不可直接定当前算法BUG",
                                "historical_examples": historical_examples,
                                "precision": "亚分公式与两位展示值的差异保持待确认；未指定舍入算法",
                                "turnover": "保留已实派145.79乘2与291.59的1分差候选；本runner未查独立账变/流水源"}
    report["source_run_id"] = report["run_id"]
    report["mode"] = "recorded-readonly-reassessment"
    report["network_requests"] = 0
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S%f")
    folder = original.parent / ("api-readonly-" + stamp + "-reassessment")
    folder.mkdir(exist_ok=False)
    report["run_id"] = folder.name
    report["counts"] = dict(Counter(item["status"] for item in report["results"]))
    for row in catalogue:
        if check_key(row["用例名称"]) in {"nl-sum", "rule-bonus", "before-cap"}:
            row["验收点"] = "ISOP-2090-C14"
    (folder / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_views(folder / "views", catalogue, report, extra_views=False)
    print(json.dumps({"folder": str(folder.relative_to(ROOT)), "counts": report["counts"],
                      "original_preserved": str(Path(path).relative_to(ROOT)), "network_requests": 0}, ensure_ascii=False, indent=2))
    return 0
