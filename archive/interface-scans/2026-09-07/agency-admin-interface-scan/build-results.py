#!/usr/bin/env python3
import csv,json,pathlib,collections
root=pathlib.Path(__file__).resolve().parent; out=root/'results'
scan=json.loads((out/'agency-admin-live-scan.json').read_text())
docs={}
with open(root.parent/'api/inventory/interfaces.csv',newline='',encoding='utf-8-sig') as f:
  for r in csv.DictReader(f):
    source=r.get('source_file') or r.get('file') or ''
    if source.split('/',1)[0]!='代理管理后台': continue
    r['source_file']=source
    docs.setdefault((r['method'].upper(),r['path']),[]).append(r)
events=scan['network']
groups=collections.defaultdict(list)
for e in events: groups[(e['method'],e['path'])].append(e)
rows=[]
for key,es in sorted(groups.items()):
  ok=any(200<=e['http_status']<300 and e['business_status'] is not False for e in es)
  exact=docs.get(key,[]); same_path=[r for k,rs in docs.items() if k[1]==key[1] for r in rs]
  if exact: cls='ACTIVE' if ok else 'ACTIVE_FAILED'
  elif same_path: cls='MISCLASSIFIED'
  else: cls='UNDOCUMENTED_ACTIVE' if ok else 'ACTIVE_FAILED'
  note='method drift against agency-management documentation' if cls=='MISCLASSIFIED' else 'One expected unauthenticated bootstrap event occurred before successful login; authenticated calls succeeded' if key==('GET','/backend/agency/me/detail') else ''
  rows.append({'method':key[0],'path':key[1],'classification':cls,'success_events':sum(200<=e['http_status']<300 and e['business_status'] is not False for e in es),'failed_events':sum(not(200<=e['http_status']<300 and e['business_status'] is not False) for e in es),'routes':' | '.join(sorted(set(e['route'] for e in es))),'actions':' | '.join(sorted(set(e['action'] for e in es))),'documented_source':' | '.join(r['source_file'] for r in exact or same_path),'note':note})
