import fs from "node:fs";
import path from "node:path";

export function loadJson(relativePath) {
  const fullPath = path.resolve(process.cwd(), relativePath);
  return JSON.parse(fs.readFileSync(fullPath, "utf8"));
}
