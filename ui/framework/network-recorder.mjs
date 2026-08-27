function redactHeaders(headers) {
  const out = {};
  for (const [key, value] of Object.entries(headers || {})) {
    out[key] = /^(t|authorization|cookie)$/i.test(key) ? "<redacted>" : String(value).slice(0, 200);
  }
  return out;
}

function redactUrl(url) {
  return String(url).replace(/([?&](?:token|t|password|otp|code)=)[^&]+/gi, "$1<redacted>");
}

function redactBody(body) {
  if (!body) return "";
  return String(body)
    .replace(/(["'](?:password|otp|code|token|t)["']\s*:\s*)"?[^",&\s}]+/gi, "$1<redacted>")
    .replace(/((?:password|otp|code|token|t)=)[^&\s]+/gi, "$1<redacted>")
    .slice(0, 1200);
}

export function attachNetworkRecorder(page, { hostPattern = /filbet2025\.com/ } = {}) {
  const records = [];

  page.on("request", (request) => {
    const url = request.url();
    if (!hostPattern.test(url)) return;
    records.push({
      kind: "request",
      method: request.method(),
      url: redactUrl(url),
      resourceType: request.resourceType(),
      headers: redactHeaders(request.headers()),
      postData: redactBody(request.postData()),
      ts: Date.now(),
    });
  });

  page.on("response", async (response) => {
    const url = response.url();
    if (!hostPattern.test(url)) return;
    const headers = response.headers();
    let body = "";
    if (/json|text|cbor|octet-stream/i.test(headers["content-type"] || "")) {
      body = await response.text().catch(() => "");
    }
    records.push({
      kind: "response",
      method: response.request().method(),
      url: redactUrl(url),
      status: response.status(),
      headers: redactHeaders(headers),
      body: redactBody(body),
      ts: Date.now(),
    });
  });

  return records;
}
