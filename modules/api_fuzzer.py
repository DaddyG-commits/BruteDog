#!/usr/bin/env python3
"""
API_FUZZER.PY — Direct REST API IDOR & Privilege Escalation Probe
"""
import sys
import httpx

def fuzz_api_endpoints(target_url, cookie_dict):
    base_url = target_url.rstrip("/")
    # Target high-value financial API endpoints for IDOR / horizontal privilege escalation
    endpoints = [
        "/user/dashboard",
        "/user/profile-setting",
        "/user/transfer-balance",
        "/api/wallet/balance",
        "/admin/dashboard" # Testing for vertical escalation
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)",
        "X-Requested-With": "XMLHttpRequest"
    }

    print(f"[+] Launching API IDOR & Privilege Escalation Scan...")
    with httpx.Client(verify=False, cookies=cookie_dict, timeout=10.0) as client:
        for ep in endpoints:
            url = f"{base_url}{ep}"
            resp = client.get(url, headers=headers)
            print(f"[*] Probing {ep} -> Status: {resp.status_code} [Length: {len(resp.text)}] ")
            if resp.status_code == 200 and "unauthorized" not in resp.text.lower():
                print(f"[!] POTENTIAL VULNERABILITY / DATA EXPOSURE AT: {url}")

if __name__ == "__main__":
    print("Usage: python3 -m modules.api_fuzzer <target_url>")
