import fs from "node:fs";
import path from "node:path";

export function loadEnv(file = process.env.ENV_FILE || ".env.fat") {
  const shell = { ...process.env };
  const values = {};
  const files = [file];
  if (shell.QA_ENV_LOCAL) files.push(shell.QA_ENV_LOCAL);
  for (const item of files) {
    const fullPath = path.resolve(process.cwd(), item);
    if (!fs.existsSync(fullPath)) {
      if (item === shell.QA_ENV_LOCAL) throw new Error('QA_ENV_LOCAL file missing; create the ignored personal file or unset QA_ENV_LOCAL.');
      continue;
    }
    for (const line of fs.readFileSync(fullPath, "utf8").split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
      const idx = trimmed.indexOf("=");
      values[trimmed.slice(0, idx).trim()] = trimmed.slice(idx + 1).trim().replace(/^['"]|['"]$/g, "");
    }
  }
  for (const [key, value] of Object.entries(values)) {
    if (shell.ENV_FILE_PRECEDENCE !== "shell" || !(key in shell)) process.env[key] = value;
  }
}

export function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}
