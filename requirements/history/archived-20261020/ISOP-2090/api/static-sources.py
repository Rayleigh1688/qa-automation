#!/usr/bin/env python3
"""Bounded, unauthenticated download of public FAT frontend static assets."""
from __future__ import annotations

import argparse
from datetime import datetime
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import ssl
import sys
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPSHandler, build_opener, Request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "scripts"))
from filbet.requirement_session import NoRedirect
from qa_core.output_paths import repository_output_path
ORIGINS = {"admin": "https://admin-fat.filbet2025.com",
           "client": "https://client-fat.filbet2025.com"}
ORIGIN = ORIGINS["admin"]
DEFAULT_OUT = ROOT / "reports/qa/ISOP-2090/20261012-full/evidence/source"


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.urls.append(values["src"])
        if tag == "link" and values.get("rel") == "modulepreload" and values.get("href"):
            self.urls.append(values["href"])


def static_url(value, base=ORIGIN + "/", origin=ORIGIN):
    anchor = origin + "/"
    if urlsplit(base).netloc == "pwa.filbet.com":
        anchor = "https://pwa.filbet.com/filbet/dev/v20260129/"
    url = urljoin(anchor if value.startswith(("assets/", "modules/")) else base, value)
    parsed = urlsplit(url)
    client_cdn = (origin == ORIGINS["client"] and parsed.netloc == "pwa.filbet.com"
                  and parsed.path.startswith(("/filbet/dev/v20260129/assets/", "/filbet/dev/v20260129/modules/"))
                  and parsed.path.endswith(".js"))
    if parsed.scheme != "https" or (parsed.netloc != urlsplit(origin).netloc and not client_cdn):
        return None
    if parsed.query or parsed.fragment or parsed.username:
        return None
    if parsed.path != "/" and not client_cdn and not (parsed.path.startswith(("/assets/", "/_nuxt/")) and parsed.path.endswith(".js")):
        return None
    return url


def save_private(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)


def references(text, base, origin=ORIGIN):
    found = []
    for value in re.findall(r"[\"']((?:https://[A-Za-z0-9.-]+)?[A-Za-z0-9_./-]+\.js)[\"']", text):
        url = static_url(value, base, origin)
        if url:
            found.append(url)
    return sorted(set(found))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--service", choices=tuple(ORIGINS), default="admin")
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--out", type=lambda value: repository_output_path(value, ROOT), default=str(DEFAULT_OUT))
    parser.add_argument("--max-assets", type=int, default=12)
    parser.add_argument("--asset", action="append", default=[],
                        help="explicit public static URL/path, verified against origin/path allowlist")
    args = parser.parse_args()
    origin = ORIGINS[args.service]
    if args.max_assets < 1 or args.max_assets > 40:
        parser.error("max-assets must be between 1 and 40")
    if not args.execute:
        print(json.dumps({"origin": origin, "authenticated": False,
                          "allowed": ["/", "/assets/*.js"], "max_assets": args.max_assets}))
        return 0
    context = ssl._create_unverified_context() if args.insecure else ssl.create_default_context()
    opener = build_opener(NoRedirect(), HTTPSHandler(context=context))
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(ZoneInfo("Asia/Manila")).strftime("%Y%m%dT%H%M%S%f")
    manifest = {"origin": origin, "authenticated": False, "assets": [], "unfetched": []}
    queued = [static_url(value, origin + "/", origin) for value in args.asset] if args.asset else [origin + "/"]
    if any(value is None for value in queued):
        parser.error("explicit asset must be a public /assets/*.js URL on FAT origin")
    seen = set()
    limit = args.max_assets + (0 if args.asset else 1)
    while queued and len(manifest["assets"]) < limit:
        url = queued.pop(0)
        if url in seen:
            continue
        seen.add(url)
        with opener.open(Request(url, headers={"accept": "text/html,application/javascript"}), timeout=20) as response:
            if static_url(response.url, origin + "/", origin) != url:
                raise ValueError("unexpected static-asset redirect")
            content = response.read(12 * 1024 * 1024 + 1)
            if len(content) > 12 * 1024 * 1024:
                raise ValueError("static asset exceeds bounded size")
            status = response.code
            content_type = response.headers.get("content-type", "")
        text = content.decode("utf-8", errors="replace")
        basename = Path(urlsplit(url).path).name or "index.html"
        target = args.out / (stamp + "-" + basename)
        save_private(target, content)
        valid_source = not (url.endswith(".js") and "html" in content_type.lower())
        refs = references(text, url, origin) if valid_source else []
        if url.endswith("/"):
            html = Assets()
            html.feed(text)
            refs.extend(filter(None, (static_url(value, url, origin) for value in html.urls)))
        manifest["assets"].append({"url": url, "http": status, "bytes": len(content),
                                   "content_type": content_type, "valid_source": valid_source,
                                   "file": str(target.relative_to(ROOT)), "references": sorted(set(refs))})
        # Prioritise application chunks over framework/vendor dependencies.
        refs = sorted(set(refs), key=lambda item: ("legacy" in item.lower(), not bool(re.search(r"activity|promo|loss|rebate|index", item, re.I)), item))
        queued.extend(item for item in refs if item not in seen and item not in queued)
    manifest["unfetched"] = queued
    target = args.out / (stamp + "-manifest.json")
    save_private(target, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"assets": len(manifest["assets"]), "unfetched": len(queued),
                      "manifest": str(target.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"error_type": type(error).__name__,
                          "error": str(error)[:400], "authenticated": False}))
        raise SystemExit(1)
