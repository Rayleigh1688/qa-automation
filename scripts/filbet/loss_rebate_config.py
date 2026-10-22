"""Guarded FAT ty41 configuration checks; never changes funds or permissions.

Contract: verified kn/zc in index-0daee2f9.js, not the separate ty40 editor.
The only successful content mutation allowed by this lane is a reversible summary marker.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo

from filbet.requirement_session import Session
from qa_core.environment import load_environment
from qa_core.case_report import write_views
from totp import current_totp

ROOT = Path(__file__).resolve().parents[2]
TZ = ZoneInfo("Asia/Manila")
LIST_PATH = "/admin/promo/list"
UPDATE_PATH = "/admin/promo/update"
DETAIL_PATH = "/promo/net/loss/detail"
QUERY = {"page": 1, "page_size": 100}
IGNORED = {"updated_at", "updated_uid", "updated_name"}
VIP_LEVELS = ("bronze", "silver", "gold", "platinum", "diamond")
NEGATIVE_KEYS = ("duplicate-game", "empty-group-name", "duplicate-group-name", "long-group-name",
                 "negative-lower-limit", "negative-upper-limit", "negative-multiple",
                 "negative-group-rate", "negative-vip-ratio")
CONFIG_CHECK_KEYS = ("same-value",) + NEGATIVE_KEYS


class ContractError(ValueError):
    pass


class ConcurrentChange(RuntimeError):
    pass


def select_checks(requested=None):
    """Keep the existing order, but never add checks to an explicit selection."""
    if requested is None:
        return CONFIG_CHECK_KEYS
    if (not isinstance(requested, (list, tuple)) or not requested
            or any(not isinstance(key, str) or key not in CONFIG_CHECK_KEYS for key in requested)
            or len(set(requested)) != len(requested)):
        raise ContractError("checks must be a nonempty, unique selection from the config check allowlist")
    return tuple(key for key in CONFIG_CHECK_KEYS if key in requested)


def private_json(path, data):
    """Create evidence exclusively with private permissions, including before first write."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def status(response):
    body = response.get("body")
    return body.get("status") if isinstance(body, dict) and type(body.get("status")) is bool else None


def activity(response):
    body = response.get("body")
    data = body.get("data") if isinstance(body, dict) else None
    if response.get("http") != 200 or status(response) is not True or not isinstance(data, dict):
        raise ContractError("activity list must be HTTP200/status true/data object")
    rows = data.get("d")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ContractError("activity list rows missing")
    if type(data.get("t")) is not int or data["t"] > len(rows):
        raise ContractError("activity list must be complete in first page")
    selected = [row for row in rows if str(row.get("ty")) == "41"]
    if len(selected) != 1 or str(selected[0].get("id")) != "41":
        raise ContractError("requires unique ty41/activity41")
    return deepcopy(selected[0])


def business(row):
    result = {key: deepcopy(value) for key, value in row.items() if key not in IGNORED}
    value = result.get("config")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as error:
            raise ContractError("invalid activity config JSON") from error
    if not isinstance(value, dict):
        raise ContractError("activity config must be object")
    result["config"] = value
    return result


def differences(first, second):
    """Field names only; raw values remain in private evidence."""
    a, b = business(first), business(second)
    keys = sorted(key for key in set(a) | set(b) if a.get(key) != b.get(key))
    if "config" in keys:
        keys.remove("config")
        keys += ["config." + key for key in sorted(set(a["config"]) | set(b["config"]))
                 if a["config"].get(key) != b["config"].get(key)]
    return keys


def string_value(value, default="0"):
    return default if value is None or value == "" else str(value)


def ids(value):
    if not isinstance(value, list) or any(isinstance(item, (dict, list, bool)) or item is None for item in value):
        raise ContractError("game IDs must be a list of scalars")
    return list(dict.fromkeys(str(item) for item in value if str(item)))


def group_name(value):
    # JavaScript String.slice and length count UTF-16 units, including emoji pairs.
    return str(value).strip().encode("utf-16-le", "surrogatepass")[:40].decode("utf-16-le", "surrogatepass")


def vip_rates(value):
    # Fc/Pn initializes the five canonical levels before zc serializes the editor state.
    rates = {str(item["level"]).strip().lower(): string_value(item.get("ratio")) for item in value}
    return [{"level": level, "ratio": rates.get(level, "0")} for level in VIP_LEVELS]


