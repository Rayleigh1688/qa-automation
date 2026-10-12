"""Directed ISOP-2090 client collection; no admin login or business writes."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path

from filbet.loss_rebate import ROOT, TZ, ContractError, amount, private_json
from filbet.requirement_session import Session
from qa_core.environment import load_environment
from qa_core.case_report import write_views

DETAIL_PATH = "/promo/net/loss/detail"
FALLBACK_PATH = "/member/game/listRw"
FALLBACK_QUERY = {"game_types": "3", "page": 1, "page_size": 10, "sort": "Popular", "query": ""}


def data_object(response):
    body = response.get("body")
    if response.get("http") != 200 or not isinstance(body, dict) or body.get("status") is not True or not isinstance(body.get("data"), dict):
        raise ContractError("client response is not HTTP200/status true/data object")
    return body["data"]


def source_array(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as error:
            raise ContractError("client array string is invalid JSON") from error
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ContractError("client array shape is invalid")
    return value


def game_id(game):
    value = game.get("id") or game.get("game_id")
    if value is None or isinstance(value, (dict, list, bool)):
        raise ContractError("game id missing or invalid")
    return str(value)


def eligible(game):
    code = game.get("code") or game.get("game_code")
    return isinstance(code, str) and bool(code.strip()) and isinstance(game.get("img"), str) and bool(game["img"].strip())


def analyse(detail_response, fallback_response, admin_snapshot):
    detail, fallback = data_object(detail_response), data_object(fallback_response)
    if not {"start_time", "end_time", "cur_time", "state", "conf", "detail", "game_list"}.issubset(detail):
        raise ContractError("observed client detail fields missing")
    if not isinstance(detail["detail"], str) or any(type(detail[key]) is not int for key in ("start_time", "end_time", "cur_time", "state")):
        raise ContractError("observed client detail scalar shape changed")
    if "d" not in fallback or type(fallback.get("t")) is not int or fallback["t"] < 0:
        raise ContractError("observed client fallback list/total missing")
    games = source_array(detail.get("game_list"))
    fallback_games = source_array(fallback.get("d"))
    priority = [game for game in games if eligible(game)]
    chosen = (priority if priority else [game for game in fallback_games if eligible(game)])[:10]
    response = json.loads(Path(admin_snapshot).read_text(encoding="utf-8"))["response"]
    rows = data_object(response).get("d")
    if not isinstance(rows, list):
        raise ContractError("saved admin promo list shape invalid")
    activity = next(row for row in rows if str(row.get("ty")) == "41")
    config = json.loads(activity["config"]) if isinstance(activity.get("config"), str) else activity.get("config")
    if not isinstance(config, dict) or not isinstance(config.get("games"), list):
        raise ContractError("saved admin config games invalid")
    first = config["games"][0] if config["games"] else None
    first_ids = {str(value) for value in (first.get("list", []) if first else [])}
    detail_ids, chosen_ids = {game_id(game) for game in games}, {game_id(game) for game in chosen}
    compliance = sorted({key for game in games + fallback_games for key in game
                         if any(term in key.lower() for term in ("state", "status", "enable", "compliance", "recommend", "risk"))})
    slot = next(row for row in config.get("venue", []) if str(row.get("game_class")) == "3")
    rates = source_array(detail.get("conf"))
    rate_map = {str(item.get("level", "")).strip().lower(): amount(item.get("ratio")) for item in rates}
    slot_map = {str(item.get("level", "")).strip().lower(): amount(item.get("ratio")) for item in slot.get("rebate_ratio", [])}
    return {"detail_fields": {key: type(value).__name__ for key, value in detail.items()},
            "detail_game_count": len(games), "detail_eligible_count": len(priority),
            "fallback_count": len(fallback_games), "selected_count": len(chosen),
            "selection_source": "detail.game_list" if priority else "Slot Popular fallback",
            "first_group_count": len(first_ids), "first_group_state": first.get("state") if first else None,
            "detail_matches_first_group": detail_ids == first_ids,
            "selected_matches_first_group": chosen_ids == first_ids,
            "selected_ids": sorted(chosen_ids), "first_group_ids": sorted(first_ids),
            "game_compliance_field_names": compliance,
            "rate_table_matches_saved_slot": rate_map == slot_map,
            "detail_text_matches_saved_summary": detail.get("detail") == activity.get("summary"),
            "fallback_compliance_observation": [{"id": game_id(game), **{key: game[key] for key in ("compliance", "online", "maintained") if isinstance(game.get(key), (str, int, bool))}} for game in fallback_games],
            "detail_text_length": len(detail.get("detail", "")) if isinstance(detail.get("detail"), str) else None,
            "detail_text_sha256": hashlib.sha256(detail.get("detail", "").encode()).hexdigest() if isinstance(detail.get("detail"), str) else None,
            "rate_table": [{key: item.get(key) for key in ("name", "level", "ratio")
                            if isinstance(item.get(key), (str, int, float))}
                           for item in rates]}


def client_views(folder, report):
    comparison = report.get("comparison", {})
    context = report.get("selection_context", {})
    all_noncompliant = bool(context.get("first_group_matches_comparison") and context.get("first_group_count")
                            and context.get("compliance_2_count") == context.get("first_group_count"))
    rows, results = [], []
    checks = [("shape", "客户端真实响应结构", "C15", "PASS", "详情为data对象；字段类型=" + json.dumps(comparison.get("detail_fields", {})) + "；目录为data.d数组"),
              ("slot-rates", "客户端比例与已存Slot配置", "C15", "PASS" if comparison.get("rate_table_matches_saved_slot") else "FAIL", "五级比例=" + json.dumps(comparison.get("rate_table", []), ensure_ascii=False)),
              ("rich-text", "客户端富文本与已存活动summary", "C15", "PASS" if comparison.get("detail_text_matches_saved_summary") else "NOT_RUN", "已存后台summary与本次detail精确一致" if comparison.get("detail_text_matches_saved_summary") else "与已存summary不同；配置时点需确认"),
              ("first-group", "当前推荐来源与第一组", "C16", "NOT_RUN", f"第一组{comparison.get('first_group_count')}款/state={comparison.get('first_group_state')}；detail返回{comparison.get('detail_game_count')}款；走{comparison.get('selection_source')}选{comparison.get('selected_count')}款；" + ("DB首组全部不合规，开启合规可能过滤为空；采集时header条件未对齐，不能定失败" if all_noncompliant else "第一组独立合规源/采集条件尚未确认")),
              ("compliance", "推荐合规源与过滤", "C16", "NOT_RUN", "目录属性已留证；未由属性名猜合规含义，不证明第一组全部合规或不合规")]
    refs = "; ".join(item["private_evidence"] for item in report["requests"])
    for key, title, case, status, actual in checks:
        ident = "2090-CLIENT-" + key
        results.append({"id": ident, "check_key": key, "case_ids": ["ISOP-2090-" + case], "status": status, "actual": actual, "evidence": refs})
        rows.append({"用例编号": ident, "类型": "API", "模块/接口": DETAIL_PATH, "用例名称": title,
                     "前置条件": "FAT；单次client密码登录；后台只读旧快照", "参数/步骤": "仅detail和Slot Popular目录GET；离线比较",
                     "预期结果": "支持本项合同；未确认的合规含义不推定", "级别": "验收子项", "验收点": "ISOP-2090-" + case})
    report["results"] = results
    report["counts"] = dict(Counter(item["status"] for item in results))
    write_views(folder / "views", rows, report, extra_views=False)


def analyse_recorded(args):
    original = Path(args.recorded).resolve()
    report = json.loads(original.read_text(encoding="utf-8"))
    if (report.get("mode") != "directed-client-readonly" or len(report.get("requests", [])) != 2
            or not isinstance(report.get("source_time"), str) or not report["source_time"]
            or not isinstance(report.get("run_id"), str) or not report["run_id"]):
        raise ValueError("requires the recorded two-GET client batch")
    responses = [json.loads((ROOT / item["private_evidence"]).read_text(encoding="utf-8"))["response"] for item in report["requests"]]
    report.pop("error", None)
    report["comparison"] = analyse(*responses, args.admin_snapshot)
    report["admin_snapshot"] = str(Path(args.admin_snapshot).resolve().relative_to(ROOT))
    report["source_run_id"] = report["run_id"]
    report["mode"] = "recorded-readonly-reassessment"
    report["scope"] = "原客户端两GET响应的离线结构/快照比较；无新登录或请求；仅C15/C16 API子项"
    report["classification"] = {"reviewed_at": datetime.now(TZ).isoformat(),
                                "source_time": report["source_time"], "source_run_id": report["source_run_id"],
                                "source": "原采集时间与原两GET私有证据保留；本次只按真实结构核对及加入独立DB选择条件摘要"}
    report["network_requests"] = 0
    if args.selection_context:
        context = json.loads(Path(args.selection_context).read_text(encoding="utf-8"))
        games = context.get("games")
        if not isinstance(games, list) or any(not isinstance(game, dict) for game in games):
            raise ContractError("selection context game rows missing")
        report["selection_context"] = {
            "source": str(Path(args.selection_context).resolve().relative_to(ROOT)),
            "first_group_matches_comparison": {str(game.get("id")) for game in games} == set(report["comparison"]["first_group_ids"]),
            "first_group_count": len(games),
            "compliance_2_count": sum(game.get("compliance") == 2 for game in games),
            "online_normal_count": sum(game.get("online") == 1 and game.get("maintained") == 1 for game in games),
            "header_context": "独立DB公开摘要记载header外部改变；API与UI采集条件未对齐，不定产品失败",
        }
        report["boundaries"].append("独立DB公开摘要和API时点/合规header条件未对齐；C16保持未定失败")
    report["boundaries"].append("本文件为原两GET响应离线结构核对；0新请求；采集时间保持原值")
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S%f")
    folder = args.out / ("client-readonly-" + stamp + "-analysis")
    folder.mkdir(parents=True, exist_ok=False)
    report["run_id"] = folder.name
    report["source_assets"] = [{"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                               for path in sorted((args.out / "evidence/source").glob("*index-Cucz2P_Y.js"))]
    client_views(folder, report)
    (folder / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"folder": str(folder.relative_to(ROOT)), "comparison": report["comparison"], "counts": report["counts"], "network_requests": 0}, ensure_ascii=False, indent=2))
    return 0


def run_client_readonly(args):
    if Path(args.env).name != ".env.fat":
        raise ValueError("client collector only supports FAT")
    if not args.execute:
        print(json.dumps({"execute": False, "scope": "fresh client password login then two GETs", "paths": [DETAIL_PATH, FALLBACK_PATH]}))
        return 0
    config = load_environment(args.env)
    if config.get("API_URL") != "https://client-fat.filbet2025.com":
        raise ValueError("FAT client endpoint mismatch")
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S%f")
    folder, evidence = args.out / ("client-readonly-" + stamp), args.out / "evidence" / ("client-readonly-" + stamp)
    folder.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    report = {"requirement": "ISOP-2090", "environment": "FAT", "mode": "directed-client-readonly",
              "run_id": folder.name, "source_time": datetime.now(TZ).isoformat(), "requests": [],
              "scope": "client GET detail/fallback; saved admin configuration; no admin login",
              "boundaries": ["仅C15/C16 API子项；不覆盖App/UI整卡", "合规含义与禁用组推荐答复未确认，不以当前响应定义预期"]}
    session = Session(config["API_URL"], config, admin=False, timeout=20, insecure=args.insecure)
    try:
        session.login_client_password()
        report["login"] = "success; client token in memory only"
        responses = []
        for index, (path, query) in enumerate(((DETAIL_PATH, None), (FALLBACK_PATH, FALLBACK_QUERY)), 1):
            response = session.request("GET", path, query=query)
            target = evidence / f"{index:03d}-private.json"
            private_json(target, {"method": "GET", "path": path, "query": query, "response": response})
            body = response.get("body")
            report["requests"].append({"method": "GET", "path": path, "private_evidence": str(target.relative_to(ROOT)),
                                      "http": response.get("http"), "business_status": body.get("status") if isinstance(body, dict) and type(body.get("status")) is bool else None,
                                      "data_type": type(body.get("data")).__name__ if isinstance(body, dict) else None})
            responses.append(response)
        report["comparison"] = analyse(*responses, args.admin_snapshot)
        report["admin_snapshot"] = str(Path(args.admin_snapshot).resolve().relative_to(ROOT))
        client_views(folder, report)
    except Exception as error:
        report["error"] = type(error).__name__ + "; no guessed follow-up requests"
    finally:
        session.token = ""
    (folder / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"folder": str(folder.relative_to(ROOT)), **report}, ensure_ascii=False, indent=2))
    return 1 if "error" in report or any(item["status"] == "FAIL" for item in report.get("results", [])) else 0
