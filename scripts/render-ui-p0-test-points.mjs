#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const source = path.resolve("ui/data/client-p0-test-points.json");
const out = path.resolve("ui/reports/client-ui-p0-test-points.md");
const data = JSON.parse(fs.readFileSync(source, "utf8"));

function cell(value = "") {
  return String(value || "").replace(/\|/g, "\\|");
}

const lines = [
  "# 客户端 P0 UI 测试点",
  "",
  "## 原则",
  "",
  ...data.principles.map((item) => `- ${item}`),
  "",
  "## 测试点",
  "",
  "| ID | 模块 | 类型 | 执行方式 | 测试点 | 路由 | 自动化状态 | Spec |",
  "|---|---|---|---|---|---|---|---|",
];

for (const item of data.testPoints) {
  lines.push(
    `| ${cell(item.id)} | ${cell(item.module)} | ${cell(item.type)} | ${cell(item.executionMode)} | ${cell(item.title)} | \`${cell(item.route)}\` | ${cell(item.automationStatus)} | ${cell(item.spec)} |`,
  );
}

lines.push("", "## 断言明细", "");
for (const item of data.testPoints) {
  lines.push(`### ${item.id} ${item.title}`, "");
  lines.push(`- 执行方式: ${item.executionMode || ""}`);
  lines.push(`- 自动化状态: ${item.automationStatus || ""}`);
  if (item.spec) lines.push(`- 对应用例: \`${item.spec}\``);
  for (const assertion of item.assertions) lines.push(`- ${assertion}`);
  lines.push("");
}

fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, lines.join("\n"));
console.log(`wrote ${out}`);