def save_body(row):
    """Equivalent ty41 registered Step1 fields and zc save format for this frozen baseline.

    Refuse normalization drift: this lane cannot silently change gates/rates/groups/limits.
    turnover_limit is already the backend mapping, the result of the editor's ht(Qe(...)).
    """
    original = business(row)["config"]
    required = {"venue", "games", "exclude_games", "turnover_limit", "lower_limit", "upper_limit",
                "activity_range", "user_list", "source_rule", "popup_text", "order_review", "received_type"}
    if not required.issubset(original) or not isinstance(original["turnover_limit"], dict):
        raise ContractError("full observed ty41 config contract required")
    if row.get("state") not in (1, 2) or str(row.get("ty")) != "41" or str(row.get("id")) != "41":
        raise ContractError("baseline is not active/inactive activity41")
    if not isinstance(row.get("summary"), str):
        raise ContractError("summary string required")
    config = {key: deepcopy(value) for key, value in original.items()
              if key not in {"venue", "games", "exclude_games", "exclude_gid", "turnover_limit", "user_list", "multiple"}}
    config.update({
        "venue": [{"name": item["name"], "game_class": str(item["game_class"]),
                   "rebate_ratio": vip_rates(item["rebate_ratio"])} for item in original["venue"]],
        "games": [{"name": group_name(item["name"]), "list": ids(item["list"]),
                   "rate": string_value(item.get("rate")), "state": 1 if item.get("state") in (1, "1") else 0}
                  for item in original["games"]],
        "exclude_games": ids(original["exclude_games"]),
        "upper_limit": string_value(original["upper_limit"]), "lower_limit": string_value(original["lower_limit"]),
        "turnover_limit": deepcopy(original["turnover_limit"]), "activity_range": int(original["activity_range"]),
        "user_list": [] if int(original["activity_range"]) == 0 else deepcopy(original["user_list"]),
        "source_rule": int(original["source_rule"]),
        "popup_text": str(original["popup_text"]).strip() or "Congratulations! You received Loss Rebate Bonus!",
        "order_review": 1, "received_type": 2})
    if config != original:
        raise ContractError("ty41 save formatting would change frozen business config")
    def date_field(key):
        value = row[key]
        if type(value) not in (int, float):
            raise ContractError("display timestamps must be epoch milliseconds")
        return datetime.fromtimestamp(value / 1000, TZ).strftime("%Y-%m-%d %H:%M:%S")
    return {"activity_type": 2, "id": row["id"], "name": row["name"], "state": row["state"],
            "start_at": date_field("display_start_at"), "end_at": date_field("display_end_at"),
            "source_introduction": 1, "ty": row["ty"], "multiple": string_value(row.get("multiple"), "1"),
            "config": json.dumps(config, ensure_ascii=False, separators=(",", ":")), "summary": row["summary"]}


def negative_body(body, key):
    """Mutate after valid formatting so UI normalization does not repair the negative."""
    result = deepcopy(body)
    config = json.loads(result["config"])
    groups = config["games"]
    if len(groups) < 2 or not groups[0]["list"] or not config["venue"][0]["rebate_ratio"]:
        raise ContractError("negative samples require two groups and venue/VIP samples")
    if key == "duplicate-game":
        groups[1]["list"].append(groups[0]["list"][0])
    elif key == "empty-group-name":
        groups[0]["name"] = ""
    elif key == "duplicate-group-name":
        groups[1]["name"] = groups[0]["name"]
    elif key == "long-group-name":
        groups[0]["name"] = "QA2090-" + "X" * 14  # exactly 21 ASCII characters
    elif key in ("negative-lower-limit", "negative-upper-limit"):
        config[key.removeprefix("negative-").replace("-", "_")] = "-1"
    elif key == "negative-multiple":
        result["multiple"] = "-1"
    elif key == "negative-group-rate":
        groups[0]["rate"] = "-1"
    elif key == "negative-vip-ratio":
        config["venue"][0]["rebate_ratio"][0]["ratio"] = "-1"
    else:
        raise ValueError("unknown negative")
    result["config"] = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    return result


