#!/usr/bin/env python3
"""Consolidate valid admin discovery evidence and write-action disposition."""

from __future__ import annotations

import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; D=ROOT/"fat-admin-interface-scan"; R=D/"results"
MAP_FIELDS=["surface","top_menu","page_name","page_route","control_type","action_name","method","normalized_path","query_fields","path_fields","body_fields","header_fields","parameter_source","http_status","business_status","response_structure","auth_role","side_effect","before_state","after_state","original_category","original_name","original_source_file","classification","currently_used_by_ui","evidence","anomaly","blocked_scope"]

def canon(p):
 p=re.sub(r"/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=/|$)","/{id}",p);p=re.sub(r"/\d{6,}(?=/|$)","/{id}",p);return re.sub(r"\{[^/]+\}","{id}",p)
def read_csv(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write_csv(p,fields,rows):
 with p.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

inventory=read_csv(ROOT/"api/inventory/interfaces.csv")
inv=defaultdict(list)
for x in inventory:
 if x.get("method") and x.get("path"):inv[(x["method"].upper(),canon(x["path"]))].append(x)

actions=read_csv(R/"fat-admin-explicit-actions.csv")
writes=[x for x in actions if x["risk"]=="WRITE_REQUIRES_CURRENT_RUN_DATA"]
flow=json.loads((R/"fat-admin-controlled-marquee-flow.json").read_text())
channel=json.loads((R/"fat-admin-controlled-channel-group-flow.json").read_text())
executed={"Add Marquee":"POST /admin/marquee/add","Edit":"POST /admin/marquee/update","Delete":"POST /admin/marquee/delete"}
create_words=re.compile(r"add|new|single new|batch addition|batch send|add staff|add ip",re.I)
write_status=[]
for x in writes:
 status="BLOCKED_DATA_SCOPE";reason="No current-run-created target with the required business state"
 if x["page_name"]=="Marquee Management" and x["action_name"] in executed:
  status="EXECUTED";reason="Current-run unique marquee was created, located, edited and deleted; exact numeric ID was over-redacted, unique marker retained"
 elif x["page_name"]=="Channel Management" and x["action_name"]=="Add":
  status="NO_CREATE_REQUEST";reason="Confirm produced no create request; delayed /admin/game/search events were excluded"
 elif create_words.search(x["action_name"]) or (x["page_name"]=="Material Management" and x["action_name"]=="Add"):
  status="BLOCKED_PREREQUISITE";reason="Creation form requires additional valid fields/assets/approval or lacks a proven cleanup path"
 write_status.append({"top_menu":x["top_menu"],"page_name":x["page_name"],"page_route":x["page_route"],"action_name":x["action_name"],"status":status,"target_reference":flow.get("test_marker","") if status=="EXECUTED" else channel.get("test_name","") if status=="NO_CREATE_REQUEST" else "","target_id":flow.get("target_id","") if status=="EXECUTED" else "","before_state":flow.get("before_state","") if status=="EXECUTED" else "","after_state":flow.get("after_state","") if status=="EXECUTED" else "","side_effect":"Created, updated, then deleted current-run marquee" if status=="EXECUTED" else "No proven side effect","evidence":"fat-admin-controlled-marquee-flow.json" if status=="EXECUTED" else "fat-admin-controlled-channel-group-flow.json" if status=="NO_CREATE_REQUEST" else "fat-admin-write-form-probes.json + explicit action inventory","reason":reason})
write_csv(R/"fat-admin-write-action-status.csv",["top_menu","page_name","page_route","action_name","status","target_reference","target_id","before_state","after_state","side_effect","evidence","reason"],write_status)

component=[R/"fat-admin-page-initialization-interface.csv",R/"fat-admin-explicit-read-action-interface.csv",R/"fat-admin-explicit-navigation-action-interface.csv",R/"fat-admin-explicit-filter-action-interface.csv",R/"fat-admin-explicit-reviewed-action-interface.csv"]
mapping=[]
for p in component:mapping.extend(read_csv(p))
for s in write_status:
 endpoints=[]
 if s["status"]=="EXECUTED":
  primary=executed[s["action_name"]];endpoints=[primary,"GET /admin/marquee/list"]
 if not endpoints:endpoints=[""]
 for endpoint in endpoints:
  method,path=(endpoint.split(" ",1) if endpoint else ("",""));doc=(inv.get((method,canon(path))) or [None])[0] if endpoint else None
  mapping.append({"surface":"admin","top_menu":s["top_menu"],"page_name":s["page_name"],"page_route":s["page_route"],"control_type":"button","action_name":s["action_name"],"method":method,"normalized_path":path,"query_fields":"page,page_size,ty" if path=="/admin/marquee/list" else "","path_fields":"","body_fields":"captured field names unavailable (request encoding)","header_fields":"browser session/runtime","parameter_source":"Current-run unique marquee form/row" if endpoint else "No request captured","http_status":"200" if endpoint else "","business_status":"True" if endpoint else "","response_structure":"object" if path.endswith("/list") else "string","auth_role":"FAT admin authenticated session; operation visible to current role","side_effect":s["side_effect"],"before_state":s["before_state"],"after_state":s["after_state"],"original_category":f"{doc['surface']}/{doc['module']}" if doc else "","original_name":doc.get("name","") if doc else "","original_source_file":doc.get("file","") if doc else "","classification":("ACTIVE" if doc else "UNDOCUMENTED_ACTIVE") if endpoint else "DOCUMENTED_UNVERIFIED","currently_used_by_ui":"YES" if endpoint else s["status"],"evidence":s["evidence"]+f"; write_status={s['status']}; target_ref={s['target_reference']}","anomaly":"Exact target numeric ID was over-redacted" if s["status"]=="EXECUTED" else "","blocked_scope":"" if endpoint else s["reason"]})
write_csv(R/"fat-admin-page-action-interface.csv",MAP_FIELDS,mapping)

events=[]
init=json.loads((R/"fat-admin-page-initialization.json").read_text());events+=init["network"]
for artifact,allowed in [("read",None),("navigation",None),("filter",{"input","select","filter_submit"}),("reviewed",None)]:
 x=json.loads((R/f"fat-admin-explicit-{artifact}-actions.json").read_text())
 events += [e for e in x["network"] if e.get("control_type") not in {"page_initialization","login"} and (allowed is None or e.get("control_type") in allowed)]
events += [e|{"page_route":"/operations/marquee-management","control_type":"button","action_name":e["action"]} for e in flow["network"] if e.get("action") in {"create","edit","delete"}]
groups=defaultdict(list)
for e in events:groups[(e["method"],canon(e["path"]))].append(e)
endpoint_rows=[]
for (method,path),es in sorted(groups.items()):
 docs=inv.get((method,path),[]);doc=docs[0] if docs else None;success=[e for e in es if 200<=int(e.get("http_status") or 0)<300 and e.get("business_status") is not False];failed=[e for e in es if e not in success]
 classification=("MISCLASSIFIED" if doc and doc.get("surface")!="admin" else "ACTIVE" if doc else "UNDOCUMENTED_ACTIVE") if success else "ACTIVE_FAILED"
 endpoint_rows.append({"method":method,"normalized_path":path,"classification":classification,"success_events":len(success),"failed_events":len(failed),"pages":" | ".join(sorted({e.get("page_route","") for e in es})),"actions":" | ".join(sorted({e.get("action_name","") for e in es})),"http_statuses":" | ".join(sorted({str(e.get("http_status")) for e in es})),"business_statuses":" | ".join(sorted({str(e.get("business_status")) for e in es})),"original_surface":doc.get("surface","") if doc else "","original_module":doc.get("module","") if doc else "","original_name":doc.get("name","") if doc else "","original_source_file":doc.get("file","") if doc else "","evidence":"valid stage 2/3 UI Network; see page-action mapping"})
write_csv(R/"fat-admin-endpoint-summary.csv",["method","normalized_path","classification","success_events","failed_events","pages","actions","http_statuses","business_statuses","original_surface","original_module","original_name","original_source_file","evidence"],endpoint_rows)

observed=set(groups);comparison=[];reachable={"POST /admin/login/auth","POST /admin/login","GET /admin/kyc/pending/count","GET /admin/kyc/config/info","POST /admin/kyc/list","POST /admin/finance/deposit/risk/list","POST /admin/finance/deposit/list","GET /admin/finance/transaction/types","POST /admin/finance/transaction/list","POST /admin/finance/withdraw/risk/audit/list","POST /admin/finance/withdraw/list","GET /admin/me/detail","GET /admin/priv/list","GET /admin/group/list","GET /admin/finance/payment/bank/list"}
for key,docs in sorted(inv.items()):
 admin=[x for x in docs if x.get("surface")=="admin"]
 if not admin:continue
 d=admin[0];status=next((x["classification"] for x in endpoint_rows if (x["method"],x["normalized_path"])==key),None)
 if not status:status="DOCUMENTED_REACHABLE" if f"{key[0]} {key[1]}" in reachable else "DOCUMENTED_UNVERIFIED"
 comparison.append({"method":key[0],"normalized_path":key[1],"classification":status,"documented_name":d.get("name",""),"module":d.get("module",""),"source_file":d.get("file",""),"ui_observed":"YES" if key in observed else "NO","note":"No STALE/REPLACED_BY decision without replacement or non-use evidence" if key not in observed else ""})
for e in endpoint_rows:
 docs=inv.get((e["method"],e["normalized_path"]),[])
 if e["classification"]=="MISCLASSIFIED":comparison.append({"method":e["method"],"normalized_path":e["normalized_path"],"classification":"MISCLASSIFIED","documented_name":e["original_name"],"module":e["original_module"],"source_file":e["original_source_file"],"ui_observed":"YES","note":f"Observed from admin UI but inventory surface is {e['original_surface']}"})
 elif not docs:comparison.append({"method":e["method"],"normalized_path":e["normalized_path"],"classification":"UNDOCUMENTED_ACTIVE","documented_name":"","module":"","source_file":"","ui_observed":"YES","note":"Observed in FAT UI; absent from inventory"})
write_csv(R/"fat-admin-inventory-comparison.csv",["method","normalized_path","classification","documented_name","module","source_file","ui_observed","note"],comparison)

summary={"generated_at":flow["captured_at"],"environment":"FAT","live_permission_roots":12,"live_menu_pages":57,"page_initialization":{"pages":57,"raw_events":844,"unique_method_paths":78,"errors":0},"explicit_actions":{"total":679,"non_write_attempted":615,"actual_interactions":197+91+106+31,"skipped":124+42+4+14,"errors":6,"write_total":64,"write_status":dict(Counter(x["status"] for x in write_status))},"controlled_write":{"target_reference":flow["test_marker"],"target_id":flow["target_id"],"before":flow["before_state"],"after":flow["after_state"],"cleanup":flow["cleanup"],"executed_actions":3,"note":"Numeric target ID was over-redacted; unique marker and row lifecycle retained"},"unique_endpoints":len(endpoint_rows),"endpoint_classification":dict(Counter(x["classification"] for x in endpoint_rows)),"endpoint_with_failures":sum(int(x["failed_events"])>0 for x in endpoint_rows),"page_action_rows":len(mapping),"inventory_comparison_rows":len(comparison),"invalidated_probe_excluded":True}
(R/"fat-admin-final-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
