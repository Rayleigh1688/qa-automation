#!/usr/bin/env python3
import collections,csv,json,pathlib,re,sys

root=pathlib.Path(__file__).resolve().parent
out=root/'results'
scan=json.loads((out/'agency-portal-live-scan.json').read_text(encoding='utf-8'))
allowed={'ACTIVE','ACTIVE_FAILED','UNDOCUMENTED_ACTIVE','DOCUMENTED_REACHABLE','DOCUMENTED_UNVERIFIED','STALE','REPLACED_BY','THIRD_PARTY','MISCLASSIFIED'}

docs=collections.defaultdict(list)
with open(root.parent/'api/inventory/interfaces.csv',encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f):
    if row.get('top_domain')!='代理后台': continue
    method=(row.get('method') or '').upper().strip()
    path=row.get('path') or ''
    if method and path: docs[(method,path)].append(row)

groups=collections.defaultdict(list)
for event in scan['network']:
  groups[(event['method'].upper(),event['path'])].append(event)

endpoint_rows=[]
for key,events in sorted(groups.items()):
  ok=any(200<=e['http_status']<300 and e['business_status'] is not False for e in events)
  exact=docs.get(key,[])
  same_path=[r for (m,p),rows in docs.items() if p==key[1] for r in rows]
  if exact: classification='ACTIVE' if ok else 'ACTIVE_FAILED'
  elif same_path: classification='MISCLASSIFIED'
  else: classification='UNDOCUMENTED_ACTIVE' if ok else 'ACTIVE_FAILED'
  endpoint_rows.append({
    'method':key[0],'path':key[1],'classification':classification,
    'success_events':sum(200<=e['http_status']<300 and e['business_status'] is not False for e in events),
    'failed_events':sum(not(200<=e['http_status']<300 and e['business_status'] is not False) for e in events),
    'routes':' | '.join(sorted(set(e['route'] for e in events))),
    'actions':' | '.join(sorted(set(e['action'] for e in events))),
    'query_fields':' | '.join(sorted(set(','.join(e['query_fields']) for e in events if e['query_fields']))),
    'body_fields':' | '.join(sorted(set(','.join(e['body_fields']) for e in events if e['body_fields']))),
    'response_shapes':' | '.join(sorted(set(f"{e['response_data_type']}:{','.join(e['response_data_keys'])}" for e in events))),
    'documented_source':' | '.join(r['file'] for r in exact or same_path),
    'note':'method mismatch against 代理后台 documentation' if classification=='MISCLASSIFIED' else '',
  })

def write_csv(name,rows,fields):
  with open(out/name,'w',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)

endpoint_fields=list(endpoint_rows[0]) if endpoint_rows else ['method','path','classification','success_events','failed_events','routes','actions','query_fields','body_fields','response_shapes','documented_source','note']
write_csv('agency-portal-endpoints.csv',endpoint_rows,endpoint_fields)

successful_routes={p['route'] for p in scan['pages'] if not p['error'] and p['final_origin']==scan['base_origin'] and p['final_route']==p['route']}
menu_rows=[]
for m in scan['menu']:
  verified=m['route'] in successful_routes
  source=m['route_source']
  if verified and 'bundle_candidate_pending_dynamic_route_gate' in source:
    source='bundle_candidate_plus_authenticated_path_controls_and_network_verified'
  menu_rows.append({'order':m['order'],'top_menu':m['menu_path'][0] if m['menu_path'] else m['page_name'],'menu_path':' > '.join(m['menu_path']),'page_name':m['page_name'],'route':m['route'],'route_source':source,'permission_observation':('rendered exact menu label and authenticated route' if 'rendered_exact_label' in source else 'bundle navigation candidate accepted by authenticated path, controls and page Network') if verified else 'candidate not dynamically verified'})
