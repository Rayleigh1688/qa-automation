const SECRET_HEADER_RE = /^(t|authorization|cookie|set-cookie|x-auth|x-token)$/i;
const SECRET_PARAM_RE = /^(token|t|password|pwd|otp|code|auth|authorization|session|session_id|player_id|uid|phone|mobile)$/i;
const BUSINESS_PATH_RE = /\/(member|finance|game|wallet|withdraw|deposit|bonus|activity|kyc|bank|pay|order|record|report|balance|transaction|bet|launch|enter|process)\b/i;

function redactHeaders(headers) {
  const out = {};
  for (const [key, value] of Object.entries(headers || {})) {
    out[key] = SECRET_HEADER_RE.test(key) ? "<redacted>" : String(value).slice(0, 200);
  }
  return out;
}

function redactUrl(url) {
  try {
    const parsed = new URL(String(url));
    for (const key of Array.from(parsed.searchParams.keys())) {
      if (SECRET_PARAM_RE.test(key)) parsed.searchParams.set(key, "<redacted>");
    }
    return parsed.toString();
  } catch {
    return String(url).replace(/([?&](?:token|t|password|otp|code|phone|mobile)=)[^&]+/gi, "$1<redacted>");
  }
}

function redactBody(body) {
  if (!body) return "";
  return String(body)
    .replace(/(["'](?:password|pwd|otp|code|token|t|phone|mobile|authorization|session|session_id)["']\s*:\s*)"?[^",&\s}]+/gi, "$1<redacted>")
    .replace(/((?:password|pwd|otp|code|token|t|phone|mobile|authorization|session|session_id)=)[^&\s]+/gi, "$1<redacted>")
    .replace(/((?:phone|mobile|country_code)[A-Za-z]?)[0-9]{2,16}/gi, "$1<redacted>")
    .slice(0, 1200);
}

function safeUrlParts(value) {
  try {
    const url = new URL(value);
    return {
      origin: url.origin,
      path: url.pathname,
      queryKeys: Array.from(url.searchParams.keys()).sort(),
    };
  } catch {
    return { origin: "", path: String(value).split("?")[0], queryKeys: [] };
  }
}

function bodyFieldNames(body = "") {
  const text = String(body || "");
  if (!text) return [];
  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return Object.keys(parsed).sort();
  } catch {}

  const fields = new Set();
  for (const match of text.matchAll(/(?:^|[&{,\s"])([A-Za-z0-9_]{2,40})(?=["']?\s*[:=])/g)) {
    fields.add(match[1]);
  }
  return Array.from(fields).sort().slice(0, 40);
}

function responseFieldNames(body = "") {
  const text = String(body || "");
  if (!text) return [];
  try {
    const parsed = JSON.parse(text);
    const data = parsed?.data && typeof parsed.data === "object" ? parsed.data : parsed;
    if (data && typeof data === "object" && !Array.isArray(data)) return Object.keys(data).sort().slice(0, 40);
  } catch {}
  return [];
}

export function attachNetworkRecorder(target, { hostPattern = /filbet2025\.com/ } = {}) {
  const records = [];
  const eventSource = typeof target.context === "function" ? target.context() : target;

  eventSource.on("request", (request) => {
    const url = request.url();
    if (!hostPattern.test(url)) return;
    const safeUrl = redactUrl(url);
    const urlParts = safeUrlParts(safeUrl);
    records.push({
      kind: "request",
      method: request.method(),
      url: safeUrl,
      origin: urlParts.origin,
      path: urlParts.path,
      queryKeys: urlParts.queryKeys,
      resourceType: request.resourceType(),
      headers: redactHeaders(request.headers()),
      postData: redactBody(request.postData()),
      postDataFields: bodyFieldNames(redactBody(request.postData())),
      isBusinessCandidate: BUSINESS_PATH_RE.test(urlParts.path),
      ts: Date.now(),
    });
  });

  eventSource.on("response", async (response) => {
    const url = response.url();
    if (!hostPattern.test(url)) return;
    const headers = response.headers();
    let body = "";
    if (/json|text|cbor|octet-stream/i.test(headers["content-type"] || "")) {
      body = await response.text().catch(() => "");
    }
    const safeUrl = redactUrl(url);
    const urlParts = safeUrlParts(safeUrl);
    records.push({
      kind: "response",
      method: response.request().method(),
      url: safeUrl,
      origin: urlParts.origin,
      path: urlParts.path,
      queryKeys: urlParts.queryKeys,
      status: response.status(),
      headers: redactHeaders(headers),
      body: redactBody(body),
      responseFields: responseFieldNames(redactBody(body)),
      isBusinessCandidate: BUSINESS_PATH_RE.test(urlParts.path),
      ts: Date.now(),
    });
  });

  return records;
}

export function summarizeNetworkRecords(records, { maxRows = 160 } = {}) {
  const byEndpoint = new Map();
  for (const record of records || []) {
    if (!record.isBusinessCandidate) continue;
    const key = `${record.method || ""} ${record.origin || ""}${record.path || ""}`;
    const current = byEndpoint.get(key) || {
      method: record.method || "",
      origin: record.origin || "",
      path: record.path || "",
      queryKeys: new Set(),
      postDataFields: new Set(),
      responseFields: new Set(),
      statuses: new Set(),
      requestCount: 0,
      responseCount: 0,
      firstTs: record.ts,
      lastTs: record.ts,
    };

    for (const item of record.queryKeys || []) current.queryKeys.add(item);
    for (const item of record.postDataFields || []) current.postDataFields.add(item);
    for (const item of record.responseFields || []) current.responseFields.add(item);
    if (record.status) current.statuses.add(record.status);
    if (record.kind === "request") current.requestCount += 1;
    if (record.kind === "response") current.responseCount += 1;
    current.firstTs = Math.min(current.firstTs, record.ts);
    current.lastTs = Math.max(current.lastTs, record.ts);
    byEndpoint.set(key, current);
  }

  return Array.from(byEndpoint.values())
    .sort((a, b) => a.firstTs - b.firstTs)
    .slice(0, maxRows)
    .map((item) => ({
      ...item,
      queryKeys: Array.from(item.queryKeys).sort(),
      postDataFields: Array.from(item.postDataFields).sort(),
      responseFields: Array.from(item.responseFields).sort(),
      statuses: Array.from(item.statuses).sort((a, b) => a - b),
    }));
}
