#!/usr/bin/env python3
"""
SESSION_HIJACKER.PY — Advanced Session Seeding & Token Replay
"""
import sys
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlsplit

def exploit_session(target_url):
    parsed = urlsplit(target_url if "://" in target_url else f"https://{target_url}")
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    
    login_url = f"{base_url}/user/login"
    print(f"[+] Initializing Red-Team Session Harvester against: {base_url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    with httpx.Client(verify=False, follow_redirects=True, timeout=10.0) as client:
        # Step 1: Establish initial cookie jar and pull a fresh CSRF token
        resp = client.get(login_url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        token = soup.find("input", {"name": "_token"})
        
        if token:
            csrf_val = token.get("value")
            print(captured_cookies := dict(client.cookies))
            print(f"[+] Captured Session Cookie Jar: {captured_cookies}")
            print(f"[+] Harvested Replay CSRF Token: {csrf_val}")
            return captured_cookies, csrf_val
        else:
            print("[-] Failed to harvest session token.")
            return None, None

if __name__ == "__main__":
    exploit_session(sys.argv[1] if len(sys.argv) > 1 else "https://cryptobytes.online")
