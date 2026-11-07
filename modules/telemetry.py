#!/usr/bin/env python3
"""
TELEMETRY.PY — Live Offensive Streamer & Proof-of-Work Formatter
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

def stream_proof(exploit_type, endpoint, payload, response_body, proof_data):
    """
    Instantly streams verified proof-of-work to the terminal with zero delay.
    """
    sys.stdout.write(f"\n{RED}{BOLD}[***] LIVE EXPLOIT VERIFIED: {exploit_type.upper()} [***]{RESET}\n")
    sys.stdout.write(f"  ├── Target Endpoint : {NEON_BLUE}{endpoint}{RESET}\n")
    sys.stdout.write(f"  ├── Injected Payload: {YELLOW}{json.dumps(payload)}{RESET}\n")
    sys.stdout.write(f"  └── STOLEN VALUE / PROOF:\n")
    
    if isinstance(proof_data, dict):
        for k, v in proof_data.items():
            sys.stdout.write(f"      ├── {CYAN}{k}{RESET} : {MATRIX_GREEN}{v}{RESET}\n")
    else:
        sys.stdout.write(f"      └── {MATRIX_GREEN}{str(proof_data)[:300]}{RESET}\n")
        
    sys.stdout.write(f"  └── Response Preview: {GREEN}{response_body[:150]}...{RESET}\n\n")
    sys.stdout.flush()
