#!/usr/bin/env python3
"""
PARSER.PY — Live Endpoint Discovery Engine
Features:
- Live HTTP/HTTPS endpoint discovery
- Concurrent requests with bounded workers
- Progressive terminal output
- HTTP status and content-type detection
- Redirect identification
- Redacted sensitive-content indicators
- TLS certificate verification
- No report files or disk output
- Compatible parse_target_source(target) interface
"""
import asyncio
import re
import ssl
import socket
import time
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
# ============================================================
# CONFIGURATION
# ============================================================
MAX_WORKERS = 8
REQUEST_TIMEOUT = 8
MAX_RESPONSE_SIZE = 512 * 1024
USER_AGENT = "NETKIT-Live-Parser/2.0"
COMMON_PATHS = [
    "/",
    "/robots.txt",
    "/sitemap.xml",
    "/favicon.ico",
    "/.well-known/security.txt",
    "/api",
    "/api/",
    "/api/health",
    "/api/status",
    "/api/v1",
    "/health",
    "/healthz",
    "/status",
    "/login",
    "/register",
    "/admin",
    "/dashboard",
    "/account",
    "/api/docs",
    "/docs",
    "/openapi.json",
    "/swagger.json",
    "/swagger/",
    "/graphql",
    "/actuator",
    "/actuator/health",
    "/server-status",
    "/.git/HEAD",
]
SENSITIVE_PATTERNS = {
    "Possible API key": re.compile(
        r"\b(?:api[_-]?key|access[_-]?key)\b",
        re.IGNORECASE
    ),
    "Possible password field": re.compile(
        r"\b(?:password|passwd|pwd)\b",
        re.IGNORECASE
    ),
    "Possible token field": re.compile(
        r"\b(?:access[_-]?token|refresh[_-]?token|auth[_-]?token)\b",
        re.IGNORECASE
    ),
    "Possible private-key marker": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.IGNORECASE
    ),
    "Possible cloud credential field": re.compile(
        r"\b(?:aws_secret_access_key|client_secret)\b",
        re.IGNORECASE
    ),
}
# ============================================================
# TERMINAL OUTPUT
# ============================================================
def print_status(message):
    print(f"[INFO] {message}", flush=True)
def print_success(message):
    print(f"[+] {message}", flush=True)
def print_warning(message):
    print(f"[!] {message}", flush=True)
def print_error(message):
    print(f"[-] {message}", flush=True)
def print_section(title):
    print()
    print("=" * 65)
    print(f" {title}")
    print("=" * 65)
# ============================================================
# TARGET NORMALIZATION
# ============================================================
def normalize_target(target):
    if not target:
        raise ValueError("Target cannot be empty.")
    target = str(target).strip()
    if "://" not in target:
        target = "https://" + target
    parsed = urlparse(target)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS targets are supported.")
    if not parsed.hostname:
        raise ValueError("Invalid target hostname.")
    hostname = parsed.hostname
    if any(char.isspace() for char in hostname):
        raise ValueError("Invalid hostname.")
    return parsed
def resolve_target(hostname):
    try:
        addresses = socket.getaddrinfo(
            hostname,
            None,
            type=socket.SOCK_STREAM
        )
        return sorted({
            item[4][0]
            for item in addresses
        })
    except socket.gaierror:
        return []
# ============================================================
# RESPONSE ANALYSIS
# ============================================================
def analyze_response(body):
    """
    Detects possible sensitive-content indicators.
    Does not print or return the actual secret values.
    """
    findings = []
    if not body:
        return findings
    text = body.decode(
        "utf-8",
        errors="ignore"
    )
    for label, pattern in SENSITIVE_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            findings.append({
                "type": label,
                "count": len(matches),
                "exposure_confirmed": False,
            })
    return findings
# ============================================================
# HTTP REQUEST
# ============================================================
def inspect_endpoint(base_url, path):
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Connection": "close",
        },
        method="GET",
    )
    result = {
        "url": url,
        "path": path,
        "status": None,
        "content_type": None,
        "content_length": 0,
        "redirect": None,
        "findings": [],
        "error": None,
        "elapsed": 0,
    }
    start = time.monotonic()
    try:
        context = ssl.create_default_context()
        with urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
            context=context
        ) as response:
            result["status"] = response.status
            result["content_type"] = response.headers.get(
                "Content-Type",
                "unknown"
            )
            result["redirect"] = response.geturl()
            body = response.read(MAX_RESPONSE_SIZE)
            result["content_length"] = len(body)
            result["findings"] = analyze_response(body)
    except HTTPError as exc:
        result["status"] = exc.code
        result["content_type"] = exc.headers.get(
            "Content-Type",
            "unknown"
        )
        result["error"] = f"HTTP {exc.code}"
    except URLError as exc:
        result["error"] = str(exc.reason)
    except socket.timeout:
        result["error"] = "Connection timeout"
    except ssl.SSLError:
        result["error"] = "TLS verification failed"
    except Exception as exc:
        result["error"] = str(exc)
    result["elapsed"] = round(
        time.monotonic() - start,
        3
    )
    return result