def candidate_state(baseline, body):
    """Only writable activity fields owned by this precise candidate; other fields stay frozen."""
    result = deepcopy(baseline)
    for key in ("name", "state", "summary", "multiple", "config"):
        result[key] = deepcopy(body[key])
    return result


class ApprovalCode:
    def __init__(self, config):
        self.secret = config.get("ADMIN_APPROVAL_TOTP_SECRET")
        self.algorithm = config.get("ADMIN_APPROVAL_TOTP_ALGORITHM", "SHA1")
        self.last = None
        if not self.secret:
            raise ValueError("fresh approval TOTP secret required")

    def __call__(self):
        while True:
            now = time.time()
            remaining = 30 - now % 30
            code = current_totp(self.secret, timestamp=now, algorithm=self.algorithm)
            if remaining <= 3 or code == self.last:
                time.sleep(remaining + 0.15)
                continue
            self.last = code
            return int(code)


class GuardedChecks:
    def __init__(self, session, code, evidence, report):
        self.session, self.code, self.evidence, self.report = session, code, evidence, report
        self.sequence = 0
        self.post_attempts = 0
        self.restore_attempted = False
        self.baseline = None
        self.last = None

    def request(self, method, path, label, **kwargs):
        self.sequence += 1
        target = self.evidence / f"{self.sequence:03d}-{label}-private.json"
        recorded = {"method": method, "path": path, "time": datetime.now(TZ).isoformat()}
        if "body" in kwargs:
            recorded["body"] = {key: value for key, value in kwargs["body"].items() if key != "google_code"}
        if "query" in kwargs:
            recorded["query"] = kwargs["query"]
        try:
            if method == "POST":
                self.post_attempts += 1
            response = self.session.request(method, path, **kwargs)
        except (Exception, KeyboardInterrupt) as error:
            recorded["error_type"] = type(error).__name__  # never include unsafe exception text
            private_json(target, recorded)
            self.report["requests"].append({"method": method, "path": path, "label": label,
                                            "private_evidence": str(target.relative_to(ROOT)), "error_type": type(error).__name__})
            raise
        recorded["response"] = response
        private_json(target, recorded)
        self.report["requests"].append({"method": method, "path": path, "label": label,
                                        "private_evidence": str(target.relative_to(ROOT)), "http": response.get("http"),
                                        "business_status": status(response)})
        return response

    def read(self, label):
        self.last = activity(self.request("GET", LIST_PATH, label, query=QUERY))
        return self.last

    def post(self, body, expected, label):
        # Acquire the fresh one-use code first; the CAS GET is immediately before POST.
        code = self.code()
        current = self.read(label + "-cas")
        if business(current) != business(expected):
            raise ConcurrentChange("fresh activity differs; no POST issued")
        return self.request("POST", UPDATE_PATH, label + "-post", body={**body, "google_code": code},
                            headers={"content-type": "application/json"}, encoding="cbor")

    def result(self, key, outcome, actual, case="C18"):
        refs = [item["private_evidence"] for item in self.report["requests"] if item["label"].startswith(key)]
        self.report["results"].append({"id": "2090-CONFIG-" + key, "check_key": key,
                                        "case_ids": ["ISOP-2090-" + case], "status": outcome,
                                        "actual": actual, "evidence": str(self.evidence.relative_to(ROOT)),
                                        "private_evidence": refs})

    def restore(self, observed, candidate, label="restore"):
        """One independent cleanup attempt, never turns the failed check into PASS."""
        if business(observed) == business(self.baseline):
            self.report["restoration"] = {"status": "UNCHANGED", "business_fields_match_baseline": True}
            return True
        if business(observed) != business(candidate_state(self.baseline, candidate)):
            self.report["restoration"] = {"status": "EXTERNAL_OR_UNKNOWN", "business_fields_match_baseline": False,
                                          "difference_fields_from_candidate": differences(candidate_state(self.baseline, candidate), observed),
                                          "no_restore_post": True}
            return False
        if self.restore_attempted:
            self.report.setdefault("restoration", {})["no_second_restore_post"] = True
            return False
        self.restore_attempted = True
        try:
            response = self.post(save_body(self.baseline), observed, label)
            final = self.read(label + "-readback")
            ok = response.get("http") == 200 and status(response) is True and not differences(self.baseline, final)
            self.report["restoration"] = {"status": "RESTORED" if ok else "FAILED", "business_fields_match_baseline": not differences(self.baseline, final),
                                          "difference_fields": differences(self.baseline, final)}
            return ok
        except KeyboardInterrupt:
            self.report["restoration"] = {"status": "UNKNOWN", "error_type": "KeyboardInterrupt", "no_post_retry": True}
            raise
        except Exception as error:
            self.report["restoration"] = {"status": "UNKNOWN", "error_type": type(error).__name__, "no_post_retry": True}
            return False

    def run(self, marker=False, client=None, marker_only=False, selected=None):
        keys = select_checks(selected)
        if selected is not None and (marker or marker_only):
            raise ContractError("selected checks cannot combine with marker modes")
        self.report["selected_checks"] = [] if marker_only else list(keys)
        self.baseline = self.read("baseline")
        private_json(self.evidence / "baseline-activity41-private.json", self.baseline)
        body = save_body(self.baseline)
        if marker_only:
            self.marker(body, client)
            return
        for key in keys:
            candidate = body if key == "same-value" else negative_body(body, key)
            attempts_before = self.post_attempts
            try:
                response = self.post(candidate, self.baseline, key)
                current = self.read(key + "-readback")
                wanted = True if key == "same-value" else False
                delta = differences(self.baseline, current)
                ok = response.get("http") == 200 and status(response) is wanted and not delta
                self.result(key, "PASS" if ok else "FAIL",
                            f"HTTP={response.get('http')}; business status={status(response)}; changed fields={delta}; expected status={wanted}",
                            "C07" if key == "duplicate-game" else "C18")
                if not ok:
                    self.report["stopped"] = key + ": contract failed; remaining writes stopped"
                    self.restore(current, candidate)
                    break
            except ConcurrentChange:
                self.result(key, "NOT_RUN", "fresh CAS found external business change; no POST")
                self.report["stopped"] = key + ": external change; no restore over external configuration"
                break
            except (Exception, KeyboardInterrupt) as error:
                recorded = next((item for item in self.report["results"] if item["check_key"] == key), None)
                if recorded is None:
                    self.result(key, "FAIL", type(error).__name__ + "; ambiguous operation; no POST retry")
                else:
                    recorded["followup_error_type"] = type(error).__name__
                self.report.setdefault("stopped", key + ": ambiguous operation; remaining writes stopped")
                if isinstance(error, KeyboardInterrupt):
                    self.report["interrupted"] = key + ": KeyboardInterrupt; no further requests"
                    if self.post_attempts > attempts_before:
                        self.report["restoration"] = {"status": "UNKNOWN", "error_type": "KeyboardInterrupt", "no_post_retry": True}
                    else:
                        self.report["restoration"] = {"status": "NOT_NEEDED", "reason": "no POST issued"}
                    break
                if self.post_attempts > attempts_before:
                    try:
                        observed = self.read("uncertain-readback")
                        self.restore(observed, candidate)
                    except (Exception, KeyboardInterrupt) as read_error:
                        self.report["restoration"] = {"status": "UNKNOWN", "error_type": type(read_error).__name__}
                        if isinstance(read_error, KeyboardInterrupt):
                            self.report["interrupted"] = key + ": KeyboardInterrupt during uncertain readback/cleanup"
                else:
                    self.report["restoration"] = {"status": "NOT_NEEDED", "reason": "no POST issued"}
                break
        finished = {item["check_key"] for item in self.report["results"]}
        for key in CONFIG_CHECK_KEYS:
            if key not in finished:
                reason = "not selected in this directed batch" if key not in keys else "stopped after prior failure/external change"
                self.result(key, "NOT_RUN", reason, "C07" if key == "duplicate-game" else "C18")
        if marker and not self.report.get("stopped"):
            self.marker(body, client)
        else:
            self.result("rich-text-marker", "NOT_RUN", "marker disabled or preceding config check stopped", "C15")

    def client_detail(self, client, label):
        original = self.session
        try:
            self.session = client
            response = self.request("GET", DETAIL_PATH, label)
        finally:
            self.session = original
        body = response.get("body")
        data = body.get("data") if isinstance(body, dict) else None
        if response.get("http") != 200 or status(response) is not True or not isinstance(data, dict) or not isinstance(data.get("detail"), str):
            raise ContractError("client detail contract changed")
        return data["detail"]

    def marker(self, body, client):
        marker = "QA2090-" + self.report["run_id"]
        candidate = {**body, "summary": body["summary"] + "<p>" + marker + "</p>"}
        attempts_before = self.post_attempts
        try:
            client.login_client_password()
            old_text = self.client_detail(client, "rich-text-marker-before")
            if old_text != self.baseline["summary"]:
                raise ContractError("client baseline does not match admin summary")
            response = self.post(candidate, self.baseline, "rich-text-marker")
            current = self.read("rich-text-marker-readback")
            expected = deepcopy(self.baseline)
            expected["summary"] = candidate["summary"]
            text = self.client_detail(client, "rich-text-marker-client")
            ok = response.get("http") == 200 and status(response) is True and business(current) == business(expected) and text == candidate["summary"]
            restored = self.restore(current, candidate, "rich-text-marker-restore")
            final_text = self.client_detail(client, "rich-text-marker-restored-client")
            ok = ok and restored and final_text == old_text
            self.result("rich-text-marker", "PASS" if ok else "FAIL", "unique marker client sync and exact admin/client restore=" + str(ok), "C15")
        except ConcurrentChange:
            self.result("rich-text-marker", "NOT_RUN", "external CAS change; no overwrite", "C15")
        except KeyboardInterrupt:
            self.report["interrupted"] = "rich-text-marker: KeyboardInterrupt; no further requests"
            self.report["stopped"] = "rich-text-marker: interrupted; sync/restore not completed"
            self.result("rich-text-marker", "FAIL", "KeyboardInterrupt; marker sync/restore incomplete; no POST retry", "C15")
            if self.post_attempts > attempts_before:
                if self.report.get("restoration", {}).get("status") in ("RESTORED", "UNCHANGED"):
                    self.report["restoration"]["client_restoration_unverified"] = True
                else:
                    self.report["restoration"] = {"status": "UNKNOWN", "error_type": "KeyboardInterrupt", "no_post_retry": True}
            else:
                self.report["restoration"] = {"status": "NOT_NEEDED", "reason": "no marker POST issued"}
        except Exception as error:
            self.result("rich-text-marker", "FAIL", type(error).__name__ + "; marker sync/restore uncertain", "C15")
            if self.post_attempts > attempts_before:
                try:
                    current = self.read("rich-text-marker-uncertain-readback")
                    self.restore(current, candidate, "rich-text-marker-restore")
                except (Exception, KeyboardInterrupt) as read_error:
                    self.report["restoration"] = {"status": "UNKNOWN", "error_type": type(read_error).__name__}
                    if isinstance(read_error, KeyboardInterrupt):
                        self.report["interrupted"] = "rich-text-marker: KeyboardInterrupt during uncertain readback/cleanup"
                        self.report["stopped"] = "rich-text-marker: interrupted; restore unknown"
        finally:
            client.token = ""


