#!/usr/bin/env python3
"""
TELEMETRY.PY v7.5 — Live Offensive Streamer & Automated Loot Exfiltration Handler (Elite Edition)
Features:
- Automated high-value loot parsing (JWTs, API keys, wallet balances, admin tokens)
- Zero-disk in-memory exfiltration packaging
- Real-time zero-delay proof-of-work terminal rendering
"""
import sys
import json

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"
MATRIX_GREEN = "\033[38;5;46m"
NEON_BLUE = "\033[38;5;51m"
MAGENTA = "\033[95m"

def extract_valuable_loot(response_body):
    """Parses response bodies to automatically harvest high-value credentials, keys, and tokens."""
    looted_assets = {}
    if not response_body or not isinstance(response_body, str):
        return looted_assets

    try:
        data = json.loads(response_body)
        if isinstance(data, dict):
            for k, v in data.items():
                if any(sub in k.lower() for sub in ["token", "key", "secret", "balance", "wallet", "admin", "role", "session", "user_id"]):
                    looted_assets[k] = v
    except json.JSONDecodeError:
        pass

    return looted_assets

def stream_proof(exploit_type, endpoint, payload, response_body, proof_data):
    """
    Instantly streams verified proof-of-work and automatically extracts exfiltrated loot to the terminal.
    """
    sys.stdout.write(f"\n{RED}{BOLD}[***] LIVE EXPLOIT VERIFIED: {exploit_type.upper()} [***]{RESET}\n")
    sys.stdout.write(f"  ├── Target Endpoint : {NEON_BLUE}{endpoint}{RESET}\n")
    sys.stdout.write(f"  ├── Injected Payload: {YELLOW}{json.dumps(payload)}{RESET}\n")
    
    # Automatically parse and highlight exfiltrated high-value loot
    auto_loot = extract_valuable_loot(response_body)
    if auto_loot:
        sys.stdout.write(f"  ├── {MAGENTA}AUTOMATED LOOT EXPORT (HIGH-VALUE ASSETS):{RESET}\n")
        for l_key, l_val in auto_loot.items():
            sys.stdout.write(f"  │     └── {CYAN}{l_key}{RESET} : {MATRIX_GREEN}{l_val}{RESET}\n")

    sys.stdout.write(f"  └── STOLEN VALUE / PROOF:\n")
    
    if isinstance(proof_data, dict):
        for k, v in proof_data.items():
            sys.stdout.write(f"      ├── {CYAN}{k}{RESET} : {MATRIX_GREEN}{v}{RESET}\n")
    else:
        sys.stdout.write(f"      └── {MATRIX_GREEN}{str(proof_data)[:300]}{RESET}\n")
        
    sys.stdout.write(f"  └── Response Preview: {GREEN}{response_body[:150]}...{RESET}\n\n")
    sys.stdout.flush()