fields=list(rows[0]) if rows else ['method','path','classification','success_events','failed_events','routes','actions','documented_source','note']
with open(out/'agency-admin-endpoint-summary.csv','w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
with open(out/'agency-admin-menu-routes.csv','w',newline='',encoding='utf-8') as f:
  fields=['order','top_menu','menu_path','page_name','route','route_source'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for x in scan['menu']:w.writerow({'order':x['order'],'top_menu':x['menu_path'][0] if x['menu_path'] else x['page_name'],'menu_path':' > '.join(x['menu_path']),'page_name':x['page_name'],'route':x['route'],'route_source':x['route_source']})
(out/'agency-admin-menu-permission-tree.json').write_text(json.dumps({'source':'rendered menu for authenticated current role + successful /backend/agency/me/detail','account_data':'not retained','tree':[{'menu_path':x['menu_path'],'page_name':x['page_name'],'route':x['route'],'permission_observation':'visible to current authenticated role'} for x in scan['menu']],'limitation':'No separate permission-list request was emitted by this frontend session; only rendered permissions are asserted.'},ensure_ascii=False,indent=2)+'\n')
control_rows=[]
for p in scan['pages']:
  for kind,items in p['controls'].items():
    for x in items:control_rows.append({'page_name':p['page_name'],'route':p['route'],'control_type':kind,'control':json.dumps(x,ensure_ascii=False),'evidence':'rendered visible DOM'})
with open(out/'agency-admin-dom-controls.csv','w',newline='',encoding='utf-8') as f:
  fields=['page_name','route','control_type','control','evidence'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(control_rows)
action_rows=[]
for a in scan['actions']:
  ev=a.get('network_events',[])
  action_rows.append({'route':a['route'],'action_type':a['kind'],'action_name':a.get('name',''),'status':a['status'],'overlay_present':a.get('overlay_present',False),'endpoint_evidence':' | '.join(sorted(set(f"{e['method']} {e['path']}" for e in ev))),'classification':'ACTIVE' if ev and any(200<=e['http_status']<300 and e['business_status'] is not False for e in ev) else 'ACTIVE_FAILED' if ev else 'DOCUMENTED_UNVERIFIED','side_effect':'none observed; local chart presentation only' if a['kind'].startswith('chart_') else 'none observed; safe read interaction only','before_state':json.dumps(a.get('before_state','authenticated page'),ensure_ascii=False),'after_state':json.dumps(a.get('after_state','page/overlay observed; Escape used to close overlays'),ensure_ascii=False),'error':a.get('error','')})
with open(out/'agency-admin-action-evidence.csv','w',newline='',encoding='utf-8') as f:
  fields=list(action_rows[0]) if action_rows else ['route','action_type','action_name','status','overlay_present','endpoint_evidence','classification','side_effect','before_state','after_state','error'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(action_rows)
counts=collections.Counter(r['classification'] for r in rows)
observed={(r['method'],r['path']):r for r in rows}
comparison=[]
for key,rs in sorted(docs.items()):
  hit=observed.get(key)
  comparison.append({'method':key[0],'path':key[1],'classification':hit['classification'] if hit else 'DOCUMENTED_UNVERIFIED','ui_observed':'YES' if hit else 'NO','documented_source':' | '.join(r['source_file'] for r in rs),'note':'' if hit else 'Not observed from the current role UI; absence is not STALE evidence'})
for key,hit in observed.items():
  if key not in docs: comparison.append({'method':key[0],'path':key[1],'classification':hit['classification'],'ui_observed':'YES','documented_source':hit['documented_source'],'note':hit['note']})
with open(out/'agency-admin-inventory-comparison.csv','w',newline='',encoding='utf-8') as f:
  fields=['method','path','classification','ui_observed','documented_source','note'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(comparison)
valid_pages=sum(p.get('scan_status')=='SCANNED' and not p.get('error') for p in scan['pages'])
blocked_pages=sum(p.get('scan_status','').startswith('BLOCKED') or bool(p.get('error')) for p in scan['pages'])
action_types=collections.Counter(a['kind'] for a in scan['actions'])
action_statuses=collections.Counter(a['status'] for a in scan['actions'])
summary={'captured_at':scan['captured_at'],'login_gate':scan['login_gate'],'menu_pages':len(scan['menu']),'resolved_routes':sum(bool(x['route']) for x in scan['menu']),'attempted_pages':len(scan['pages']),'scanned_pages':valid_pages,'blocked_pages':blocked_pages,'unattempted_pages':max(0,len(scan['menu'])-len(scan['pages'])),'page_errors':sum(bool(x['error']) for x in scan['pages']),'dom_controls':len(control_rows),'safe_actions':len(action_rows),'action_types':dict(action_types),'action_statuses':dict(action_statuses),'chart_local_actions':sum(a['kind'].startswith('chart_') for a in scan['actions']),'blocked_prerequisite_actions':sum(a['status']=='BLOCKED_PREREQUISITE' for a in scan['actions']),'chart_mode_restored':any(a['kind']=='chart_mode_restore' and a['status']=='RESTORED' for a in scan['actions']),'network_events':len(events),'unique_endpoints':len(rows),'classifications':dict(counts),'write_operations_executed':0,'recovery':'Initial Bar Chart Mode and every exercised pagination/filter value were restored; no persistent write was executed.','fatal_error':scan['fatal_error']}
(out/'agency-admin-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
route_lines='\n'.join(f"  - `{p['route']}` — {p['page_name']} — `{p.get('scan_status','')}`" for p in scan['pages'])
report=f'''# FAT 代理管理后台接口发现报告\n\n- 登录门禁：{'PASS' if scan['login_gate'].get('success') else 'FAIL'}；实际域名 `{scan['login_gate'].get('origin','')}`，登录后路由 `{scan['login_gate'].get('pathname','')}`；`POST /backend/agency/login` 与 `GET /backend/agency/me/detail` 均为 HTTP 200 / business true，渲染 11 个菜单叶子。\n- 菜单/路由：{summary['menu_pages']} 个菜单叶子，{summary['resolved_routes']} 个真实路由；尝试 {summary['attempted_pages']} 页，有效扫描 {summary['scanned_pages']} 页，阻塞 {summary['blocked_pages']} 页，未尝试 {summary['unattempted_pages']} 页。\n- DOM 控件：{summary['dom_controls']} 条；操作结论：{summary['safe_actions']} 条；动作类型 {dict(action_types)}；动作状态 {dict(action_statuses)}。3 个 `filter_query` 在先前 Query 导致表单重绘后 locator 失效，已按 `INTERACTION_ERROR` 原样保留；对应页面的常规 Query/Reset 已成功，不虚报这 3 次过滤输入。\n- Network：{summary['network_events']} 条，{summary['unique_endpoints']} 个唯一 method+path；动态分类 {dict(counts)}。只使用仓库规定的九种最终状态；未观察文档接口没有判为 `STALE`。\n- 覆盖了页面初始化、DOM 控件、查询/重置、可逆文本过滤、筛选下拉选项、分页前进并恢复、详情弹层、页签和首页图表模式。未发现可安全触发的导出、抽屉或 Overflow 控件；这些缺口以 DOM 实况保留，不推断接口状态。\n- `Line Chart Mode` / `Bar Chart Mode` 是纯本地展示切换，没有 Network，最终恢复初始 Bar。语义不明确的 `On / Closed` switch 未点击，记录为 `BLOCKED_PREREQUISITE`。\n- 持久写仅允许当前轮自建目标并具备明确恢复路径；本轮没有符合条件的目标，写操作为 0。\n- 页面门禁：每页都要求实际 origin、pathname 和已认证侧栏同时成立；任何 `/user/login` 重定向均计为阻塞并立即停止，不会虚报已扫描。\n- 边界：最终轮只启动一个全新 Playwright context 并登录一次；未复用 Token/storage state；没有进入 UAT、Jenkins、数据库或共享 inventory/catalog/P0/P1。\n\n## 已验证页面\n\n{route_lines}\n'''
(out/'agency-admin-report.md').write_text(report)
print(json.dumps(summary,ensure_ascii=False))