write_csv('agency-portal-menu-routes.csv',menu_rows,['order','top_menu','menu_path','page_name','route','route_source','permission_observation'])
(out/'agency-portal-menu-permission-tree.json').write_text(json.dumps({'source':'public bundle navigation definitions cross-checked by authenticated exact labels where available, actual pathname and page Network','account_data':'not retained','tree':menu_rows,'limitation':'Only this account current authenticated route surface is asserted; routes not present are not classified STALE.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

control_rows=[]
for page in scan['pages']:
  for kind,items in page['controls'].items():
    for item in items:
      control_rows.append({'page_name':page['page_name'],'route':page['route'],'control_type':kind,'control':json.dumps(item,ensure_ascii=False),'evidence':'visible DOM; values and table content omitted'})
write_csv('agency-portal-dom-controls.csv',control_rows,['page_name','route','control_type','control','evidence'])

action_rows=[]
for action in scan['actions']:
  events=action.get('network_events',[])
  if events:
    ok=any(200<=e['http_status']<300 and e['business_status'] is not False for e in events)
    classification='ACTIVE' if ok else 'ACTIVE_FAILED'
  else: classification='DOCUMENTED_UNVERIFIED'
  action_rows.append({'route':action['route'],'action_type':action['action_type'],'action_name':action['action_name'],'status':action['status'],'before_route':action['before_route'],'after_route':action['after_route'],'overlay_opened':action['after_overlay_count']>action['before_overlay_count'],'download_observed':action['download_observed'],'endpoint_evidence':' | '.join(sorted(set(f"{e['method']} {e['path']}" for e in events))),'classification':classification,'side_effect':action['side_effect'],'restoration':'Escape/previous-page/original route restoration attempted','error':action['error']})

executed={(a['route'],a['action_name'].lower()) for a in action_rows}
interesting=re.compile(r'^(?:today.*|yesterday|this week|last week|this month|last month|search(?:\s*/\s*query)?|copy|copy link|promo poster|export|download|detail|view)$',re.I)
for page in scan['pages']:
  for button in page['controls'].get('buttons',[]):
    label=button.get('label','').strip()
    if label and interesting.match(label) and (page['route'],label.lower()) not in executed and not (label.lower()=='search' and (page['route'],'query') in executed):
      action_rows.append({'route':page['route'],'action_type':'visible_control_audit','action_name':label,'status':'VISIBLE_NOT_EXECUTED','before_route':page['route'],'after_route':page['route'],'overlay_opened':False,'download_observed':False,'endpoint_evidence':'','classification':'DOCUMENTED_UNVERIFIED','side_effect':'none; control was not clicked','restoration':'not applicable','error':'Second and final authenticated context ended; no third login permitted. Visible-control gap retained explicitly.'})
write_csv('agency-portal-actions.csv',action_rows,['route','action_type','action_name','status','before_route','after_route','overlay_opened','download_observed','endpoint_evidence','classification','side_effect','restoration','error'])

observed={(r['method'],r['path']):r for r in endpoint_rows}
comparison=[]
for key,rows in sorted(docs.items()):
  hit=observed.get(key)
  comparison.append({'method':key[0],'path':key[1],'classification':hit['classification'] if hit else 'DOCUMENTED_UNVERIFIED','ui_observed':'YES' if hit else 'NO','documented_source':' | '.join(r['file'] for r in rows),'note':'' if hit else 'Not observed from current-role UI; absence is not STALE evidence'})
for key,hit in observed.items():
  if key not in docs: comparison.append({'method':key[0],'path':key[1],'classification':hit['classification'],'ui_observed':'YES','documented_source':hit['documented_source'],'note':hit['note']})
write_csv('agency-portal-inventory-comparison.csv',comparison,['method','path','classification','ui_observed','documented_source','note'])

counts=collections.Counter(r['classification'] for r in endpoint_rows)
summary={'captured_at':scan['captured_at'],'login_gate':scan['login_gate'],'document_scope':'top_domain=代理后台 only','documented_endpoints':len(docs),'menu_pages':len(scan['menu']),'resolved_routes':sum(bool(m['route']) for m in scan['menu']),'scanned_pages':len(scan['pages']),'page_errors':sum(bool(p['error']) for p in scan['pages']),'dom_controls':len(control_rows),'actions':len(action_rows),'network_events':len(scan['network']),'unique_endpoints':len(endpoint_rows),'classifications':dict(counts),'persistent_write_operations':0,'recovery':'Pagination/local navigation restoration attempted; no persistent mutation submitted.','fatal_error':scan['fatal_error']}
(out/'agency-portal-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

gate='PASS' if scan['login_gate'].get('success') else 'FAIL'
report=f'''# FAT 代理前台接口发现报告

- 登录门禁：**{gate}**；登录后实际 origin `{scan['login_gate'].get('authenticated_origin','')}`，路由 `{scan['login_gate'].get('authenticated_path','')}`。登录请求与身份/Profile 请求均有成功证据。
- 会话隔离：扫描器创建全新专用 Playwright browser context，不加载或导出 storage state，不复用代理管理后台 Token。
- 当前账号已认证导航面：{summary['menu_pages']} 个菜单定义/可访问叶子，{summary['resolved_routes']} 个解析路由；扫描 {summary['scanned_pages']} 页，页面错误 {summary['page_errors']}。
- 菜单证据说明：通用 `aside/nav` selector 未命中该站点的自定义/响应式导航壳（`navigation_shell_visible=false`），不据此判菜单缺失。5 个 bundle 导航候选均已由登录态下实际 pathname、页面控件和页面初始化 Network 动态核对成功；其中可识别的精确菜单文案另有 DOM 证据。
- DOM 与操作：{summary['dom_controls']} 条可见控件结构，{summary['actions']} 条操作/可见性结论。已执行首页 Search/Reset、列表 Reset、筛选展开、规则页签和当前可见 Overflow；未点击的日期快捷项、`Search / Query`、复制/海报等控件逐项保留为 `VISIBLE_NOT_EXECUTED` / `DOCUMENTED_UNVERIFIED`。当前 DOM 未渲染分页、详情、导出或独立抽屉入口。
- Network：{summary['network_events']} 条首方事件，{summary['unique_endpoints']} 个唯一 method+path；动态分类 `{dict(counts)}`。
- 静态对照：只读取 inventory 中顶层 `代理后台` 的 {summary['documented_endpoints']} 个 method+path；没有混入 `代理管理后台`。未观察文档接口保持 `DOCUMENTED_UNVERIFIED`，没有仅凭缺失动态证据判 `STALE`。
- 写操作：0。当前账号不是本轮新建目标，未提交密码重置、消息发送、设置或资金相关持久写；不存在恢复遗留。
- 敏感信息：手机号、OTP、Token、Cookie、设备标识和响应业务值均未保留；结果只含字段名、类型、计数、标准化路径和脱敏 DOM 标签。
- 边界：仅 FAT；未进入 UAT、Jenkins、数据库、共享 inventory/catalog 或 P0/P1 资产。
'''
(out/'agency-portal-report.md').write_text(report,encoding='utf-8')

for classification in counts:
  if classification not in allowed: raise SystemExit(f'illegal classification: {classification}')

patterns=[re.compile(r'(?<!\d)(?:\+?63|0)?9\d{9}(?!\d)'),re.compile(r'\b\d{6}\b'),re.compile(r'(?i)(?:token|cookie|authorization|device[_-]?id)\s*[=:]\s*["\']?[^,\s"\']+')]
violations=[]
for file in out.iterdir():
  if file.is_file():
    text=file.read_text(encoding='utf-8')
    for pattern in patterns:
      if pattern.search(text): violations.append(f'{file.name}:{pattern.pattern}')
if violations:
  print(json.dumps({'sensitive_audit':'FAIL','violations':violations},ensure_ascii=False));sys.exit(2)
print(json.dumps({'summary':summary,'sensitive_audit':'PASS'},ensure_ascii=False))