# ============================================================
# LIVE RESULT DISPLAY
# ============================================================
def display_result(result):
    status = result["status"]
    path = result["path"]
    if status is not None:
        if status == 200:
            print_success(
                f"{status} | {path} | "
                f"{result['content_type']} | "
                f"{result['elapsed']}s"
            )
        elif status in (301, 302, 307, 308):
            print_warning(
                f"{status} | {path} | Redirect"
            )
        elif status in (401, 403):
            print_warning(
                f"{status} | {path} | Access restricted"
            )
        elif status == 404:
            print(f"[404] {path}", flush=True)
        else:
            print(
                f"[HTTP {status}] {path}",
                flush=True
            )
    else:
        print_error(
            f"{path} | {result['error']}"
        )
    for finding in result["findings"]:
        print_warning(
            f"Possible sensitive-content indicator: "
            f"{finding['type']} "
            f"(matches: {finding['count']})"
        )
        print_warning(
            "Indicator only — exposure requires manual validation."
        )
# ============================================================
# MAIN PARSER
# ============================================================
def parse_target_source(target):
    """
    Main parser entry point.
    Returns:
        {
            "target": str,
            "addresses": list,
            "results": list,
            "findings": list,
            "aggregated_text": str,
            "count": int,
            "status": str
        }
    No files are created.
    """
    print_section("LIVE ENDPOINT DISCOVERY")
    parsed = normalize_target(target)
    hostname = parsed.hostname
    scheme = parsed.scheme
    base_url = f"{scheme}://{parsed.netloc}/"
    print_status(f"Target: {base_url}")
    print_status(f"Hostname: {hostname}")
    # --------------------------------------------------------
    # DNS RESOLUTION
    # --------------------------------------------------------
    print_section("DNS RESOLUTION")
    addresses = resolve_target(hostname)
    if not addresses:
        print_error("DNS resolution failed.")
        return {
            "target": base_url,
            "addresses": [],
            "results": [],
            "findings": [],
            "aggregated_text": "",
            "count": 0,
            "status": "DNS_FAILED",
        }
    for address in addresses:
        print_success(f"Resolved: {address}")
    # --------------------------------------------------------
    # ENDPOINT DISCOVERY
    # --------------------------------------------------------
    print_section("LIVE ENDPOINT TESTING")
    print_status(
        f"Testing {len(COMMON_PATHS)} endpoints "
        f"with {MAX_WORKERS} workers."
    )
    results = []
    findings = []
    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:
        futures = {
            executor.submit(
                inspect_endpoint,
                base_url,
                path
            ): path
            for path in COMMON_PATHS
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                display_result(result)
                for finding in result["findings"]:
                    findings.append({
                        "path": result["path"],
                        **finding,
                    })
            except Exception as exc:
                print_error(
                    f"Worker failure: {exc}"
                )
    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    successful = sum(
        1 for result in results
        if result["status"] is not None
    )
    open_endpoints = sum(
        1 for result in results
        if result["status"] == 200
    )
    print_section("PARSER SUMMARY")
    print(f"Target:              {base_url}")
    print(f"Resolved addresses:  {len(addresses)}")
    print(f"Endpoints tested:    {len(results)}")
    print(f"HTTP responses:      {successful}")
    print(f"HTTP 200 responses:  {open_endpoints}")
    print(f"Indicators found:    {len(findings)}")
    if findings:
        print_warning(
            "Sensitive-content indicators require manual verification."
        )
    else:
        print_success(
            "No configured sensitive-content indicators detected."
        )
    print_section("PARSER COMPLETE")
    return {
        "target": base_url,
        "addresses": addresses,
        "results": results,
        "findings": findings,
        "aggregated_text": "",
        "count": len(results),
        "status": "COMPLETED",
    }
# ============================================================
# ASYNC COMPATIBILITY WRAPPER
# ============================================================
async def parse_target_source_async(target):
    return await asyncio.to_thread(
        parse_target_source,
        target
    )
# ============================================================
# STANDALONE EXECUTION
# ============================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(
            "Usage: python3 parser.py https://example.com"
        )
        sys.exit(1)
    try:
        parse_target_source(sys.argv[1])
    except KeyboardInterrupt:
        print_warning("Parser interrupted by user.")
    except Exception as exc:
        print_error(f"Parser failed: {exc}")