def finish(folder, report):
    report["counts"] = dict(Counter(item["status"] for item in report["results"]))
    rows = [{"用例编号": item["id"], "类型": "API", "模块/接口": UPDATE_PATH, "用例名称": item["check_key"],
             "前置条件": "FAT activity41 frozen baseline; fresh approval code and immediate CAS",
             "参数/步骤": "independent exact ty41 body; POST once; GET full business readback",
             "预期结果": "same value accepted; negatives explicitly rejected without mutation; marker immediately restored",
             "级别": "验收子项", "验收点": ";".join(item["case_ids"])} for item in report["results"]]
    (folder / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if rows:
        write_views(folder / "views", rows, report, extra_views=False)


def run_config(args):
    if Path(args.env).name != ".env.fat":
        raise ValueError("config lane requires .env.fat")
    requested = getattr(args, "checks", None)
    keys = select_checks(requested)
    if requested is not None and (args.marker or args.marker_only or args.restore_from):
        raise ContractError("selected checks cannot combine with marker or restoration modes")
    if not args.execute:
        print(json.dumps({"execute": False, "environment": "FAT", "activity": 41,
                          "steps": ["single baseline", "reversible summary marker"] if args.marker_only else
                          ["single baseline"] + list(keys) + (["reversible summary marker"] if args.marker else []),
                          "guards": ["exact FAT hosts", "CAS before every POST", "one POST attempt", "stop and restore on failure"],
                          "restore_from": str(args.restore_from) if args.restore_from else None,
                          "network_requests": 0}, ensure_ascii=False))
        return 0
    if args.fat_guard != "ISOP-2090-activity41":
        raise ValueError("execute requires --fat-guard ISOP-2090-activity41")
    config = load_environment(args.env)
    if (config.get("ADMIN_URL"), config.get("API_URL")) != ("https://admin-fat.filbet2025.com", "https://client-fat.filbet2025.com"):
        raise ValueError("FAT hosts mismatch")
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S%f")
    name = "config-directed-" + stamp
    folder, evidence = args.out / name, args.out / "evidence" / name
    folder.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    report = {"requirement": "ISOP-2090", "environment": "FAT", "mode": "directed-config-guarded", "run_id": name,
              "source_time": datetime.now(TZ).isoformat(), "requests": [], "results": [],
              "scope": "activity41 same-value/invalid config; optional summary marker; no funds/permissions/jobs",
              "boundaries": ["API validation children only; UI and date settlement not covered",
                             "CAS detects pre-POST drift; backend lacks atomic revision precondition",
                             "restore outcome is separate and never converts failed business check to PASS"],
              "source": "evidence/source/ty41-loss-rebate-save-contract-verified.txt"}
    if args.marker_only:
        report["mode"] = "directed-config-marker-only"
    admin = Session(config["ADMIN_URL"], config, timeout=20, insecure=args.insecure)
    client = Session(config["API_URL"], config, admin=False, timeout=20, insecure=args.insecure) if args.marker or args.marker_only else None
    try:
        codes = ApprovalCode(config)
        admin.login()
        report["login"] = "fresh admin; token memory only"
        checks = GuardedChecks(admin, codes, evidence, report)
        if args.restore_from:
            source = Path(args.restore_from).resolve()
            original = json.loads(source.read_text(encoding="utf-8"))
            if original.get("mode") != "directed-config-guarded" or original.get("environment") != "FAT":
                raise ContractError("requires recorded FAT guarded config batch")
            source_evidence = args.out.resolve() / "evidence" / original["run_id"]
            if source_evidence.parent != args.out.resolve() / "evidence":
                raise ContractError("source evidence outside selected batch root")
            checks.baseline = json.loads((source_evidence / "baseline-activity41-private.json").read_text(encoding="utf-8"))
            accepted = [item for item in original["requests"] if item["method"] == "POST" and item.get("business_status") is True]
            last = accepted[-1]
            key = last["label"].removesuffix("-post")
            if key not in NEGATIVE_KEYS or not any(item["check_key"] == key and item["status"] == "FAIL" for item in original["results"]):
                raise ContractError("cleanup requires a recorded unexpectedly accepted negative")
            record = ROOT / last["private_evidence"]
            if record.resolve().parent != source_evidence:
                raise ContractError("unexpected source response path")
            candidate = json.loads(record.read_text(encoding="utf-8"))["body"]
            if candidate != negative_body(save_body(checks.baseline), key):
                raise ContractError("recorded candidate does not match exact negative body")
            report["mode"] = "directed-config-restoration"
            report["source_batch"] = str(source.relative_to(ROOT))
            report["source_failed_check"] = key
            current = checks.read("cleanup-baseline")
            ok = checks.restore(current, candidate, "cleanup-restore")
            checks.result("cleanup-restore", "PASS" if ok else "FAIL", "independent cleanup; original negative remains FAIL; exact baseline restored=" + str(ok))
        else:
            checks.run(args.marker, client, args.marker_only, selected=requested)
    except (Exception, KeyboardInterrupt) as error:
        report["error_type"] = type(error).__name__
    finally:
        admin.token = ""
        if client:
            client.token = ""
        finish(folder, report)
    print(json.dumps({"folder": str(folder.relative_to(ROOT)), "counts": report["counts"], "stopped": report.get("stopped"),
                      "restoration": report.get("restoration"), "error_type": report.get("error_type")}, ensure_ascii=False, indent=2))
    return 1 if report.get("error_type") or any(item["status"] == "FAIL" for item in report["results"]) else 0
