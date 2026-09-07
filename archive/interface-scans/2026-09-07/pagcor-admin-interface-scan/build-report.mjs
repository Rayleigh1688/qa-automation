import fs from "node:fs";
import path from "node:path";

const dir = path.resolve("pagcor-admin-interface-scan/results");
const data = JSON.parse(fs.readFileSync(path.join(dir, "pagcor-admin-live-scan.json"), "utf8"));
const csv = (rows, fields) => [fields, ...rows.map((r) => fields.map((f) => r[f] ?? ""))]
  .map((row) => row.map((v) => `"${String(Array.isArray(v) ? v.join(" | ") : v).replaceAll('"', '""')}"`).join(",")).join("\n") + "\n";

fs.writeFileSync(path.join(dir, "pagcor-admin-endpoints.csv"), csv(data.endpoints.map((x) => ({ ...x, pages: x.pages || [] })), [
  "method", "path", "classification", "documented_match", "event_count", "success_count", "failed_count", "pages", "evidence", "note",
]));
fs.writeFileSync(path.join(dir, "pagcor-admin-actions.csv"), csv(data.actions.map((x) => ({
  page_route: x.page_route, label: x.label, control_type: x.control_type, result: x.result,
  option_count: x.option_count ?? "", selected: x.selected ?? "", request_count: x.request_count,
})), ["page_route", "label", "control_type", "result", "option_count", "selected", "request_count"]));

const dynamic = data.endpoints.filter((x) => x.event_count > 0);
const classes = Object.fromEntries([...new Set(data.endpoints.map((x) => x.classification))].sort().map((c) => [c, data.endpoints.filter((x) => x.classification === c).length]));
const page = data.pages[0];
const report = `# FAT PAGCOR compliance admin scan report

- Login gate: **PASS**. Actual origin \`${data.gate.actual_origin}\`; authenticated hash route \`${data.gate.initial_post_login_route}\`.
- Evidence: successful \`POST /cmpl/login\`, successful \`GET /cmpl/me/detail\`, authenticated business-page initialization, and rendered navigation.
- Session isolation: a fresh PAGCOR-only Playwright context was used; storage state was not exported and the token remained in memory only.
- Navigation: one rendered top-navigation entry (报表中心 → \`/#/reportCenter/pagcor\`). This application has no traditional sidebar menu items; none are claimed as verified.
- Permission tree: ${data.permission_tree.queried_pid_count} PIDs queried, ${data.permission_tree.responses.filter((x) => x.business_status === true).length}/${data.permission_tree.responses.length} successful responses, ${data.permission_tree.responses.reduce((n, x) => n + x.item_count, 0)} returned permission nodes. \`GET /cmpl/priv/list\` is \`DOCUMENTED_REACHABLE\`, not UI-active.
- Page coverage: ${data.pages.length}/1 rendered route; ${Object.values(page.controls).reduce((n, x) => n + x.length, 0)} DOM control/table snapshots; ${data.actions.length} safe actions; ${data.network.length} first-party Network events.
- Dynamic endpoints: ${dynamic.length} unique, all ${dynamic.every((x) => x.classification === "ACTIVE") ? "ACTIVE" : "mixed"}. Static comparison: ${Object.entries(classes).map(([k, v]) => `${k} ${v}`).join(", ")}.
- Filters/query: five visible selectors each selected its first legal option; Search, Today, Yesterday, This Week, This Month, Last Month, Reset, and a final Search were exercised. Date before/after values are retained as non-personal state evidence.
- Export: clicked once; no Network or download event occurred, so the action is \`CLICKED_NO_INTERFACE_EVIDENCE\`. No file was saved.
- Not visible in the current DOM: second page, detail entry, modal, drawer, and Overflow. These are not reported as failed or stale.
- Persistent writes: 0. No current-run-owned target or real-time business TOTP was available; fixed login codes were not used for business operations.
- Privacy audit: credentials, token, cookies, OTP/TOTP, device ID, response rows, and raw personal data are not serialized.

Unobserved documented endpoints remain \`DOCUMENTED_UNVERIFIED\`; absence is not treated as \`STALE\`.
`;
fs.writeFileSync(path.join(dir, "pagcor-admin-report.md"), report);
console.log(`[report] endpoints=${data.endpoints.length} actions=${data.actions.length} dynamic=${dynamic.length}`);
